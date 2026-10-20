"""Independent offline receipt for the frozen BTC weekend study.

Reconstructs only the already-frozen baseline and final configuration; never
searches alternatives, imports MT5, opens account INIs/journals, or launches a
terminal. Run this file to reproduce the checks and write its own AUDIT.json.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import unittest
from zoneinfo import ZoneInfo

import numpy as np

NY = ZoneInfo("America/New_York")


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(root):
    root = Path(root).resolve()
    checks = 0

    def read(name):
        return json.loads((root / name).read_text(encoding="utf-8-sig"))

    def ok(value, message):
        nonlocal checks
        checks += 1
        if not value:
            raise AssertionError(message)

    def same(a, b, message, tolerance=1e-7):
        if a is None or b is None:
            ok(a is None and b is None, message)
        else:
            ok(math.isclose(float(a), float(b), abs_tol=tolerance, rel_tol=1e-9), message)

    frozen, selection, outcomes = read("FROZEN.json"), read("SELECTION.json"), read("OOS.json")
    robustness, costs, split, searched = read("ROBUSTNESS.json"), read("COST SENSITIVITIES.json"), read("data-split.json"), read("SEARCH RESULTS.json")
    for name, expected in frozen["locked"]["files"].items():
        ok(sha(root / name) == expected, "Frozen file: " + name)
    for name, expected in frozen["locked"]["source_hashes"].items():
        ok(sha(root / name) == expected, "Frozen price source: " + name)
    ok(frozen["selected_config"] == selection["selected_config"] == frozen["locked"]["selected_config"], "Selected identity")
    ok(selection["selection_status"] == "FAILED_VALIDATION_EXPLORATORY_ONLY" and selection["oos_read_for_selection"] is False, "Failed-validation status and OOS exclusion")
    ok(selection["selected_config"] == selection["dev_finalists"][0]["config"], "Fallback remains first DEVELOPMENT centre")
    ok(len(searched["trials"]) == len({t["config_id"] for t in searched["trials"]}) == selection["unique_configurations"] == 345, "Actual unique trial count")
    ok(split["oos"]["start"] == "2024-10-17" and split["oos"]["end_exclusive"] == "2026-10-17", "Two-calendar-year holdout")
    ok(datetime.fromisoformat(frozen["frozen_at_utc"]).timestamp() < (root / "OOS.json").stat().st_mtime, "Freeze predates saved OOS output")
    with np.load(root / "data/BTCUSD-M5.npz", allow_pickle=False) as saved:
        bars = saved["rates"].copy()
    with np.load(root / "data/BTCUSD-D1.npz", allow_pickle=False) as saved:
        daily = saved["rates"].copy()
    times, days = np.ascontiguousarray(bars["time"]), np.ascontiguousarray(daily["time"])
    record_occurrences, period_rows = 0, []
    for title, pair in outcomes["panels"].items():
        for variant, panel in pair.items():
            config = frozen["selected_config"] if variant == "selected" else frozen["baseline_config"]
            ok(panel["config"] == config, "Frozen panel configuration: " + title + variant)
            records = panel["trades"]
            previous = 0
            balance = peak = 10000.0
            gain = loss = max_dd = max_cash_dd = 0.0
            wins = losses = win_streak = loss_streak = max_win = max_loss = 0
            missing, filtered = set(panel["missing_week_ids"]), set(panel["filtered_week_ids"])
            scheduled, weekly, seen = panel["scheduled_week_ids"], panel["weekly_returns"], set()
            ok(set(scheduled) == set(weekly), "Authoritative weekly universe")
            ok(not missing & filtered, "Missing and filtered classifications distinct")
            ok(not set(panel["censored_incomplete_week_ids"]) & set(scheduled), "Censored week not inserted as zero")
            for trade in records:
                record_occurrences += 1
                entry, exit_time = trade["entry_epoch"], trade["exit_epoch"]
                ok(entry >= previous, "No overlapping weekend positions")
                previous = exit_time
                local_entry = datetime.fromtimestamp(entry, NY)
                local_deadline = datetime.fromtimestamp(trade["planned_exit_epoch"], NY)
                ok(local_entry.weekday() == 4 and local_entry.hour * 60 + local_entry.minute == config["entry_minute_ny"], "NY Friday entry")
                ok(local_deadline.weekday() == 6 and local_deadline.hour * 60 + local_deadline.minute == config["exit_minute_ny"], "NY Sunday deadline")
                ok(trade["week_id"] == local_entry.date().isoformat(), "Friday week identity")
                seen.add(trade["week_id"])
                ok(trade["config_id"] == panel["config_id"], "Record configuration")
                ok(panel["start_epoch"] <= entry < exit_time <= trade["planned_exit_epoch"] < panel["end_exclusive_epoch"], "Closed window and administrative censor")
                i, j = np.searchsorted(times, [entry, trade["planned_exit_epoch"]])
                ok(times[i] == entry and times[j] == trade["planned_exit_epoch"], "Exact M5 endpoints")
                price = float(bars["open"][i])
                same(price, trade["entry_price"], "Entry OPEN price")
                if variant == "selected":
                    index = int(np.searchsorted(days + 86400, entry, side="right")) - 1
                    ok(index >= 0 and int(days[index]) + 86400 <= entry, "Completed D1 signal")
                    ok(daily["close"][index] > daily["open"][index], "Prior D1 bullish")
                    distance = price * .02
                    stop, target = price - distance, price + distance
                    expected_exit = float(bars["open"][j])
                    for k in range(i, j + 1):
                        opening = float(bars["open"][k])
                        low = opening if k == j else float(bars["low"][k])
                        high = opening if k == j else float(bars["high"][k])
                        if opening <= stop:
                            expected_exit = opening
                            break
                        if opening >= target:
                            expected_exit = target
                            break
                        if low <= stop:
                            expected_exit = stop
                            break
                        if high >= target:
                            expected_exit = target
                            break
                    same(expected_exit, trade["exit_price"], "Frozen 2% stop / 1R target / deadline geometry")
                    same(distance, trade["initial_stop_distance"], "Frozen initial stop distance")
                else:
                    same(bars["open"][j], trade["exit_price"], "Baseline Sunday OPEN")
                result = trade["exit_price"] / trade["entry_price"] - 1
                same(result, trade["return_per_notional"], "Unit notional return", 1e-12)
                pnl = balance * result
                balance += pnl
                gain += max(pnl, 0)
                loss += max(-pnl, 0)
                peak = max(peak, balance)
                max_dd = max(max_dd, (peak - balance) / peak * 100)
                max_cash_dd = max(max_cash_dd, peak - balance)
                wins += int(result > 0)
                losses += int(result < 0)
                win_streak = win_streak + 1 if result > 0 else 0
                loss_streak = loss_streak + 1 if result < 0 else 0
                max_win, max_loss = max(max_win, win_streak), max(max_loss, loss_streak)
                if trade["week_id"] not in missing:
                    same(weekly[trade["week_id"]], result, "Weekly return")
            for week in scheduled:
                if week in missing:
                    ok(weekly[week] is None, "Missing history never zero")
                elif week in filtered:
                    ok(weekly[week] == 0 and week not in seen, "Known filter/no-entry zero")
                else:
                    ok(week in seen, "Known position in scheduled week")
            metrics = panel["metrics"]
            same(balance, metrics["ending_balance_usd"], "Compounded cash")
            same(balance - 10000, metrics["pnl_usd"], "Compounded P&L")
            same((balance / 10000 - 1) * 100, metrics["return_pct"], "Compounded return")
            same(gain / loss if loss else None, metrics["profit_factor"], "Actual compounded-cash PF")
            same(max_dd, metrics["closed_dd_pct"], "Closed DD percent")
            same(max_cash_dd, metrics["closed_dd_usd"], "Closed DD cash")
            ok((len(records), wins, losses, max_win, max_loss) == (metrics["trades"], metrics["wins"], metrics["losses"], metrics["max_win_streak"], metrics["max_loss_streak"]), "Counts and streaks")
            same(100 * wins / len(records) if records else None, metrics["win_rate_pct"], "Win rate")
            ok(metrics["missing_week_count"] == len(missing) and metrics["coverage_evidence_pass"] == (not missing), "Missing evidence flags")
            period_rows.append({"period": title, "variant": variant, "trades": len(records),
                                "return_pct": metrics["return_pct"], "profit_factor": metrics["profit_factor"],
                                "missing_weeks": len(missing), "censored_incomplete_week_ids": panel["censored_incomplete_week_ids"]})
    for variant in ("baseline", "selected"):
        panel, diagnostic = outcomes["panels"]["Retrospective OOS · two years"][variant], robustness[variant]
        if panel["missing_week_ids"]:
            ok(diagnostic["status"] == "unavailable_incomplete_history" and diagnostic["missing_week_ids"] == panel["missing_week_ids"], "Primary Monte Carlo refuses missing history")
        for result in (diagnostic, diagnostic.get("observed_complete_weeks_only_sensitivity", {})):
            if "deflated_sharpe" in result:
                ok(result["deflated_sharpe"]["tested_configurations"] == 345, "MC actual trial count")
            for length, value in result.get("block_bootstrap", {}).items():
                ok(value["paths"] == 10000 and value["block_calendar_weeks"] == int(length), "Joint block-bootstrap policy")
            for value in result.get("trade_removal", {}).values():
                ok(value["paths"] == 10000, "Removal path count")
        ok(costs[variant]["historical_full_cost_net"] is None and costs[variant]["status"] == "PROXY_AND_ASSUMPTIONS_ONLY", "No invented historical net cost")
    ok(robustness["actual_unique_configurations"] == 345, "Robustness unique trial count")
    input_names = ["FROZEN.json", "SELECTION.json", "SELECTION LOCK.json", "OOS.json", "ROBUSTNESS.json", "COST SENSITIVITIES.json", "SEARCH RESULTS.json", "data-split.json"]
    return {"status": "PASS", "verified_at_utc": datetime.now(timezone.utc).isoformat(), "checks": checks,
            "closed_record_occurrences_checked": record_occurrences, "period_rows_checked": len(period_rows),
            "periods": period_rows, "actual_unique_configurations": 345,
            "selected_config_id": selection["selected_config_id"], "selection_status": selection["selection_status"],
            "all_locked_hashes_match": True, "frozen_file_hashes": frozen["locked"]["files"],
            "frozen_price_hashes": frozen["locked"]["source_hashes"],
            "inspected_output_hashes": {name: sha(root / name) for name in input_names},
            "auditor_source_sha256": sha(Path(__file__)), "family_null_status": robustness["family_null_development"]["status"],
            "reproduce": "python audit.py (from this study folder)", "no_live_calls": True,
            "limitations": ["Reconciles only the frozen baseline and final candidate; no alternate OOS configuration evaluated.",
                            "Gross M5 surrogate records with incomplete weeks remain descriptive, not executable net or certified full-period evidence.",
                            "Checks frozen-source price geometry and metadata, not independent broker data or historical financing.",
                            "Monte Carlo count/missing-data policy checked; not every random path independently regenerated here.",
                            "This receipt does not certify pending native executions, true tick equity, future profit or prop-firm pass probabilities.",
                            "No private account identifiers, tester INIs or journals were read."]}


def verify_fixtures():
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name)
                               for name in ("test_robustness", "test_report"))
    result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
    if not result.wasSuccessful():
        raise AssertionError("Offline synthetic fixture suite failed")
    return {"status": "PASS", "tests_run": result.testsRun, "modules": ["test_robustness", "test_report"],
            "command": "python -m unittest test_robustness test_report -q", "synthetic_only": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    receipt = verify(args.root)
    receipt["fixture_verification"] = verify_fixtures()
    receipt["fixture_source_hashes"] = {name: sha(args.root / name) for name in ("test_robustness.py", "test_report.py", "report.py")}
    (args.root / "AUDIT.json").write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({key: receipt[key] for key in ("status", "checks", "closed_record_occurrences_checked", "period_rows_checked", "fixture_verification")}))


if __name__ == "__main__":
    main()
