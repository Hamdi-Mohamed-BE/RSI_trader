"""Explicit, local research orchestration. Never installs EAs or places live orders.

Run development only after a verified native export. Evaluation requires the
persisted final selection freeze; rerunning development after that is refused.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

import numpy as np

import search
import robustness

ROOT = Path(__file__).resolve().parent


def read(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8-sig"))


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def clean(value):
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [clean(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def save(name, value):
    (ROOT / name).write_text(json.dumps(clean(value), indent=2, allow_nan=False) + "\n", encoding="utf-8")


def preflight():
    data, plan, split = read("DATA.json"), read("PLAN.json"), read("data-split.json")
    spec = data["specification"]
    if spec.get("symbol") != "BTCUSD" or float(spec.get("point", 0)) != 0.01 or spec.get("profit_currency") != "USD":
        raise RuntimeError("Search spread unit requires the verified .01-point BTCUSD USD-profit specification")
    frozen = read("PLAN-FREEZE.json")
    if sha(ROOT / "PLAN.json") != frozen["plan_sha256"] or sha(ROOT / "data-split.json") != frozen["split_sha256"]:
        raise RuntimeError("Preregistered plan/date split changed")
    checks = []
    for source in data["coverage"]:
        path = ROOT / source["path"]
        if sha(path) != source["sha256"]:
            raise RuntimeError("Export source hash changed")
        with np.load(path, allow_pickle=False) as archive:
            bars = archive["rates"]
            finite_positive = all(bool(np.all(np.isfinite(bars[k]) & (bars[k] > 0))) for k in ("open", "high", "low", "close"))
            ordering = bool(np.all(bars["high"] >= np.maximum(bars["open"], bars["close"])) and np.all(bars["low"] <= np.minimum(bars["open"], bars["close"])) and np.all(bars["high"] >= bars["low"]))
            timestamps = bool(np.all(np.diff(bars["time"]) > 0) and np.all(bars["time"] % source["timeframe_seconds"] == 0))
            volume = bool(np.all(bars["tick_volume"] >= 0))
            checks.append({"timeframe": source["timeframe"], "all_ohlc_finite_positive": finite_positive,
                           "ohlc_ordered": ordering, "timestamps_ordered_aligned": timestamps,
                           "nonnegative_tick_volume": volume, "start_covered": source["start_covered"],
                           "end_covered": source["end_covered"], "interior_gap_count": source["gaps"],
                           "unknown_spread_bars": source["nonpositive_spread_bars"]})
    passed = data["status"] == "EXPORT_COMPLETE" and all(all(row[k] for k in ("all_ohlc_finite_positive", "ohlc_ordered", "timestamps_ordered_aligned", "nonnegative_tick_volume", "start_covered", "end_covered")) for row in checks)
    result = {"status": "SOURCE_APPROVED_WITH_GAP_AUDITS" if passed else "SOURCE_REJECTED", "checks": checks,
              "end_exclusive": plan["data"]["end_exclusive"], "interior_gaps_not_imputed": True,
              "coverage_is_not_execution_quality": True, "source_hashes": {source["path"]: sha(ROOT / source["path"]) for source in data["coverage"]}}
    save("SOURCE CHECK.json", result)
    if not passed:
        raise RuntimeError("Source validation failed; no search authorized")
    return result


def engine():
    preflight()
    return search.WeekendEngine(ROOT / "data", read("PLAN.json"), read("data-split.json"), ROOT)


def raw_gates(eng):
    plan = read("PLAN.json")
    result = {"basis": "Causal gross M5 search surrogate. Native gates separately audited; not a promotion pass.", "windows": []}
    for years, start in ((3, plan["raw_gate"]["three_year_start"]), (5, plan["raw_gate"]["five_year_start"])):
        end = plan["raw_gate"]["end_exclusive"]
        base = eng.panel(search.BASELINE, start, end)
        controls = [eng.panel(search.BASELINE, start, end, control_weekday=day) for day in range(4)]
        control_scores = [row["metrics"]["score"] for row in controls]
        complete_controls = all(not row["missing_week_ids"] for row in controls)
        metric = base["metrics"]
        requirements = {"minimum_30_trades": metric["trades"] >= 30,
                        "pf_at_least_1_15": metric["profit_factor"] is not None and metric["profit_factor"] >= 1.15,
                        "positive_return": metric["return_pct"] > 0,
                        "beats_median_exposure_matched_control_score": complete_controls and metric["score"] > float(np.median(control_scores)),
                        "complete_control_history": complete_controls,
                        "complete_price_evidence": not base["missing_week_ids"]}
        result["windows"].append({"years": years, "start": start, "end_exclusive": end, "baseline_metrics": metric,
                                  "controls": [{"entry_weekday": day, "metrics": row["metrics"]} for day, row in enumerate(controls)],
                                  "requirements": requirements, "passed": all(requirements.values())})
    result["all_surrogate_gates_passed"] = all(row["passed"] for row in result["windows"])
    result["exploratory_continuation_authorized"] = True
    save("RAW-GATES.json", result)
    return result


def develop():
    if (ROOT / "FROZEN.json").exists() or (ROOT / "SELECTION LOCK.json").exists():
        raise RuntimeError("Final configuration already frozen; refusing a new search")
    eng = engine()
    raw_gates(eng)
    del eng
    result = search.run_development(ROOT)
    selection = result["selection"]
    save("SELECTION LOCK.json", {"selected_config": selection["selected_config"], "selection_sha256": sha(ROOT / "SELECTION.json"),
        "search_sha256": sha(ROOT / "search.py"), "trial_results_sha256": sha(ROOT / "SEARCH RESULTS.json"),
        "selected_at_utc": datetime.now(timezone.utc).isoformat(), "no_oos_read": True})
    print(json.dumps({"selection_status": selection["selection_status"], "unique_configurations": selection["unique_configurations"], "selected_config": selection["selected_config"], "oos_still_locked": True}, indent=2))


def freeze_selection():
    if (ROOT / "FROZEN.json").exists():
        raise RuntimeError("Final OOS freeze already exists")
    selection, lock = read("SELECTION.json"), read("SELECTION LOCK.json")
    if sha(ROOT / "SELECTION.json") != lock["selection_sha256"] or sha(ROOT / "search.py") != lock["search_sha256"] or sha(ROOT / "SEARCH RESULTS.json") != lock["trial_results_sha256"]:
        raise RuntimeError("Locked selection/search results changed")
    files = ["PLAN.json", "data-split.json", "search.py", "SEARCH RESULTS.json", "SELECTION.json", "SELECTION LOCK.json", "DATA.json", "SOURCE CHECK.json", "robustness.py", "native_robustness.py", "run_pipeline.py", "PRE-SEARCH CORRECTIONS.json", "DEVELOPMENT ATTEMPTS.json", "run_native.py", "native.py", "EA/BtcWeekend.mq5"]
    source = read("SOURCE CHECK.json")
    frozen = {"frozen_at_utc": datetime.now(timezone.utc).isoformat(), "research_only": True,
              "retrospective_oos": True, "selected_config": selection["selected_config"],
              "baseline_config": selection["baseline_config"],
              "locked": {"selected_config": selection["selected_config"], "files": {name: sha(ROOT / name) for name in files},
                         "source_hashes": source["source_hashes"]}}
    save("FROZEN.json", frozen)
    print(json.dumps({"selection_status": selection["selection_status"], "unique_configurations": selection["unique_configurations"], "selected_config": selection["selected_config"], "frozen_before_oos": True}, indent=2))


def cost_scenarios(panel, specification):
    trades = panel["trades"]
    valid = [row for row in trades if row.get("observed_spread_proxy_return") is not None]
    complete = len(valid) == len(trades)
    output = {"historical_full_cost_net": None, "status": "PROXY_AND_ASSUMPTIONS_ONLY", "trades": len(trades),
              "observed_positive_entry_spread_trades": len(valid), "spread_proxy_complete": complete,
              "warning": "Spread proxy retains gross exit geometry, not actual ask-sensitive stop/target reexecution. Historical financing, commissions and slippage are not reconstructed.", "scenarios": []}
    if complete and trades:
        records = deepcopy(trades)
        for row in records:
            row["return_per_notional"] = row["observed_spread_proxy_return"]
        output["scenarios"].append({"name": "Observed entry-bar spread proxy only", "metrics": search.summarize(records, panel["start_epoch"], panel["end_exclusive_epoch"])})
        if int(specification.get("swap_mode", -1)) != 1 or specification.get("profit_currency") != "USD" or specification.get("symbol") != "BTCUSD":
            output["swap_sensitivity_status"] = "Unavailable: current specification is not verified points-mode BTCUSD with USD quote/profit currency"
            return output
        point = float(specification["point"])
        long_swap = float(specification["swap_long"])
        if long_swap >= 0:
            output["swap_sensitivity_status"] = "Unavailable: current long swap is not a negative points charge; no credit is converted to a cost"
            return output
        swap = -long_swap * point
        output["current_swap_points_to_price_assumption"] = {"point": point, "absolute_swap_price_per_btc_per_charge": swap,
            "not_historical_cost_reconstruction": True, "rollover_boundary_uncertain": True}
        for charges in (3, 4):
            for original, row in zip(trades, records):
                row["return_per_notional"] = original["observed_spread_proxy_return"] - charges * swap / (original["entry_price"] + original["observed_entry_spread_points"] * point)
            output["scenarios"].append({"name": f"Spread proxy minus assumed {charges} current swap charges per trade (sensitivity only)", "metrics": search.summarize(records, panel["start_epoch"], panel["end_exclusive_epoch"])})
    return output


def evaluate():
    if (ROOT / "OOS.json").exists():
        raise RuntimeError("OOS already saved; rebuild report without reevaluating/reselecting")
    eng = engine()
    chosen, baseline = read("FROZEN.json")["selected_config"], search.BASELINE
    split, selection = read("data-split.json"), read("SELECTION.json")
    intervals = [("Development", split["development"]["start"], split["development"]["end_exclusive"]),
                 ("Older validation", split["validation"]["start"], split["validation"]["end_exclusive"]),
                 ("Retrospective OOS · two years", split["oos"]["start"], split["oos"]["end_exclusive"]),
                 ("Recent 3 months", "2026-07-17", "2026-10-17"), ("Recent 6 months", "2026-04-17", "2026-10-17"),
                 ("Recent 1 year", "2025-10-17", "2026-10-17"), ("Recent 3 years", "2023-10-17", "2026-10-17"),
                 ("Recent 5 years", "2021-10-17", "2026-10-17"), ("Full available requested history", "2018-01-01", "2026-10-17")]
    periods, panels = [], {}
    for label, start, end in intervals:
        base = eng.panel(baseline, start, end, allow_oos=True, include_paths=label.startswith("Retrospective"))
        selected = eng.panel(chosen, start, end, allow_oos=True, include_paths=label.startswith("Retrospective"))
        periods.append({"label": label, "start": start, "end": end,
                        "baseline": {"metrics": base["metrics"], "missing_week_ids": base["missing_week_ids"], "censored_incomplete_week_ids": base["censored_incomplete_week_ids"]},
                        "selected": {"metrics": selected["metrics"], "missing_week_ids": selected["missing_week_ids"], "censored_incomplete_week_ids": selected["censored_incomplete_week_ids"]}})
        panels[label] = {"baseline": base, "selected": selected}
    oos = panels["Retrospective OOS · two years"]
    save("OOS.json", {"retrospective_not_untouched": True, "frozen_config_only": True, "periods": periods, "panels": panels})
    trials = read("SEARCH RESULTS.json")["trials"]
    sharpe_std = np.std([row["metrics"]["weekly_sharpe"] / math.sqrt(52) for row in trials if row["metrics"]["weekly_sharpe"] is not None], ddof=1)
    diagnostics = {}
    for name, panel in oos.items():
        diagnostics[name] = robustness.analyze_robustness(panel["trades"], tested_configurations=selection["unique_configurations"],
            scheduled_week_ids=panel["scheduled_week_ids"], missing_week_ids=panel["missing_week_ids"], paths=10000,
            trial_sharpe_std=float(sharpe_std), period_start_epoch=panel["start_epoch"], period_end_epoch=panel["end_exclusive_epoch"])
        if panel["missing_week_ids"] and panel["trades"]:
            known = [week for week in panel["scheduled_week_ids"] if week not in set(panel["missing_week_ids"])]
            observed_trades = [row for row in panel["trades"] if row["week_id"] in set(known)]
            diagnostics[name]["observed_complete_weeks_only_sensitivity"] = robustness.analyze_robustness(observed_trades,
                tested_configurations=selection["unique_configurations"], scheduled_week_ids=known, paths=10000,
                trial_sharpe_std=float(sharpe_std))
            diagnostics[name]["observed_complete_weeks_only_sensitivity"]["not_complete_period_evidence"] = True
            diagnostics[name]["observed_complete_weeks_only_sensitivity"]["block_spacing_caveat"] = "Removing missing calendar weeks compresses spacing: five retained weekly records may span more than five calendar weeks. Not full-period evidence."
    matrix, ids, weeks, missing = eng.week_return_matrix([row["config"] for row in trials], split["development"]["start"], split["development"]["end_exclusive"])
    diagnostics["family_null_development"] = robustness.family_null(matrix, ids, selection["selected_config_id"], paths=10000)
    diagnostics["family_null_development"]["missing_week_ids"] = missing
    complete_rows = np.all(np.isfinite(matrix), axis=1)
    if missing and int(complete_rows.sum()) >= 3:
        sensitivity = robustness.family_null(matrix[complete_rows], ids, selection["selected_config_id"], paths=10000)
        sensitivity.update({"complete_common_weeks_only": True, "not_complete_development_evidence": True,
                            "weeks_retained": int(complete_rows.sum()), "weeks_excluded": len(missing),
                            "reason": "Entire calendar weeks with any missing configuration removed jointly; no outcomes-based filtering or column-independent resampling. Five retained records may span more than five calendar weeks."})
        diagnostics["family_null_complete_weeks_sensitivity"] = sensitivity
    diagnostics["actual_unique_configurations"] = selection["unique_configurations"]
    save("ROBUSTNESS.json", diagnostics)
    data = read("DATA.json")
    save("COST SENSITIVITIES.json", {name: cost_scenarios(panel, data["specification"]) for name, panel in oos.items()})
    print(json.dumps({"periods": periods, "robustness_status": {k: v.get("status") for k, v in diagnostics.items() if isinstance(v, dict)}}, indent=2))


def final_report():
    data, source = read("DATA.json"), read("SOURCE CHECK.json")
    oos, diagnostics, selection = read("OOS.json"), read("ROBUSTNESS.json"), read("SELECTION.json")
    native = read("NATIVE AUDIT.json") if (ROOT / "NATIVE AUDIT.json").exists() else {"status": "PENDING_NATIVE_CONFIRMATION", "promotion_passed": False}
    gates = {"research_only_authorization": True, "raw_surrogate_gates": read("RAW-GATES.json")["all_surrogate_gates_passed"],
             "older_validation": selection["selection_status"] == "research_selection_passed_older_validation",
             "genuinely_untouched_oos": False, "native_execution_promotion": native.get("promotion_passed", False),
             "historical_full_cost_reconstruction": False, "independent_portfolio_overlap": None, "live_deployment_approved": False}
    final = {"study_status": "RESEARCH ONLY — not promoted", "research_only": True, "date_split": read("data-split.json"),
             "source_summary": {"server": data["server"], "coverage": data["coverage"], "preflight": source},
             "raw_gates": read("RAW-GATES.json"), "selection": selection, "periods": oos["periods"],
             "robustness": diagnostics, "native_audit": native, "cost_scenarios": read("COST SENSITIVITIES.json"),
             "native_robustness": read("NATIVE ROBUSTNESS.json") if (ROOT / "NATIVE ROBUSTNESS.json").exists() else None,
             "promotion_gates": gates, "cautions": [
                "Research-only. No production EA, BAT, website or active account was changed. No new push was authorized.",
                "Main comparison is a gross causal M5 OHLC search surrogate at 1x current cash allocation, not 1% stop risk or executable net performance.",
                "2024-10-17 to2026-10-17 is retrospective temporal OOS, previously inspected; no claim of untouched data.",
                "Complete price windows and unknown history are distinguished. Missing bars/spreads are never filled with invented values.",
                "October16-18 weekend is incomplete at the frozen end and censored, not a valid forced-close trade.",
                "Native Model4 can substitute generated ticks when real history is absent; inspect actual coverage before interpreting execution evidence.",
                "Current swap sensitivities are assumptions, not reconstructed historical financing. Backtests/Monte Carlo do not establish future success probabilities."]}
    save("FINAL.json", final)
    from report import build_report
    print(build_report(ROOT))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["preflight", "development", "freeze", "evaluate", "report"])
    args = parser.parse_args()
    {"preflight": preflight, "development": develop, "freeze": freeze_selection, "evaluate": evaluate, "report": final_report}[args.action]()
