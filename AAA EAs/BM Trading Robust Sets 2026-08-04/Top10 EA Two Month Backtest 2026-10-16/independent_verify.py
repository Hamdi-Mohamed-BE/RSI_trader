"""Independent CSV/HTML verification. No terminal, trading package or network import."""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
from html.parser import HTMLParser
import csv
import json
import math
from pathlib import Path
import re
import statistics
import sys

ROOT = Path(__file__).resolve().parent
INITIAL = Decimal("10000")
CASH_FIELDS = ("gross", "commission", "swap", "fee")


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def stamp(row):
    return int(row.get("time_msc") or int(row["epoch"]) * 1000)


def iso(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat()


def dec(row, name):
    return Decimal(str(row.get(name, 0) or 0))


def cash(row):
    return sum((dec(row, name) for name in CASH_FIELDS), Decimal("0"))


def close_enough(actual, expected, label, tolerance=0.000001):
    if expected is None:
        assert actual is None, (label, actual, expected)
    else:
        assert actual is not None and math.isfinite(float(actual)), (label, actual)
        assert abs(float(actual) - float(expected)) <= tolerance, (label, actual, expected)


def csv_rows(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


class Cells(HTMLParser):
    def __init__(self):
        super().__init__()
        self.cells = []
        self.active = False
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag == "td":
            self.active = True
            self.parts = []

    def handle_data(self, data):
        if self.active:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag == "td" and self.active:
            self.cells.append(" ".join("".join(self.parts).split()))
            self.active = False


def report_metric(path, label, percent=False):
    data = Path(path).read_bytes()
    text = data.decode("utf-16") if data[:2] in (b"\xff\xfe", b"\xfe\xff") else data.decode("utf-8-sig", errors="replace")
    parser = Cells()
    parser.feed(text)
    values = [parser.cells[i + 1] for i, value in enumerate(parser.cells[:-1]) if value.rstrip(":") == label.rstrip(":")]
    assert len(values) == 1, ("HTML metric missing or duplicated", label, values)
    clean = values[0].replace("\xa0", "").replace(" ", "").replace(",", "")
    match = re.search(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)", clean)
    assert match, (label, values)
    return float(match.group())


def summarize_positions(positions):
    positions = sorted(positions, key=lambda p: (p["close_msc"], p["position_id"]))
    values = [p["net"] for p in positions]
    positives = [v for v in values if v > 0]
    negatives = [v for v in values if v < 0]
    gp, gl = sum(positives, Decimal("0")), -sum(negatives, Decimal("0"))
    w = l = mw = ml = 0
    for value in values:
        w = w + 1 if value > 0 else 0
        l = l + 1 if value < 0 else 0
        mw, ml = max(mw, w), max(ml, l)
    return dict(
        positions=len(positions), trades=len(positions),
        exit_fills=sum(p["exit_fills"] for p in positions),
        wins=len(positives), losses=len(negatives),
        breakeven=len(values) - len(positives) - len(negatives),
        net_profit=float(gp - gl), return_pct=float((gp - gl) / INITIAL * 100),
        profit_factor=float(gp / gl) if gl else None,
        win_rate_pct=100 * len(positives) / len(values) if values else None,
        gross_profit=float(gp), gross_loss=float(gl),
        avg_win=float(gp / len(positives)) if positives else None,
        avg_loss=float(-gl / len(negatives)) if negatives else None,
        avg_trade=float((gp - gl) / len(values)) if values else None,
        payoff_ratio=float((gp / len(positives)) / (gl / len(negatives))) if positives and negatives else None,
        largest_win=float(max(positives)) if positives else None,
        largest_loss=float(min(negatives)) if negatives else None,
        mean_hold_minutes=sum((p["close_msc"] // 1000 - p["open_msc"] // 1000) / 60 for p in positions) / len(positions) if positions else None,
        max_win_streak=mw, max_loss_streak=ml,
        partial_positions=sum(p["exit_fills"] > 1 for p in positions),
        commission=float(sum((p["commission"] for p in positions), Decimal("0"))),
        swap=float(sum((p["swap"] for p in positions), Decimal("0"))),
        fee=float(sum((p["fee"] for p in positions), Decimal("0"))),
    )


def inspect_case(row, receipt, member, begin_ms, finish_ms):
    assert digest(receipt["path"]) == receipt["sha256"], ("Case receipt hash", row["slug"])
    result = read(receipt["path"])
    folder = Path(receipt["path"]).parent
    assert result["current_active_input_verification"]
    assert result["ranking_includes_boundary_liquidations"]
    assert digest(folder / "report.htm") == result["report_sha256"]
    deals = csv_rows(folder / "deals.csv")
    assert len({int(d["deal"]) for d in deals}) == len(deals), ("Duplicate native deal", row["slug"])
    assert [(stamp(d), int(d["deal"])) for d in deals] == sorted((stamp(d), int(d["deal"])) for d in deals), ("Native export chronology", row["slug"])
    groups = defaultdict(list)
    daily_cash = defaultdict(lambda: Decimal("0"))
    balance = peak = INITIAL
    dd = ddpct = Decimal("0")
    intraday_peak = INITIAL
    prior_day = None
    daily_dd = defaultdict(lambda: Decimal("0"))
    daily_ddpct = defaultdict(lambda: Decimal("0"))
    for deal in deals:
        assert int(deal["entry"]) in (0, 1) and int(deal["type"]) in (0, 1)
        assert begin_ms <= stamp(deal) < finish_ms, ("Deal outside requested dates", row["slug"], deal)
        groups[int(deal["position_id"])].append(deal)
        day_key = iso(stamp(deal))[:10]
        if day_key != prior_day:
            intraday_peak = balance
            prior_day = day_key
        value = cash(deal)
        balance += value
        peak = max(peak, balance)
        intraday_peak = max(intraday_peak, balance)
        daily_dd[day_key] = max(daily_dd[day_key], intraday_peak - balance)
        daily_ddpct[day_key] = max(daily_ddpct[day_key], 100 * (intraday_peak - balance) / intraday_peak)
        dd = max(dd, peak - balance)
        ddpct = max(ddpct, 100 * (peak - balance) / peak)
        daily_cash[iso(stamp(deal))[:10]] += value
    positions = []
    result_positions = {int(p["position_id"]): p for p in result["trades"]}
    assert len(result_positions) == len(result["trades"]), ("Duplicate result position ID", row["slug"])
    for pid, parts in groups.items():
        opened = [d for d in parts if int(d["entry"]) == 0]
        exited = [d for d in parts if int(d["entry"]) == 1]
        assert len(opened) == 1 and exited, ("Unsupported/incomplete lifecycle", row["slug"], pid)
        assert dec(opened[0], "volume") == sum((dec(d, "volume") for d in exited), Decimal("0")), ("Position volume", row["slug"], pid)
        assert all(int(d["type"]) != int(opened[0]["type"]) for d in exited)
        sums = {key: sum((dec(d, key) for d in parts), Decimal("0")) for key in CASH_FIELDS}
        item = dict(position_id=pid, open_msc=stamp(opened[0]), close_msc=max(stamp(d) for d in exited),
                    exit_fills=len(exited), forced=any("end of test" in d["comment"].lower() for d in exited),
                    net=sum(sums.values(), Decimal("0")), **sums)
        recorded = result_positions[pid]
        close_enough(recorded["net"], item["net"], (row["slug"], pid, "whole-position cash"))
        assert recorded["exit_legs"] == len(exited) and recorded["partial"] == (len(exited) > 1)
        assert recorded["open_epoch"] == item["open_msc"] // 1000 and recorded["close_epoch"] == item["close_msc"] // 1000
        positions.append(item)
    assert len(groups) == len(result_positions)
    positions.sort(key=lambda p: (p["close_msc"], p["position_id"]))
    metrics = summarize_positions(positions)
    net = sum((p["net"] for p in positions), Decimal("0"))
    close_enough(balance, INITIAL + net, (row["slug"], "position and deal cash"), tolerance=0.000001)
    close_enough(result["native"]["net_profit"], net, (row["slug"], "native net"), tolerance=0.031)
    close_enough(report_metric(folder / "report.htm", "Total Net Profit"), net, (row["slug"], "independent HTML net"), tolerance=0.031)
    close_enough(report_metric(folder / "report.htm", "Equity Drawdown Relative"), result["native"]["equity_dd_pct"], (row["slug"], "HTML native equity DD"), tolerance=0.011)
    close_enough(report_metric(folder / "report.htm", "Balance Drawdown Relative"), result["native"]["balance_dd_pct"], (row["slug"], "HTML native balance DD"), tolerance=0.011)
    native_trades = int(result["native"]["trades"])
    risk_keys = ["InpMomentumRiskPercent", "InpContrarianRiskPercent", "InpAbsoluteRiskCapPercent"] if row["slug"] == "lta-volume-profile" else ["InpRiskPercent"]
    for key in risk_keys:
        close_enough(result["inputs"][key], row["selected_risk_percent"], (row["slug"], key))
    critical = []
    if row["slug"] in ("lta-volume-profile", "xau-weakness", "xau-squeeze-momentum-standard", "ema3", "asia-breakout"):
        critical.append("InpUseMarkovRegimeFilter")
    if row["slug"] == "nasdaq-5m-candle-momentum":
        critical += ["InpRequireDIAgreement", "InpDIPeriod", "InpInitialStopPercent", "InpUseFixedTarget", "InpUseATRTrailing", "InpTrailingATR", "InpTrailStartR"]
    if row["slug"] == "usdjpy-london-open-momentum":
        critical += ["InpRequireDIAgreement", "InpUseADXFilter", "InpADXMinimum"]
    if row["slug"] in ("us100-h1-orb-13utc", "us100-orb-new-york-m30", "us100-selective-orb-v3", "xau-orb-new-york-m30", "xau-orb-london-ny-overlap-m30", "xau-trend-progression", "xau-slow-trend"):
        critical.append("InpRewardRisk")
    if row["historical_loss_sizing"]:
        critical += ["InpSizingMode", "InpHistoricalLossPoints"]
    if row["slug"].startswith("news-pulse-"):
        critical += ["InpEnableBuySide", "InpEnableSellSide", "InpMarketFallbackOnCrossedLevel", "InpWatchCPI", "InpWatchNFP", "InpWatchFOMC"]
    assert all(key in result["inputs"] for key in critical), (row["slug"], "Critical current filter/exit/sizing input unavailable", critical)
    news_event_sides = []
    if row["slug"].startswith("news-pulse-"):
        calendar = read(ROOT / "Calendar.json")
        event_keys = {(int(e["epoch"]), e["kind"]) for e in calendar["events"]}
        assert len(event_keys) == len(calendar["events"]) == 5
        for deal in deals:
            if int(deal["entry"]) != 0:
                continue
            match = re.fullmatch(r"NP\|(\d+)\|([A-Z]+)\|([BS])", deal["comment"])
            assert match, (row["slug"], "Unknown fresh news opening comment", deal["comment"])
            epoch_value, kind, side = int(match.group(1)), match.group(2), match.group(3)
            assert (epoch_value, kind) in event_keys, (row["slug"], "Opening event outside frozen official schedule", deal)
            news_event_sides.append((epoch_value, kind, side))
        assert len(news_event_sides) == len(set(news_event_sides)), (row["slug"], "Repeated same-event/same-side opening")
        assert result["calendar_audit"]["expected"] == 5 and not result["calendar_audit"]["boundary_violation"]
    if "InpAdaptivePortfolioControls" in result["inputs"]:
        assert result["inputs"]["InpAdaptivePortfolioControls"] == "false"
    for key, value in row["input_settings"].items():
        if key not in result["inputs"]:
            continue  # Inactive legacy SET keys are explicitly recorded by native runner.
        actual = result["inputs"][key]
        try:
            close_enough(actual, float(value), (row["slug"], key), tolerance=1e-9)
        except (TypeError, ValueError):
            assert str(actual).lower() == str(value).lower(), (row["slug"], key, actual, value)
    dates = [datetime.fromtimestamp(begin_ms / 1000, timezone.utc).date() + timedelta(days=i) for i in range(61)]
    rates = []
    opening = INITIAL
    for day in dates:
        value = daily_cash[day.isoformat()]
        rates.append(float(value / opening))
        opening += value
    sharpe = math.sqrt(365) * statistics.mean(rates) / statistics.stdev(rates) if statistics.stdev(rates) > 0 else None
    metrics.update(max_closed_drawdown_cash=float(dd), max_closed_drawdown_pct=float(ddpct),
                   max_daily_closed_drawdown_cash=float(max(daily_dd.values(), default=Decimal("0"))),
                   max_daily_closed_drawdown_pct=float(max(daily_ddpct.values(), default=Decimal("0"))),
                   final_balance=float(balance), closed_balance_daily_sharpe=sharpe)
    boundary_ids = [p["position_id"] for p in positions if p["forced"]]
    assert sorted(boundary_ids) == sorted(result["boundary_liquidation_positions"])
    trace = csv_rows(folder / "equity.csv")
    snapshots = [int(t["epoch"]) for t in trace]
    assert snapshots and all(begin_ms // 1000 <= t < finish_ms // 1000 for t in snapshots)
    if member is not None:
        for key, value in metrics.items():
            close_enough(member["metrics"][key], value, (row["slug"], key))
        natural = summarize_positions([p for p in positions if not p["forced"]])
        for key, value in natural.items():
            close_enough(member["natural_close_only_metrics"][key], value, (row["slug"], "natural", key))
        assert [int(t["position_id"]) for t in member["trades"]] == [p["position_id"] for p in positions]
        assert member["quality"]["boundary_position_count"] == len(boundary_ids)
        close_enough(member["metrics"]["native_equity_drawdown_pct"], result["native"]["equity_dd_pct"], (row["slug"], "native DD label"))
        assert member["quality"]["actual_first_quote_not_exported"] is True
        assert member["quality"]["first_captured_native_snapshot_utc"] == iso(min(snapshots) * 1000)
        assert member["quality"]["last_captured_native_snapshot_utc"] == iso(max(snapshots) * 1000)
        assert len(member["daily"]) == 61
        cash_opening = INITIAL
        for day in member["daily"]:
            close_enough(day["net_profit"], daily_cash[day["date"]], (row["slug"], day["date"], "daily cash"))
            close_enough(day["opening_balance"], cash_opening, (row["slug"], day["date"], "daily opening balance"))
            close_enough(day["return_pct"], 100 * daily_cash[day["date"]] / cash_opening, (row["slug"], day["date"], "daily return"))
            cash_opening += daily_cash[day["date"]]
            close_enough(day["ending_balance"], cash_opening, (row["slug"], day["date"], "daily ending balance"))
            close_enough(day["max_closed_drawdown_cash"], daily_dd[day["date"]], (row["slug"], day["date"], "daily closed DD cash"))
            close_enough(day["max_closed_drawdown_pct"], daily_ddpct[day["date"]], (row["slug"], day["date"], "daily closed DD percent"))
        close_enough(sum(day["net_profit"] for day in member["daily"]), net, (row["slug"], "daily sum"))
        monthly_cash_opening = INITIAL
        assert [month["month"] for month in member["monthly"]] == ["2026-08", "2026-09", "2026-10"]
        for month in member["monthly"]:
            month_key = month["month"]
            independent_month = summarize_positions([p for p in positions if iso(p["close_msc"])[:7] == month_key])
            for key, value in independent_month.items():
                if key != "return_pct":
                    close_enough(month[key], value, (row["slug"], month_key, key))
            close_enough(month["position_return_pct_of_original_capital"], independent_month["return_pct"], (row["slug"], month_key, "position return"))
            cash_in_month = sum((value for day_key, value in daily_cash.items() if day_key[:7] == month_key), Decimal("0"))
            close_enough(month["cash_net_profit"], cash_in_month, (row["slug"], month_key, "monthly cash"))
            close_enough(month["cash_return_pct"], 100 * cash_in_month / monthly_cash_opening, (row["slug"], month_key, "cash return"))
            monthly_cash_opening += cash_in_month
        if row["slug"].startswith("news-pulse-"):
            news_receipts = read(ROOT / "NEWS-RISK-RECEIPTS.json")
            assert member["rules"]["news_event_parameters"] == news_receipts["event_parameters"][row["slug"]]
            assert member["sizing"]["news_order_risk_receipts"] == news_receipts["by_slug"][row["slug"]]
            assert len(member["sizing"]["news_order_risk_receipts"]["orders"]) == len(positions)
    process = read(folder / "owned-process.json")
    return dict(slug=row["slug"], metrics=metrics, position_count=len(positions), exit_fills=sum(p["exit_fills"] for p in positions),
                native_report_trade_count=native_trades, native_count_matches_positions=native_trades == len(positions),
                native_count_matches_exit_fills=native_trades == sum(p["exit_fills"] for p in positions),
                forced_positions=boundary_ids, first_deal_utc=iso(min(map(stamp, deals))) if deals else None,
                last_deal_utc=iso(max(map(stamp, deals))) if deals else None,
                first_captured_native_snapshot_utc=iso(min(snapshots) * 1000),
                last_captured_native_snapshot_utc=iso(max(snapshots) * 1000),
                actual_first_quote_exported=False, observed_final_calendar_day=iso(max(snapshots) * 1000)[:10] == "2026-10-15",
                native_equity_dd_pct=result["native"]["equity_dd_pct"], owned_process_started_epoch=process["started"],
                news_openings_match_unique_official_event_sides=bool(row["slug"].startswith("news-pulse-")) if news_event_sides else None,
                raw_deal_net=float(sum(map(cash, deals), Decimal("0"))), input_risk_verified=True,
                whole_position_cash_and_volume_verified=True, report_metrics_independently_parsed=True)


def main():
    final = "--final" in sys.argv
    plan, frozen, state = (read(ROOT / name) for name in ("PLAN.json", "FROZEN.json", "RUN_STATUS.json"))
    for path, expected in frozen["files"].items():
        assert digest(path) == expected, ("Frozen dependency changed", path)
    checked = {}
    for row in plan["cases"]:
        for path, expected in row["production_hashes"].items():
            checked.setdefault(path, digest(path))
            assert checked[path] == expected, ("Production source changed", path)
    assert plan["adaptive_portfolio_controls"] is False and plan["optimization"] is False
    assert plan["normal_risk_percent"] == 1 and plan["news_risk_percent_per_order"] == 0.1
    assert len(plan["cases"]) == 37 and len({r["slug"] for r in plan["cases"]}) == 37
    assert not state["failed"], state["failed"]
    summary = read(ROOT / "SUMMARY.json") if (ROOT / "SUMMARY.json").exists() else None
    members = {r["id"]: r for r in summary["all_eas"]} if summary else {}
    if final:
        assert summary and len(state["complete"]) == 36 and len(state["missing"]) == 1
    begin = int(datetime.fromisoformat(plan["start"]).replace(tzinfo=timezone.utc).timestamp() * 1000)
    finish = int(datetime.fromisoformat(plan["end_exclusive"]).replace(tzinfo=timezone.utc).timestamp() * 1000)
    results = [inspect_case(row, state["complete"][row["slug"]], members.get(row["slug"]), begin, finish)
               for row in plan["cases"] if row["slug"] in state["complete"]]
    frozen_epoch = datetime.fromisoformat(frozen["frozen_at_utc"]).timestamp()
    assert all(r["owned_process_started_epoch"] >= frozen_epoch for r in results), "Case began before current preregistration freeze"
    rank = sorted([r for r in results if r["position_count"]], key=lambda r: (-r["metrics"]["return_pct"], r["slug"]))
    if summary:
        assert [r["slug"] for r in rank[:10]] == [r["id"] for r in summary["top10"]]
        assert len(members) == 37
    verdict = "FINAL_PASS" if final else "PARTIAL_PASS_NOT_COMPLETE"
    output = dict(schema_version=1, generated_at_utc=datetime.now(timezone.utc).isoformat(), verdict=verdict,
                  cases_verified=len(results), total_reproducible=36, missing=state["missing"],
                  production_unique_files_verified=len(checked), freeze_before_every_observed_owned_process=True,
                  summary_checked=summary is not None, independently_reproduced_top10=[r["slug"] for r in rank[:10]] if final else None,
                  total_positions=sum(r["position_count"] for r in results),
                  total_exit_fills=sum(r["exit_fills"] for r in results),
                  ranked_nonzero_cases=len(rank), zero_position_cases=[r["slug"] for r in results if not r["position_count"]],
                  official_event_parameters_and_news_risk_receipts_integrated=summary is not None,
                  cases=results, no_terminal_or_account_calls=True,
                  limitations=["Native equity DD is independently parsed from the native HTML report, not reconstructed from five-minute snapshots.",
                               "First and last captured native snapshots are test observations, not independent certification of first/last historical quotes.",
                               "This verification does not certify live spreads, historical slippage or future profitability.",
                               "Partial verifier receipts are not a completed batch or final ranking."])
    output["source_hashes"] = {name: digest(ROOT / name) for name in ("PLAN.json", "FROZEN.json", "analyze.py", "independent_verify.py", "test_independent_accounting.py", "NEWS-RISK-RECEIPTS.json")}
    if summary:
        output["source_hashes"]["SUMMARY.json"] = digest(ROOT / "SUMMARY.json")
    (ROOT / "INDEPENDENT-VERIFICATION.json").write_text(json.dumps(output, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({k: output[k] for k in ("verdict", "cases_verified", "total_reproducible", "production_unique_files_verified", "independently_reproduced_top10")}, indent=2))


if __name__ == "__main__":
    main()

