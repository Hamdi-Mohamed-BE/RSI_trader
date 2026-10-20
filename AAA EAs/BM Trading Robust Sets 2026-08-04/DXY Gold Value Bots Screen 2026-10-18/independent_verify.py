"""Independent research-screen audit; intentionally does not import run.py.

Written from PLAN before inspecting engine results.  No trading or MT5 access.
"""
from __future__ import annotations

import bisect
import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOUR = 3600
DAY = 86400


def epoch(value):
    if isinstance(value, (int, float)):
        return float(value)
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def close_map(bar_rows):
    """Input bars are UTC OPEN timestamps. Reject duplicates or bad prices."""
    result = {}
    prior = None
    for row in bar_rows:
        opening = epoch(row["time"])
        closing = opening + HOUR
        price = float(row["close"])
        if prior is not None and opening <= prior:
            raise AssertionError("Bars must be strictly increasing and unique")
        if opening % HOUR or not math.isfinite(price) or price <= 0:
            raise AssertionError("Invalid H1 open timestamp/close")
        result[closing] = price
        prior = opening
    return result


def valid_returns(prices):
    """Only genuine adjacent clock-hour closes contribute one-hour returns."""
    return {t: math.log(p / prices[t - HOUR])
            for t, p in prices.items() if t - HOUR in prices}


def independent_feature(entry, dxy, gold, *, history_anchor="entry"):
    """Pure independent implementation of the predeclared H1 feature.

    Result exposes raw endpoints so the audit can prove causality.
    """
    entry = epoch(entry)
    eligible = [t for t in dxy if t <= entry]
    empty = {"valid": False, "reason": None, "latest_close": None,
             "momentum": None, "sigma": None, "threshold": None,
             "correlation": None, "correlation_count": 0,
             "correlation_valid": False, "volatility_endpoints": [],
             "correlation_endpoints": []}
    if not eligible:
        return dict(empty, reason="no_closed_dxy")
    last = max(eligible)
    result = dict(empty, latest_close=last)
    if entry - last > HOUR:
        return dict(result, reason="stale_dxy")
    if any(last - n * HOUR not in dxy for n in range(4)):
        return dict(result, reason="signal_hour_gap")
    start = last - 3 * HOUR
    ret = valid_returns(dxy)
    anchor = entry if history_anchor == "entry" else start
    endpoints = sorted(t for t in ret if anchor - 10 * DAY <= t <= start)[-120:]
    result["volatility_endpoints"] = endpoints
    if len(endpoints) != 120:
        return dict(result, reason="insufficient_volatility_history")
    sigma = statistics.stdev([ret[t] for t in endpoints])
    result["sigma"] = sigma
    if not math.isfinite(sigma) or sigma <= 0:
        return dict(result, reason="zero_or_invalid_variance")
    result.update(valid=True, reason="valid", momentum=math.log(dxy[last] / dxy[start]),
                  threshold=math.sqrt(3) * sigma)
    gold_ret = valid_returns(gold)
    paired = sorted(t for t in ret if entry - 10 * DAY <= t <= last and t in gold_ret)[-120:]
    result.update(correlation_count=len(paired), correlation_endpoints=paired)
    if len(paired) >= 100 and entry - paired[-1] <= HOUR:
        dx = [ret[t] for t in paired]
        gx = [gold_ret[t] for t in paired]
        dmean, gmean = statistics.mean(dx), statistics.mean(gx)
        numerator = sum((d - dmean) * (g - gmean) for d, g in zip(dx, gx))
        denominator = math.sqrt(sum((d - dmean) ** 2 for d in dx)
                                * sum((g - gmean) ** 2 for g in gx))
        if denominator > 0 and math.isfinite(denominator):
            result.update(correlation=numerator / denominator, correlation_valid=True)
    return result


def independent_veto(feature, side, gated=False):
    if not feature["valid"]:
        return False
    if side not in (-1, 1):
        raise AssertionError("Expected direction +1/-1")
    conflict = (side == 1 and feature["momentum"] >= feature["threshold"]) or (
        side == -1 and feature["momentum"] <= -feature["threshold"])
    if gated:
        return bool(conflict and feature["correlation_valid"]
                    and feature["correlation"] <= -0.25)
    return bool(conflict)


def independent_metrics(rows, start, end):
    """Rows contain close epoch, id, pnl, and risk-normalized net_r."""
    start, end = epoch(start), epoch(end)
    ordered = sorted(rows, key=lambda x: (x["close"], x.get("open", 0),
                                          x.get("key", ""), int(x.get("position_id", 0))))
    cash = 10000.0
    peak = cash
    maximum_cash_dd = 0.0
    maximum_pct_dd = 0.0
    gross_wins = gross_losses = net = 0.0
    winners = losers = zeros = win_run = loss_run = max_wins = max_losses = 0
    daily = defaultdict(float)
    curve = [{"time": start, "balance": cash}]
    for row in ordered:
        value = float(row["pnl"])
        if not math.isfinite(value):
            raise AssertionError("Non-finite P&L")
        net += value
        if value > 1e-10:
            winners += 1
            gross_wins += value
            win_run += 1
            loss_run = 0
        elif value < -1e-10:
            losers += 1
            gross_losses -= value
            loss_run += 1
            win_run = 0
        else:
            zeros += 1
            win_run = loss_run = 0
        max_wins = max(max_wins, win_run)
        max_losses = max(max_losses, loss_run)
        cash += value
        peak = max(peak, cash)
        maximum_cash_dd = max(maximum_cash_dd, peak - cash)
        maximum_pct_dd = max(maximum_pct_dd, (peak - cash) / peak * 100 if peak > 0 else 0)
        day = int(row["close"] // DAY) * DAY
        daily[day] += value
        curve.append({"time": row["close"], "balance": cash})
    daily_returns = []
    daily_balance = 10000.0
    valid_sharpe = True
    for day in range(int(start // DAY) * DAY, int(end // DAY) * DAY, DAY):
        if daily_balance <= 0:
            valid_sharpe = False
            break
        daily_returns.append(daily[day] / daily_balance)
        daily_balance += daily[day]
    sharpe = None
    if (valid_sharpe and all(p["balance"] > 0 for p in curve)
            and len(daily_returns) > 1 and statistics.stdev(daily_returns) > 0):
        sharpe = statistics.mean(daily_returns) / statistics.stdev(daily_returns) * math.sqrt(365)
    return {"trades": len(rows), "wins": winners, "losses": losers, "zeros": zeros,
            "win_rate": winners / len(rows) * 100 if rows else 0,
            "pf": gross_wins / gross_losses if gross_losses else None,
            "net": net, "return_pct": net / 100,
            "end_balance": cash, "max_closed_dd": maximum_cash_dd,
            "max_closed_dd_pct": maximum_pct_dd,
            "max_win_streak": max_wins, "max_loss_streak": max_losses,
            "expectancy": net / len(rows) if rows else 0,
            "expectancy_r": statistics.mean([r["net_r"] for r in rows]) if rows else 0,
            "sharpe": sharpe, "curve": curve,
            "daily": {datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d"): v
                      for t, v in sorted(daily.items())}}


def main():
    checks = 0
    def check(condition, detail):
        nonlocal checks
        checks += 1
        if not condition:
            raise AssertionError(detail)

    def equal(actual, expected, detail):
        if isinstance(expected, (float, int)) and not isinstance(expected, bool):
            check(isinstance(actual, (float, int)) and math.isfinite(actual)
                  and math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-8),
                  f"{detail}: actual={actual!r}, independent={expected!r}")
        else:
            check(actual == expected, f"{detail}: actual={actual!r}, independent={expected!r}")

    def load(name):
        return json.loads((HERE / name).read_text(encoding="utf-8-sig"))

    plan = load("PLAN.json")
    source = load("INPUTS.json")
    result = load("RESULTS.json")
    freeze = load("FROZEN.json")
    for group in ("files", "source_files"):
        for path, expected in freeze[group].items():
            equal(digest(path), expected, f"Frozen hash {path}")
    for path, expected in source["source_hashes"].items():
        equal(digest(path), expected, f"Source evidence hash {path}")
    equal(result["plan_sha256"], digest(HERE / "PLAN.json"), "Output plan SHA")
    equal(result["inputs_sha256"], digest(HERE / "INPUTS.json"), "Output inputs SHA")
    equal(result["frozen_sha256"], digest(HERE / "FROZEN.json"), "Output freeze SHA")
    check(plan["rules"]["threshold_search"] is False, "No threshold search")
    equal(plan["metrics"]["initial_reference_balance"], 10000, "Reference initial balance")
    equal(plan["metrics"]["fixed_initial_stop_risk"], 100, "Fixed fractional risk")
    raw_dxy = load("data/DXY-H1.json")["bars"]
    raw_gold = load("data/XAUUSD-H1.json")["bars"]
    dxy, gold = close_map(raw_dxy), close_map(raw_gold)
    equal(result["data_audit"]["dxy"]["bars"], len(raw_dxy), "DXY bar count")
    equal(result["data_audit"]["gold"]["bars"], len(raw_gold), "Gold bar count")
    equal(result["data_audit"]["dxy"]["valid_one_hour_returns"], len(valid_returns(dxy)), "DXY return count")
    equal(result["data_audit"]["gold"]["valid_one_hour_returns"], len(valid_returns(gold)), "Gold return count")

    rows = source["rows"]
    def rowid(r):
        return f"{r['key']}:{int(r['position_id'])}"
    def order(r):
        return (int(r["cl"]), int(r["op"]), r["key"], int(r["position_id"]))
    equal(len(set(rowid(r) for r in rows)), len(rows), "Unique source positions")
    feature_rows = result["features"]
    actual_features = {r["id"]: r for r in feature_rows}
    equal(len(actual_features), len(feature_rows), "Unique feature IDs")
    equal(set(actual_features), set(rowid(r) for r in rows), "Complete feature membership")
    reason_map = {"no_closed_dxy": "no_completed_dxy_bar", "stale_dxy": "stale_dxy",
                  "signal_hour_gap": "nonconsecutive_signal_hours",
                  "insufficient_volatility_history": "insufficient_normalizer",
                  "zero_or_invalid_variance": "zero_or_invalid_volatility", "valid": "valid"}
    expected_features = {}
    for row in rows:
        rid = rowid(row)
        actual = actual_features[rid]
        check(row["key"] in plan["scope"], f"Scope {rid}")
        check(int(row["cl"]) >= int(row["op"]), f"Natural close follows entry {rid}")
        check(float(row["unit_risk"]) > 0, f"Positive source stop risk {rid}")
        check(all(math.isfinite(float(row[k])) for k in ("unit_risk", "unit_gross", "unit_comm", "unit_swap")), f"Finite source cash {rid}")
        check(row["side"] in ("Long", "Short"), f"Valid side {rid}")
        feature = independent_feature(row["op"], dxy, gold)
        side = 1 if row["side"] == "Long" else -1
        feature["primary_veto"] = independent_veto(feature, side)
        feature["secondary_veto"] = independent_veto(feature, side, gated=True)
        expected_features[rid] = feature
        for key in ("key", "side", "op", "cl"):
            equal(actual[key], row[key], f"Feature identity {rid}/{key}")
        equal(actual["entry_epoch"], row["op"], f"Feature entry epoch {rid}")
        equal(actual["valid"], feature["valid"], f"Validity {rid}")
        equal(actual["reason"], reason_map[feature["reason"]], f"Reason {rid}")
        for key in ("primary_veto", "secondary_veto", "correlation_valid"):
            equal(actual[key], feature[key], f"Feature {rid}/{key}")
        if feature["latest_close"] is not None:
            equal(actual["dxy_last_close_epoch"], feature["latest_close"], f"Closed endpoint {rid}")
            check(actual["dxy_last_close_epoch"] <= row["op"], f"No future DXY endpoint {rid}")
        if feature["valid"]:
            for a, b in (("momentum", "momentum"), ("volatility", "sigma"), ("threshold", "threshold")):
                equal(actual[a], feature[b], f"Numeric feature {rid}/{a}")
            equal(actual["normalizer_n"], 120, f"Full normalizer {rid}")
            equal(actual["normalizer_first_epoch"], feature["volatility_endpoints"][0], f"Normalizer first {rid}")
            equal(actual["normalizer_last_epoch"], feature["volatility_endpoints"][-1], f"Normalizer last {rid}")
            equal(actual["correlation_n"], feature["correlation_count"], f"Paired count {rid}")
            check(actual["normalizer_last_epoch"] <= actual["signal_start_epoch"] <= actual["signal_end_epoch"] <= row["op"], f"Signal/normalizer causality {rid}")
        if feature["correlation_valid"]:
            equal(actual["correlation"], feature["correlation"], f"Correlation {rid}")
            equal(actual["correlation_last_epoch"], feature["correlation_endpoints"][-1], f"Correlation end {rid}")
            check(0 <= row["op"] - actual["correlation_last_epoch"] <= HOUR, f"Fresh past-only correlation {rid}")
        check(not feature["secondary_veto"] or feature["primary_veto"], f"Secondary veto subset {rid}")

    def normalized(selected, stress):
        out = []
        for r in selected:
            numerator = float(r["unit_gross"]) + float(r["unit_comm"]) + float(r["unit_swap"])
            if stress:
                numerator -= 20
                numerator += min(0, float(r["unit_swap"]))
            nr = numerator / float(r["unit_risk"])
            out.append({"id": rowid(r), "key": r["key"], "position_id": int(r["position_id"]),
                        "open": int(r["op"]), "close": int(r["cl"]), "net_r": nr,
                        "pnl": nr * 100, "side": r["side"]})
        return out

    def metric_check(actual, selected, start, end, stress, label):
        independent_rows = normalized(selected, stress)
        expected = independent_metrics(independent_rows, start, end)
        n = len(selected)
        pairs = (("trades", "trades"), ("wins", "wins"), ("losses", "losses"),
                 ("breakevens", "zeros"), ("profit_factor", "pf"), ("net_profit", "net"),
                 ("closed_return_pct", "return_pct"), ("ending_closed_reference_balance", "end_balance"),
                 ("max_closed_dd_cash", "max_closed_dd"), ("max_closed_dd_pct", "max_closed_dd_pct"),
                 ("max_winning_streak", "max_win_streak"), ("max_losing_streak", "max_loss_streak"),
                 ("closed_daily_sharpe", "sharpe"))
        for a, b in pairs:
            equal(actual[a], expected[b], f"{label}/{a}")
        equal(actual["win_rate_pct"], expected["win_rate"] if n else None, f"{label}/win_rate")
        equal(actual["expectancy_r"], expected["expectancy_r"] if n else None, f"{label}/expectancy_r")
        equal(actual["net_r"], sum(r["net_r"] for r in independent_rows), f"{label}/net_r")
        equal(actual["longs"], sum(r["side"] == "Long" for r in selected), f"{label}/longs")
        equal(actual["shorts"], sum(r["side"] == "Short" for r in selected), f"{label}/shorts")
        wins = [r["pnl"] for r in independent_rows if r["pnl"] > 1e-10]
        losses = [r["pnl"] for r in independent_rows if r["pnl"] < -1e-10]
        equal(actual["average_win"], statistics.mean(wins) if wins else None, f"{label}/average_win")
        equal(actual["average_loss"], statistics.mean(losses) if losses else None, f"{label}/average_loss")
        days = int((end - start) // DAY)
        equal(actual["calendar_days"], days, f"{label}/calendar_days")
        equal(actual["average_closed_trades_per_calendar_day"], n / days, f"{label}/trades_per_day")
        return expected

    periods = {p["id"]: p for p in plan["periods"]}
    outputs = result["results"]
    cases = {(r["period"], r["ea"], r["cost"], r["view"]): r for r in outputs}
    expected_keys = {(p, ea, cost, view) for p in periods for ea in (*plan["scope"], "combined")
                     for cost in ("recorded", "stress") for view in ("baseline", "primary", "secondary")}
    equal(set(cases), expected_keys, "Every predeclared comparison exists")
    equal(len(outputs), len(expected_keys), "No duplicate result cases")
    for case, actual in cases.items():
        periodid, ea, cost, view = case
        p = periods[periodid]
        start, end = epoch(p["start"]), epoch(p["end_exclusive"])
        stress = cost == "stress"
        candidates = [r for r in rows if r["op"] >= start and r["cl"] < end
                      and (ea == "combined" or r["key"] == ea)]
        vk = "primary_veto" if view == "primary" else "secondary_veto"
        selected = candidates if view == "baseline" else [r for r in candidates if not expected_features[rowid(r)][vk]]
        vetoed = [] if view == "baseline" else [r for r in candidates if expected_features[rowid(r)][vk]]
        valid = [r for r in candidates if expected_features[rowid(r)]["valid"]
                 and (view != "secondary" or expected_features[rowid(r)]["correlation_valid"])]
        selected_valid = valid if view == "baseline" else [r for r in valid if not expected_features[rowid(r)][vk]]
        label = "/".join(case)
        expected = metric_check(actual["metrics"], selected, start, end, stress, label)
        metric_check(actual["vetoed_metrics"], vetoed, start, end, stress, label + "/vetoed")
        metric_check(actual["common_valid"]["baseline"], valid, start, end, stress, label + "/valid-baseline")
        metric_check(actual["common_valid"]["filtered"], selected_valid, start, end, stress, label + "/valid-filtered")
        equal(actual["common_valid"]["candidates"], len(valid), label + "/valid-count")
        equal(actual["selected_ids"], [rowid(r) for r in sorted(selected, key=order)], label + "/selection")
        equal(actual["vetoed_ids"], [rowid(r) for r in sorted(vetoed, key=order)], label + "/vetoes")
        equal(len(actual["curve"]), len(expected["curve"]), label + "/curve-length")
        for actual_point, expected_point in zip(actual["curve"], expected["curve"]):
            equal(actual_point["epoch"], expected_point["time"], label + "/curve-time")
            equal(actual_point["balance"], expected_point["balance"], label + "/curve-balance")
        coverage = actual["coverage"]
        equal(coverage["candidates"], len(candidates), label + "/candidate-count")
        equal(coverage["primary_valid"], sum(expected_features[rowid(r)]["valid"] for r in candidates), label + "/feature-coverage")
        equal(coverage["correlation_valid"], sum(expected_features[rowid(r)]["correlation_valid"] for r in candidates), label + "/correlation-coverage")
        equal(coverage["unavailable_reasons"], dict(Counter(reason_map[expected_features[rowid(r)]["reason"]]
              for r in candidates if not expected_features[rowid(r)]["valid"])), label + "/missing-reasons")
        equal(coverage["vetoed"], len(vetoed), label + "/veto-count")
        equal(coverage["retention_pct"], 100 * len(selected) / len(candidates) if candidates else None, label + "/retention")
        equal(coverage["pre_window_entries_excluded"], sum(r["op"] < start and start <= r["cl"] < end
              and (ea == "combined" or r["key"] == ea) for r in rows), label + "/boundary-exclusions")
        month_map = {}
        for t in range(int(start), int(end), DAY):
            month = datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m")
            month_map.setdefault(month, {"net_profit": 0.0, "net_r": 0.0, "trades": 0})
        for r in normalized(selected, stress):
            month = datetime.fromtimestamp(r["close"], timezone.utc).strftime("%Y-%m")
            month_map[month]["net_profit"] += r["pnl"]
            month_map[month]["net_r"] += r["net_r"]
            month_map[month]["trades"] += 1
        equal([m["month"] for m in actual["monthly"]], list(month_map), label + "/monthly-membership")
        for m in actual["monthly"]:
            for k, v in month_map[m["month"]].items():
                equal(m[k], v, label + "/month/" + m["month"] + "/" + k)
        other_cost = "recorded" if stress else "stress"
        equal(actual["selected_ids"], cases[(periodid, ea, other_cost, view)]["selected_ids"], label + "/cost-invariant-selection")
    for row in rows:
        a, b = normalized([row], False)[0], normalized([row], True)[0]
        check(b["pnl"] <= a["pnl"] + 1e-10, "Stress never improves matched-position P&L " + rowid(row))
    for group in ("files", "source_files"):
        for path, expected in freeze[group].items():
            equal(digest(path), expected, f"Post-audit frozen hash {path}")
    receipt = {"status": "PASS", "checks": checks, "source_positions": len(rows),
               "features_recomputed": len(expected_features), "comparisons_recomputed": len(cases),
               "result_sha256": digest(HERE / "RESULTS.json"),
               "plan_sha256": digest(HERE / "PLAN.json"), "frozen_sha256": digest(HERE / "FROZEN.json"),
               "independent_verifier_sha256": digest(__file__),
               "unit_test_sha256": digest(HERE / "test_screen.py"),
               "created_utc": datetime.now(timezone.utc).isoformat(),
               "method": "Independent recomputation; does not import engine or use engine feature/metric values as inputs."}
    (HERE / "VERIFICATION.json").write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(receipt, allow_nan=False))


if __name__ == "__main__":
    main()
