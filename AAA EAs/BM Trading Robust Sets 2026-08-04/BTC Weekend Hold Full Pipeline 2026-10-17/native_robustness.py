"""Offline robustness adapter for completed native BTC weekend research cases.

No MT5 imports, execution, file writes, or automatic directory discovery.  The
caller explicitly selects a completed case.  Native position net cash is used
ONCE, divided by cash observed immediately BEFORE its entry request.  This is
an account-return series, not a stop-defined R series or historical financing
reconstruction.  Missing receipts and missing held-minute samples never become
zero-return weekends.
"""
from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
from zoneinfo import ZoneInfo

import robustness

NY = ZoneInfo("America/New_York")
UTC = timezone.utc
COST_BASIS = "Native net cash including recorded commission/swap/fee once; current tester cost specification, not historical financing"
FILTER_REASONS = {
    "skip_ema50": ("filter_mode", {1}),
    "skip_ema200": ("filter_mode", {2}),
    "skip_adx": ("filter_mode", {3, 4, 5}),
    "skip_di": ("filter_mode", {5}),
    "skip_atr_percentile": ("filter_mode", {6}),
    "skip_spread_cap": ("filter_mode", {7}),
    "skip_signal_not_bullish": ("entry_mode", {1}),
    "skip_signal_no_momentum": ("entry_mode", {2}),
}


def _sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _epoch(value):
    if isinstance(value, (int, float)):
        return int(value)
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return int(parsed.timestamp())


def _number(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("Non-finite native audit number")
    return result


def _integer(value):
    result = _number(value)
    if int(result) != result:
        raise ValueError("Expected an integer native audit field")
    return int(result)


def _msc(row, key="time_msc", epoch_key="epoch"):
    return _integer(row[key]) if row.get(key) not in (None, "") else _integer(row[epoch_key]) * 1000


def _rows(path):
    with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as stream:
        yield from csv.DictReader(stream)


def weekend_calendar(candidate, start, end):
    """Independent NY wall-clock schedule, including the 47/49-hour DST weekends."""
    begin, finish = _epoch(start), _epoch(end)
    if finish <= begin:
        raise ValueError("Invalid case boundaries")
    entry_minute = _integer(candidate["entry_minute_ny"])
    exit_minute = _integer(candidate["exit_minute_ny"])
    if not (0 <= entry_minute < 1440 and 0 <= exit_minute < 1440):
        raise ValueError("NY minute must be inside a local day")
    day = datetime.fromtimestamp(begin, NY).date()
    last_day = datetime.fromtimestamp(finish, NY).date()
    scheduled, censored = [], []
    while day <= last_day:
        if day.weekday() == 4:
            midnight = datetime.combine(day, datetime.min.time(), NY)
            sunday = datetime.combine(day + timedelta(days=2), datetime.min.time(), NY)
            entry = int((midnight + timedelta(minutes=entry_minute)).timestamp())
            exit_time = int((sunday + timedelta(minutes=exit_minute)).timestamp())
            row = {"week_id": day.isoformat(), "entry_epoch": entry, "scheduled_exit_epoch": exit_time,
                   "duration_hours": (exit_time - entry) / 3600}
            if entry < finish:
                if entry < begin or exit_time >= finish:  # Native EA rejects exit >= InpTo.
                    censored.append(row | {"reason": "before_case_start" if entry < begin else "exit_not_strictly_before_case_end"})
                else:
                    scheduled.append(row)
        day += timedelta(days=1)
    return scheduled, censored


def _documented_zero(decision, candidate):
    reason = decision.get("reason", "")
    if reason in FILTER_REASONS:
        field, choices = FILTER_REASONS[reason]
        return int(candidate.get(field, 0)) in choices
    if reason == "skip_percentile_warmup" and int(candidate.get("filter_mode", 0)) == 6:
        # The receipt proves insufficient expanding-rank history.  The other
        # warmup-or-incomplete reason cannot distinguish startup from gaps.
        try:
            return 0 <= _integer(decision["valid_atr_ratios"]) < 61
        except (KeyError, ValueError, TypeError):
            return False
    if reason == "skip_entry_feature_warmup_or_incomplete":
        # New native receipts distinguish initial count insufficiency from a
        # gappy/incomplete lookback.  Older receipts cannot make this proof.
        try:
            count = _integer(decision["processed_feature_bars"])
            needed = _integer(decision["required_entry_lookback"])
            return 0 <= count < needed and needed > 0 and _integer(decision["entry_lookback_valid"]) == 0
        except (KeyError, ValueError, TypeError):
            return False
    return False


def _validate_costs(position):
    recorded = _number(position["net_profit"])
    components = [_number(position[k]) for k in ("gross_profit", "commission", "swap", "fee")]
    if abs(sum(components) - recorded) > .011:
        raise ValueError("Native position net cash does not reconcile its cost components")
    return recorded


def _request_for(position, requests, schedule):
    opening = _msc(position, "open_time_msc", "open_epoch")
    linked = []
    for request in requests:
        stamp = _msc(request)
        if (_integer(request.get("scheduled_exit_epoch", 0)) == schedule["scheduled_exit_epoch"]
                and schedule["entry_epoch"] * 1000 <= stamp < (schedule["entry_epoch"] + 60) * 1000
                and 0 <= opening - stamp <= 3000):
            linked.append(request)
    if len(linked) != 1:
        raise ValueError("Missing or ambiguous native entry-request-to-position linkage")
    request = linked[0]
    if request.get("reason") != "entry_request":
        raise ValueError("Denominator is not a before-order entry request")
    return request


def _path_samples(path, positions):
    """Read samples once; never borrow another position's account equity."""
    owners = {str(p["position_id"]): p for p in positions}
    if len(owners) != len(positions):
        raise ValueError("Duplicate native position ID")
    samples = {pid: [] for pid in owners}
    row_count = 0
    first = last = None
    invalid = 0
    for row in _rows(path):
        row_count += 1
        try:
            at = _integer(row["epoch"])
            stamp = _msc(row)
            eq = _number(row["equity"])
            first = at if first is None else min(first, at)
            last = at if last is None else max(last, at)
            pid = str(row.get("position_id", "0"))
            if pid not in owners:
                continue
            position = owners[pid]
            lo = _msc(position, "open_time_msc", "open_epoch")
            hi = _msc(position, "close_time_msc", "close_epoch")
            if lo <= stamp <= hi:
                if eq < 0:
                    raise ValueError("Negative account equity")
                samples[pid].append({"epoch": at, "time_msc": stamp, "equity": eq})
        except (KeyError, ValueError, TypeError):
            invalid += 1
    for values in samples.values():
        values.sort(key=lambda x: x["time_msc"])
    return samples, {"rows": row_count, "first_snapshot_epoch": first,
                     "last_snapshot_epoch": last, "invalid_rows": invalid}


def analyze_native_case(root, tag, paths=10000):
    """Return diagnostics for one explicit completed case; does not save or run it.

    This function is deliberately not a CLI and does not scan tags.  In
    particular, importing it cannot open OOS case results or evaluate prices.
    """
    root = Path(root).resolve()
    if (not isinstance(tag, str) or tag in (".", "..")
            or re.fullmatch(r"[A-Za-z0-9_.-]+", tag) is None):
        raise ValueError("A single explicit native case tag is required")
    if isinstance(paths, bool) or int(paths) != paths or paths < 1:
        raise ValueError("A positive integer path count is required")
    case_dir = root / "native" / tag
    result_path = case_dir / "results.json"
    equity_path = case_dir / "equity-m1.csv.gz"
    decision_path = case_dir / "decisions.csv.gz"
    selection_path = root / "SELECTION.json"
    result = json.loads(result_path.read_text(encoding="utf-8-sig"))
    selection = json.loads(selection_path.read_text(encoding="utf-8-sig"))
    tested = selection.get("unique_configurations")
    if isinstance(tested, bool) or not isinstance(tested, int) or tested < 1:
        raise ValueError("SELECTION must record the actual positive unique configuration count")
    candidate = result["candidate"]
    schedule, censored = weekend_calendar(candidate, result["start"], result["end_exclusive"])
    by_week = {row["week_id"]: row for row in schedule}
    by_exit = {row["scheduled_exit_epoch"]: row["week_id"] for row in schedule}
    decisions = list(_rows(decision_path)) if decision_path.exists() else []
    requests = result.get("entry_requests", [])
    positions = result.get("trades", [])
    reason_counts = {}
    decision_weeks = {week: [] for week in by_week}
    malformed_decisions = 0
    for decision in decisions:
        reason = str(decision.get("reason", ""))
        reason_counts[reason] = reason_counts.get(reason, 0) + 1
        try:
            week = by_exit.get(_integer(decision["scheduled_exit_epoch"]))
            if week is not None:
                at = _integer(decision["epoch"])
                if by_week[week]["entry_epoch"] <= at < by_week[week]["entry_epoch"] + 60:
                    decision_weeks[week].append(decision)
        except (KeyError, ValueError, TypeError):
            malformed_decisions += 1
    issues = {week: [] for week in by_week}
    position_weeks = {week: [] for week in by_week}
    outside = []
    for position in positions:
        try:
            week = datetime.fromtimestamp(_integer(position["open_epoch"]), NY).date().isoformat()
            if week not in by_week:
                outside.append(str(position.get("position_id")))
            else:
                position_weeks[week].append(position)
        except (KeyError, ValueError, TypeError):
            outside.append(str(position.get("position_id")))
    # Native one-position ownership must hold across the whole case, not just
    # within the selected week.  Open positions cannot be used as closed data.
    ordered = sorted(positions, key=lambda p: _msc(p, "open_time_msc", "open_epoch"))
    overlap = any(a.get("close_epoch") is None or _msc(a, "close_time_msc", "close_epoch") >
                  _msc(b, "open_time_msc", "open_epoch") for a, b in zip(ordered, ordered[1:]))
    eligible, records, audit = [], [], []
    initial = _number(result.get("metrics", {}).get("initial_balance", 10000))
    if initial <= 0:
        raise ValueError("Invalid initial native balance")
    running_cash = initial
    for position in ordered:
        week = datetime.fromtimestamp(_integer(position["open_epoch"]), NY).date().isoformat()
        if week not in by_week:
            continue
        reasons = issues[week]
        try:
            if len(position_weeks[week]) != 1:
                raise ValueError("Multiple native positions in one scheduled week")
            if not position.get("closed") or position.get("close_epoch") is None:
                raise ValueError("Unclosed native position")
            if position.get("end_of_test_liquidation") or position.get("exit_reason") == "test-end":
                raise ValueError("Administrative test-end liquidation is not a natural completed weekend")
            if overlap:
                raise ValueError("Overlapping native position ownership")
            net = _validate_costs(position)
            request = _request_for(position, requests, by_week[week])
            cash = _number(request["balance"])
            if cash <= 0 or net / cash < -1:
                raise ValueError("Invalid before-entry cash / account-relative return")
            if abs(cash - running_cash) > .025:
                raise ValueError("Before-entry request balance does not reconcile prior whole-position cash")
            close = _integer(position["close_epoch"])
            if close <= _integer(position["open_epoch"]) or close >= _epoch(result["end_exclusive"]):
                raise ValueError("Invalid closed-position case boundary")
            if position.get("scheduled_exit_epoch") not in (None, by_week[week]["scheduled_exit_epoch"]):
                raise ValueError("Native position scheduled exit differs from NY calendar")
            record = {"week_id": week, "position_id": str(position["position_id"]),
                      "entry_epoch": _integer(request["epoch"]), "exit_epoch": close,
                      "return_per_notional": net / cash, "native_net_profit": net,
                      "before_entry_request_balance": cash, "cost_basis": COST_BASIS,
                      "normalization": "native net position cash / BEFORE-entry-request account cash; not stop-defined R"}
            records.append(record)
            eligible.append(position)
            audit.append({"week_id": week, "position_id": str(position["position_id"]),
                          "before_entry_request_balance": cash, "native_net_profit": net,
                          "account_return": net / cash, "request_epoch": record["entry_epoch"],
                          "open_epoch": _integer(position["open_epoch"]), "close_epoch": close,
                          "commission": _number(position["commission"]), "swap": _number(position["swap"]),
                          "fee": _number(position["fee"]), "cost_components_reconcile": True})
        except (KeyError, ValueError, TypeError) as exc:
            reasons.append(str(exc))
        # Preserve native cash chronology even if this position's path/receipt
        # is unusable; later denominators must not be reset or falsely guessed.
        if position.get("closed"):
            try:
                running_cash += _validate_costs(position)
            except (KeyError, ValueError, TypeError):
                pass
    zero = {}
    for week in by_week:
        if position_weeks[week]:
            continue
        receipts = decision_weeks[week]
        skip_receipts = [d for d in receipts if str(d.get("reason", "")).startswith("skip_")]
        if (len(skip_receipts) == 1 and _documented_zero(skip_receipts[0], candidate)
                and not any(d.get("reason") in ("entry_request", "entry_filled", "entry_rejected") for d in receipts)):
            zero[week] = skip_receipts[0]["reason"]
        else:
            observed = sorted({str(d.get("reason", "")) for d in receipts})
            issues[week].append("No uniquely documented valid filter/warmup zero" + (": " + ", ".join(observed) if observed else "; no entry-minute decision receipt"))
    equity_meta = {"rows": 0, "invalid_rows": 0, "first_snapshot_epoch": None, "last_snapshot_epoch": None}
    if equity_path.exists():
        samples, equity_meta = _path_samples(equity_path, eligible)
    else:
        samples = {}
        for record in records:
            issues[record["week_id"]].append("Missing native sampled-M1 equity file")
    for record, position, receipt in zip(records, eligible, audit):
        pid, week = record["position_id"], record["week_id"]
        values = samples.get(pid, [])
        cash = record["before_entry_request_balance"]
        record["intratrade_path"] = [{"epoch": v["epoch"], "equity_factor": v["equity"] / cash} for v in values]
        # Endpoint minutes are not falsely required to have a held-position
        # snapshot after the stop/close has already filled.  All fully held
        # interior minutes are required; gaps remain unavailable evidence.
        first_minute = _integer(position["open_epoch"]) // 60
        last_minute = record["exit_epoch"] // 60
        present = {v["epoch"] // 60 for v in values}
        missing = [minute * 60 for minute in range(first_minute + 1, last_minute) if minute not in present]
        if not values:
            issues[week].append("No owned-position sampled equity observations")
        if missing:
            issues[week].append("Missing fully-held M1 equity minutes: " + str(len(missing)))
        receipt.update({"owned_equity_samples": len(values), "missing_fully_held_minutes": len(missing),
                        "first_missing_minute_epoch": missing[0] if missing else None,
                        "sampled_min_equity_factor": min((v["equity"] / cash for v in values), default=None),
                        "sampled_max_equity_factor": max((v["equity"] / cash for v in values), default=None)})
    global_issues = []
    if outside:
        global_issues.append("Native positions outside the complete scheduled calendar: " + ", ".join(outside))
    if equity_meta["invalid_rows"]:
        global_issues.append("Invalid sampled equity rows: " + str(equity_meta["invalid_rows"]))
    if not decision_path.exists():
        global_issues.append("Missing decision audit; absent weekends cannot be certified as filtered zero")
    if malformed_decisions:
        global_issues.append("Malformed native decision audit rows: " + str(malformed_decisions))
    if result.get("decision_counts") is not None and result["decision_counts"] != reason_counts:
        global_issues.append("Full decision audit counts differ from the native results receipt")
    metrics = result.get("metrics", {})
    expected_cash = _number(metrics.get("net_profit", sum(_number(p["net_profit"]) for p in positions)))
    all_position_cash = sum(_number(p["net_profit"]) for p in positions)
    cash_difference = all_position_cash - expected_cash
    if abs(cash_difference) > .025:
        global_issues.append("Native position cash does not reconcile case net profit")
    if global_issues:
        for week in issues:
            issues[week].extend(global_issues)
    missing_ids = [week for week in by_week if issues[week]]
    all_ids = list(by_week)
    diagnostics = robustness.analyze_robustness(
        records, tested_configurations=tested, scheduled_week_ids=all_ids,
        missing_week_ids=missing_ids, paths=int(paths), initial_balance=initial,
        period_start_epoch=_epoch(result["start"]), period_end_epoch=_epoch(result["end_exclusive"]))
    sensitivity = None
    complete_ids = [week for week in all_ids if week not in set(missing_ids)]
    if missing_ids and complete_ids:
        observed = [r for r in records if r["week_id"] in set(complete_ids)]
        sensitivity = {"label": "Complete-observed-week sensitivity ONLY; missing weeks removed, calendar compressed, not full-case evidence",
                       "dropped_week_ids": missing_ids,
                       "diagnostics": robustness.analyze_robustness(observed, tested_configurations=tested,
                           scheduled_week_ids=complete_ids, paths=int(paths), initial_balance=initial)}
    sources = {"results": {"path": str(result_path), "sha256": _sha(result_path)},
               "selection": {"path": str(selection_path), "sha256": _sha(selection_path)}}
    for key, path in (("equity_m1", equity_path), ("decisions", decision_path)):
        sources[key] = {"path": str(path), "sha256": _sha(path) if path.exists() else None}
    status = ("no_complete_scheduled_weekends" if not all_ids else "complete_native_diagnostics"
              if not missing_ids else "unavailable_incomplete_native_history")
    return {"tag": tag, "status": status,
            "case": {"candidate": candidate, "start": result["start"], "end_exclusive": result["end_exclusive"],
                     "native_model": result.get("native", {}).get("manifest", {}).get("model"),
                     "last_quote_utc": result.get("last_quote_utc"), "sizing": result.get("sizing")},
            "tested_unique_configurations": tested, "sources": sources,
            "coverage": {"scheduled_week_ids": all_ids, "scheduled_weeks": len(all_ids),
                         "censored_incomplete_weeks": censored, "documented_zero_weeks": zero,
                         "missing_week_ids": missing_ids, "missing_reasons": {w: issues[w] for w in missing_ids},
                         "observed_native_positions": len(positions), "normalized_closed_positions": len(records),
                         "owned_sampled_equity": equity_meta, "decision_counts": reason_counts,
                         "global_issues": global_issues},
            "normalization_audit": audit,
            "cash_reconciliation": {"all_native_position_net_cash": all_position_cash,
                                    "case_net_cash": expected_cash, "difference": cash_difference,
                                    "costs_counted": "net_profit includes gross_profit + commission + swap + fee exactly once"},
            "observed_native_metrics": metrics,
            "diagnostics": diagnostics, "complete_observed_week_sensitivity": sensitivity,
            "limitations": [
                COST_BASIS + ".",
                "Returns are native net cash / before-entry request cash, not nominal notional return or stop-defined R.",
                "Block resampling scales observed account-relative returns continuously; it does not rerun broker lot rounding, fee tiers, fills or margin.",
                "Intratrade paths use position-owned M1 AccountEquity snapshots only; no interpolation, not true every-tick equity/DD.",
                "Only documented applicable signal/filter skips and proven initial/percentile warmup are zero weeks. Ambiguous warmup/incomplete or failed entries remain missing.",
                "Administrative incomplete weekends and forced tester-end liquidations do not certify natural completion.",
                "The 2024-10-17 to 2026-10-17 evaluation period was previously inspected; it is retrospective, not genuinely untouched.",
                "Monte Carlo outputs are historical empirical diagnostics, not future success probabilities or prop-firm certification."]}
