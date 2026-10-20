"""Post-freeze CLOSED-BALANCE-only native cash diagnostic supplement.

This is not an alpha search, a replacement for the frozen native-equity audit,
or a promotion-gate waiver.  A completed native cash outcome does not become
unknown merely because interior M1 equity snapshots are absent.  Conversely,
unexplained no-trade weekends and absent/forced endpoints are never zeros.
No MT5 calls, automatic outcome discovery, writes, or execution on import.
"""
from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import re

import native_robustness as native_audit
import robustness


def _closed_only(value):
    """Remove the generic analyzer's endpoint-proxy floating-DD field entirely."""
    if isinstance(value, list):
        return [_closed_only(item) for item in value]
    if not isinstance(value, dict):
        return value
    result = {}
    for key, item in value.items():
        if key == "max_sampled_equity_dd_pct":
            continue
        if key == "allocation":
            result[key] = "Resampled native whole-account returns (net position cash / pre-request balance), including actual down-rounded idle cash"
        elif key in ("scope", "dd_scope"):
            result[key] = "Joint completed-position cash resampling; CLOSED-BALANCE DD only. No intratrade/floating equity or daily-loss-limit inference. Costs/lot granularity are not re-executed."
        elif key == "probability_ruin_pct":
            result["resampled_closed_cash_exhaustion_pct"] = item
        else:
            result[key] = _closed_only(item)
    return result


def _run(records, weeks, missing, tested, paths, initial, start=None, end=None):
    options = {"tested_configurations": tested, "scheduled_week_ids": weeks,
               "missing_week_ids": missing, "paths": paths, "initial_balance": initial}
    if start is not None:
        options.update(period_start_epoch=start, period_end_epoch=end)
    answer = _closed_only(robustness.analyze_robustness(records, **options))
    answer["floating_equity_drawdown"] = {"status": "unavailable_in_cash_only_supplement", "value": None}
    answer["prop_simulation"] = {"status": "unavailable_from_closed_cash_only", "gate": None,
                                 "reason": "No intratrade/daily floating-equity path, so no funded-account failure or phase-pass probability is inferred."}
    answer["promotion_complete"] = False
    return answer


def analyze_cash_only(root, tag, paths=10000):
    """Return cash-known weekly MC, never reading any M1 equity observations.

    Only the explicitly supplied native tag is opened.  The caller controls
    whether a frozen OOS case is authorized and saves the supplement receipt.
    """
    root = Path(root).resolve()
    if (not isinstance(tag, str) or tag in (".", "..")
            or re.fullmatch(r"[A-Za-z0-9_.-]+", tag) is None):
        raise ValueError("A single explicit native case tag is required")
    if isinstance(paths, bool) or int(paths) != paths or paths < 1:
        raise ValueError("Positive integer simulation path count required")
    folder = root / "native" / tag
    result_path, decision_path = folder / "results.json", folder / "decisions.csv.gz"
    selection_path = root / "SELECTION.json"
    result = json.loads(result_path.read_text(encoding="utf-8-sig"))
    selection = json.loads(selection_path.read_text(encoding="utf-8-sig"))
    tested = selection.get("unique_configurations")
    if isinstance(tested, bool) or not isinstance(tested, int) or tested < 1:
        raise ValueError("SELECTION must supply actual positive unique configuration count")
    candidate = result["candidate"]
    schedule, censored = native_audit.weekend_calendar(candidate, result["start"], result["end_exclusive"])
    calendar = {row["week_id"]: row for row in schedule}
    exit_to_week = {row["scheduled_exit_epoch"]: row["week_id"] for row in schedule}
    issues = {week: [] for week in calendar}
    decisions = list(native_audit._rows(decision_path)) if decision_path.exists() else []
    decision_weeks = {week: [] for week in calendar}
    counts, malformed = {}, 0
    for decision in decisions:
        reason = str(decision.get("reason", ""))
        counts[reason] = counts.get(reason, 0) + 1
        try:
            week = exit_to_week.get(native_audit._integer(decision["scheduled_exit_epoch"]))
            if week is not None:
                stamp = native_audit._integer(decision["epoch"])
                if calendar[week]["entry_epoch"] <= stamp < calendar[week]["entry_epoch"] + 60:
                    decision_weeks[week].append(decision)
        except (KeyError, TypeError, ValueError):
            malformed += 1
    positions, requests = result.get("trades", []), result.get("entry_requests", [])
    by_week = {week: [] for week in calendar}
    outside = []
    for position in positions:
        week = datetime.fromtimestamp(native_audit._integer(position["open_epoch"]), native_audit.NY).date().isoformat()
        if week in by_week:
            by_week[week].append(position)
        else:
            outside.append(str(position.get("position_id")))
    ordered = sorted(positions, key=lambda p: native_audit._msc(p, "open_time_msc", "open_epoch"))
    overlapping = any(a.get("close_epoch") is None or native_audit._msc(a, "close_time_msc", "close_epoch") >
                      native_audit._msc(b, "open_time_msc", "open_epoch") for a, b in zip(ordered, ordered[1:]))
    initial = native_audit._number(result.get("metrics", {}).get("initial_balance", 10000))
    if initial <= 0:
        raise ValueError("Invalid initial native cash")
    cash, records, audit = initial, [], []
    for position in ordered:
        week = datetime.fromtimestamp(native_audit._integer(position["open_epoch"]), native_audit.NY).date().isoformat()
        if week not in calendar:
            continue
        try:
            if len(by_week[week]) != 1:
                raise ValueError("Multiple native positions in one scheduled week")
            if not position.get("closed") or position.get("close_epoch") is None:
                raise ValueError("Missing natural closed-position cash endpoint")
            if position.get("end_of_test_liquidation") or position.get("exit_reason") == "test-end":
                raise ValueError("Forced tester-end endpoint is not a naturally completed cash outcome")
            if overlapping:
                raise ValueError("Overlapping native positions outside this one-position model")
            net = native_audit._validate_costs(position)
            request = native_audit._request_for(position, requests, calendar[week])
            before = native_audit._number(request["balance"])
            if before <= 0 or net / before < -1:
                raise ValueError("Invalid pre-request cash / account-relative return")
            if abs(before - cash) > .025:
                raise ValueError("Pre-request balance differs from prior native whole-position cash")
            close = native_audit._integer(position["close_epoch"])
            opening = native_audit._integer(position["open_epoch"])
            if close <= opening or close >= native_audit._epoch(result["end_exclusive"]):
                raise ValueError("Invalid or subsecond-only closed endpoint for second-resolution diagnostics")
            if position.get("scheduled_exit_epoch") not in (None, calendar[week]["scheduled_exit_epoch"]):
                raise ValueError("Native position exit schedule differs from independent NY calendar")
            record = {"week_id": week, "position_id": str(position["position_id"]),
                      "entry_epoch": native_audit._integer(request["epoch"]), "exit_epoch": close,
                      "return_per_notional": net / before,
                      "cost_basis": native_audit.COST_BASIS}
            # Intentionally NO intratrade_path: not even a fictitious straight
            # line between native endpoints is supplied to the analyzer.
            records.append(record)
            audit.append({"week_id": week, "position_id": str(position["position_id"]),
                          "entry_request_epoch": record["entry_epoch"], "close_epoch": close,
                          "before_entry_request_balance": before, "native_net_profit": net,
                          "account_return": net / before,
                          "commission": native_audit._number(position["commission"]),
                          "swap": native_audit._number(position["swap"]),
                          "fee": native_audit._number(position["fee"]), "cost_components_reconcile": True})
        except (KeyError, TypeError, ValueError) as exc:
            issues[week].append(str(exc))
        if position.get("closed"):
            try:
                cash += native_audit._validate_costs(position)
            except (KeyError, TypeError, ValueError):
                pass
    documented_zero = {}
    requested_exits = {native_audit._integer(r["scheduled_exit_epoch"]) for r in requests}
    for week, spec in calendar.items():
        if by_week[week]:
            continue
        receipt = decision_weeks[week]
        skips = [row for row in receipt if str(row.get("reason", "")).startswith("skip_")]
        if (len(skips) == 1 and native_audit._documented_zero(skips[0], candidate)
                and spec["scheduled_exit_epoch"] not in requested_exits
                and not any(row.get("reason") in ("entry_request", "entry_filled", "entry_rejected") for row in receipt)):
            documented_zero[week] = skips[0]["reason"]
        else:
            reasons = sorted({str(row.get("reason", "")) for row in receipt})
            issues[week].append("Unexplained or failed no-trade weekend; not zero" + (": " + ", ".join(reasons) if reasons else "; no receipt"))
    global_issues = []
    if outside:
        global_issues.append("Positions outside complete schedule: " + ", ".join(outside))
    if malformed:
        global_issues.append("Malformed decision rows: " + str(malformed))
    if result.get("decision_counts") is not None and result["decision_counts"] != counts:
        global_issues.append("Decision audit count mismatch")
    observed_cash = sum(native_audit._number(p["net_profit"]) for p in positions)
    native_cash = native_audit._number(result.get("metrics", {}).get("net_profit", observed_cash))
    difference = observed_cash - native_cash
    if abs(difference) > .025:
        global_issues.append("Position net cash differs from native case net cash")
    for week in issues:
        issues[week].extend(global_issues)
    weeks, missing = list(calendar), [week for week in calendar if issues[week]]
    diagnostics = _run(records, weeks, missing, tested, int(paths), initial,
                       native_audit._epoch(result["start"]), native_audit._epoch(result["end_exclusive"]))
    complete_weeks = [week for week in weeks if week not in set(missing)]
    sensitivity = None
    if missing and complete_weeks:
        sensitivity = {"label": "Conditional complete-cash-week sensitivity only; missing/unexplained weeks removed and calendar compressed, not full-case evidence",
                       "dropped_week_ids": missing,
                       "diagnostics": _run([r for r in records if r["week_id"] in set(complete_weeks)],
                                           complete_weeks, [], tested, int(paths), initial)}
    status = ("no_complete_scheduled_weekends" if not weeks else "unavailable_incomplete_closed_cash_history"
              if missing else "complete_closed_balance_cash_diagnostics")
    return {"tag": tag, "status": status,
            "methodological_supplement": {"added_after_selection_freeze": True, "alpha_or_selection_use": False,
                                         "changes_frozen_native_path_gate": False, "promotion_gate_waiver": False,
                                         "scope": "Known native closed cash ONLY, independent of absent intratrade M1 samples"},
            "case": {"candidate": candidate, "start": result["start"], "end_exclusive": result["end_exclusive"],
                     "native_model": result.get("native", {}).get("manifest", {}).get("model")},
            "tested_unique_configurations": tested,
            "sources": {"results": {"path": str(result_path), "sha256": native_audit._sha(result_path)},
                        "decisions": {"path": str(decision_path), "sha256": native_audit._sha(decision_path) if decision_path.exists() else None},
                        "selection": {"path": str(selection_path), "sha256": native_audit._sha(selection_path)},
                        "frozen_native_adapter": {"path": str(Path(native_audit.__file__)), "sha256": native_audit._sha(native_audit.__file__)}},
            "coverage": {"scheduled_week_ids": weeks, "scheduled_weeks": len(weeks),
                         "censored_incomplete_weeks": censored, "documented_zero_weeks": documented_zero,
                         "missing_week_ids": missing, "missing_reasons": {w: issues[w] for w in missing},
                         "observed_native_positions": len(positions), "normalized_closed_positions": len(records),
                         "global_issues": global_issues, "m1_equity_read": False},
            "normalization_audit": audit,
            "cash_reconciliation": {"native_position_net_cash": observed_cash, "native_case_net_cash": native_cash,
                                    "difference": difference, "costs_counted_once": True},
            "diagnostics": diagnostics, "conditional_complete_cash_week_sensitivity": sensitivity,
            "floating_equity_drawdown": {"status": "unavailable_in_cash_only_supplement", "value": None},
            "prop_account_probabilities": {"status": "unavailable_without_intratrade_daily_equity", "value": None},
            "limitations": [
                native_audit.COST_BASIS + ".",
                "Native net cash is divided by BEFORE-entry-request balance, including down-rounded unallocated cash; it is not stop-defined R.",
                "Closed DD recognizes the whole position's cash including opening costs at final close; actual cash-posting DD and floating-equity DD are different statistics.",
                "No M1 equity file is read and no absent intratrade path is interpolated. This supplement cannot infer floating DD, daily equity loss or prop-account pass/blow-up probabilities.",
                "Resampling continuously scales observed account returns; broker lot rounding, fills, commissions and financing are not re-executed under each path.",
                "Historical financing is not reconstructed. Results use the current native tester cost specification only.",
                "Unexplained or endpoint-missing weekends remain missing; documented applicable filters/warmup alone can be zero.",
                "The inspected 2024-10-17 to 2026-10-17 period is retrospective evaluation, not untouched OOS.",
                "This post-freeze methodological supplement does not alter strategy selection, failed validation, frozen tests or promotion gates.",
                "Empirical Monte Carlo summaries are not future success probabilities."]}
