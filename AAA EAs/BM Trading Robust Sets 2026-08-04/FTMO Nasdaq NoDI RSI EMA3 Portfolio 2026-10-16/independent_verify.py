"""Independent offline preflight and accounting checks. No terminal or network calls."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
import csv
import gzip
from html.parser import HTMLParser
import json
import math
from pathlib import Path
import re
import statistics
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
PRIOR = ROOT.parent / "Top10 EA Two Month Backtest 2026-10-16"
PRAGUE = ZoneInfo("Europe/Prague")
INITIAL = Decimal("10000")
EXPECTED = [("N5", "nasdaq-5m-candle-momentum"), ("RV", "xau-rsi-vwap"), ("E3", "ema3")]
CASH_FIELDS = ("gross", "commission", "swap", "fee")


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def save(name, payload):
    (ROOT / name).write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def utc(epoch):
    return datetime.fromtimestamp(float(epoch), timezone.utc)


def prague_day(epoch):
    return utc(epoch).astimezone(PRAGUE).date().isoformat()


def number(row, key):
    return Decimal(str(row.get(key, 0) or 0))


def deal_cash(row):
    return sum((number(row, key) for key in CASH_FIELDS), Decimal("0"))


def deal_msc(row):
    return int(row.get("time_msc") or int(row["epoch"]) * 1000)


def rows(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def near(actual, expected, label="", tolerance=0.000001):
    if expected is None:
        assert actual is None, (label, actual, expected)
    else:
        assert actual is not None and math.isfinite(float(actual)), (label, actual)
        assert abs(float(actual) - float(expected)) <= tolerance, (label, actual, expected)


def same_setting(actual, expected):
    try:
        return abs(float(actual) - float(expected)) < 1e-10
    except (TypeError, ValueError):
        return str(actual).strip().lower() == str(expected).strip().lower()


def day_anchor(balance, deals, epoch):
    """Independent FTMO midnight balance reconstruction from actual cash chronology."""
    today = prague_day(epoch)
    return Decimal(str(balance)) - sum((deal_cash(d) for d in deals if prague_day(deal_msc(d) / 1000) == today), Decimal("0"))


def policy_status(equity, anchor, balance, entry_days, positions=0, orders=0, phase=1,
                  prior_status=0, permit_pass=True, finalizing=False):
    """Golden reference, not a trade engine or a prediction of FTMO acceptance."""
    if prior_status != 0 or finalizing:
        return prior_status
    if equity < 9000 - 1e-7:
        return -2
    if equity < anchor - 500 - 1e-7:
        return -1
    if permit_pass and positions == 0 and orders == 0 and len(set(entry_days)) >= 4 and balance >= (11000 if phase == 1 else 10500) - 1e-7:
        return 1
    return 0


def admission(existing, lots, contract_size, requested, bid, ask, equity):
    proposed = lots * contract_size * max(requested, bid, ask) / 15
    return existing + proposed <= equity + 1e-7, proposed


def rounded_lots(raw, minimum, step, maximum):
    return max(minimum, min(maximum, math.ceil((min(raw, maximum) - 1e-12) / step) * step))


def positions_from_deals(deals):
    assert len({int(d["deal"]) for d in deals}) == len(deals), "Duplicate native deal ticket"
    assert [(deal_msc(d), int(d["deal"])) for d in deals] == sorted((deal_msc(d), int(d["deal"])) for d in deals), "Unsorted native deals"
    grouped = defaultdict(list)
    for deal in deals:
        assert int(deal["entry"]) in (0, 1) and int(deal["type"]) in (0, 1)
        grouped[int(deal["position_id"])].append(deal)
    positions = []
    for pid, parts in grouped.items():
        opened = [d for d in parts if int(d["entry"]) == 0]
        exits = [d for d in parts if int(d["entry"]) == 1]
        assert len(opened) == 1 and exits, (pid, "Incomplete or unsupported lifecycle")
        assert number(opened[0], "volume") == sum((number(d, "volume") for d in exits), Decimal("0")), (pid, "Incomplete exit volume")
        assert all(int(d["type"]) != int(opened[0]["type"]) for d in exits)
        assert all(d["symbol"] == opened[0]["symbol"] for d in parts)
        # The account-policy liquidator uses CTrade's default magic zero. Attribute
        # the complete lifecycle by position ID and opening magic, never exit magic.
        assert all(int(d["magic"]) in (0, int(opened[0]["magic"])) for d in exits)
        positions.append(dict(position_id=pid, magic=int(opened[0]["magic"]), symbol=opened[0]["symbol"],
                              open_msc=deal_msc(opened[0]), close_msc=max(deal_msc(d) for d in exits),
                              net=sum((deal_cash(d) for d in parts), Decimal("0")), exit_fills=len(exits),
                              differently_tagged_exit_fills=sum(d["magic"] != opened[0]["magic"] for d in exits),
                              boundary=any("end of test" in d["comment"].lower() for d in exits), parts=parts))
    return sorted(positions, key=lambda p: (p["close_msc"], p["position_id"]))


def position_metrics(positions):
    values = [p["net"] for p in positions]
    gains = [v for v in values if v > 0]
    losses = [v for v in values if v < 0]
    gp, gl = sum(gains, Decimal("0")), -sum(losses, Decimal("0"))
    w = l = mw = ml = 0
    for value in values:
        w = w + 1 if value > 0 else 0
        l = l + 1 if value < 0 else 0
        mw, ml = max(mw, w), max(ml, l)
    return dict(positions=len(positions), exit_fills=sum(p["exit_fills"] for p in positions),
                net_profit=float(gp - gl), return_pct=float(100 * (gp - gl) / INITIAL),
                win_rate_pct=100 * len(gains) / len(values) if values else None,
                profit_factor=float(gp / gl) if gl else None, wins=len(gains), losses=len(losses),
                breakeven=len(values) - len(gains) - len(losses),
                max_win_streak=mw, max_loss_streak=ml,
                avg_win=float(gp / len(gains)) if gains else None,
                avg_loss=float(-gl / len(losses)) if losses else None,
                avg_trade=float((gp - gl) / len(values)) if values else None,
                payoff_ratio=float((gp / len(gains)) / (gl / len(losses))) if gains and losses else None,
                largest_win=float(max(gains)) if gains else None,
                largest_loss=float(min(losses)) if losses else None,
                mean_hold_minutes=sum((p["close_msc"] - p["open_msc"]) / 60000 for p in positions) / len(positions) if positions and all("open_msc" in p for p in positions) else None,
                partial_positions=sum(p["exit_fills"] > 1 for p in positions),
                **{key: float(sum((number(d, key) for p in positions for d in p.get("parts", [])), Decimal("0")))
                   for key in ("commission", "swap", "fee")})


def cash_metrics(deals, start, end):
    begin = datetime.fromisoformat(start).date()
    finish = datetime.fromisoformat(end).date()
    calendar_days = [(begin + timedelta(days=i)).isoformat() for i in range((finish - begin).days)]
    by_day = defaultdict(lambda: Decimal("0"))
    day_dd = defaultdict(lambda: Decimal("0"))
    day_dd_pct = defaultdict(lambda: Decimal("0"))
    balance = peak = day_peak = INITIAL
    maximum_dd = maximum_dd_pct = Decimal("0")
    prior_day = None
    for deal in deals:
        key = utc(deal_msc(deal) / 1000).date().isoformat()
        assert key in calendar_days, ("Cash outside native window", key, start, end)
        if key != prior_day:
            day_peak = balance
            prior_day = key
        amount = deal_cash(deal)
        by_day[key] += amount
        balance += amount
        peak = max(peak, balance)
        day_peak = max(day_peak, balance)
        maximum_dd = max(maximum_dd, peak - balance)
        maximum_dd_pct = max(maximum_dd_pct, 100 * (peak - balance) / peak)
        day_dd[key] = max(day_dd[key], day_peak - balance)
        day_dd_pct[key] = max(day_dd_pct[key], 100 * (day_peak - balance) / day_peak)
    opening = INITIAL
    daily = []
    for key in calendar_days:
        value = by_day[key]
        daily.append(dict(date=key, net_profit=float(value), opening_balance=float(opening),
                          ending_balance=float(opening + value), return_pct=float(100 * value / opening),
                          max_closed_drawdown_cash=float(day_dd[key]), max_closed_drawdown_pct=float(day_dd_pct[key])))
        opening += value
    rates = [day["return_pct"] / 100 for day in daily]
    deviation = statistics.stdev(rates) if len(rates) >= 2 else 0
    sharpe = math.sqrt(365) * statistics.mean(rates) / deviation if deviation else None
    return dict(net_profit=float(balance - INITIAL), final_balance=float(balance),
                max_closed_drawdown_cash=float(maximum_dd), max_closed_drawdown_pct=float(maximum_dd_pct),
                max_daily_closed_drawdown_cash=float(max(day_dd.values(), default=Decimal("0"))),
                max_daily_closed_drawdown_pct=float(max(day_dd_pct.values(), default=Decimal("0"))),
                closed_balance_daily_sharpe=sharpe, calendar_days=len(daily), daily=daily)


def preflight():
    frozen, config, plan = (read(ROOT / name) for name in ("FROZEN.json", "CONFIG.json", "PLAN.json"))
    for path, expected_hash in frozen["files"].items():
        assert digest(path) == expected_hash, ("Frozen file changed", path)
    for path, expected_hash in frozen["production_hashes"].items():
        assert digest(path) == expected_hash, ("Production file changed", path)
    assert plan["config"] == config
    assert (config["start"], config["end_exclusive"], config["deposit"], config["risk_percent"], config["native_leverage"]) == ("2026-08-16", "2026-10-16", 10000, 1, 15)
    assert not any(config[key] for key in ("production_changed", "optimization", "live_changes"))
    assert len(plan["cases"]) == 7 and len({c["tag"] for c in plan["cases"]}) == 7
    assert [c["tag"] for c in plan["cases"]] == ["noDI-shared-diagnostic", "DIon-shared-control", "noDI-challenge", "N5-alone", "RV-alone", "E3-alone", "N5-direct-parity"]
    original = {row["slug"]: row for row in read(PRIOR / "PLAN.json")["cases"]}
    adapter = (ROOT / "SharedPortfolio.mq5").read_text(encoding="utf-8-sig")
    comparisons = []
    for row, (key, slug) in zip(config["entries"], EXPECTED, strict=True):
        assert row["slug"] == slug and row["key"] == key
        old = original[slug]
        assert row["source"] == old["source"] and row["preset"] == old["preset"]
        assert row["production_hashes"] == old["production_hashes"]
        expected = dict(old["input_settings"])
        expected.setdefault("InpAdaptivePortfolioControls", "false")
        if key == "N5":
            expected["InpRequireDIAgreement"] = "false"
        assert set(row["input_settings"]) == set(expected)
        assert all(same_setting(row["input_settings"][name], value) for name, value in expected.items())
        assert all(same_setting(row["inputs"][name], value) for name, value in expected.items())
        snapshot = ROOT / "snapshots" / slug
        assert digest(snapshot / "production.ex5") == digest(old["expert"])
        assert digest(snapshot / "production.set") == digest(old["preset"])
        assert read(snapshot / "inputs.json") == row["input_settings"]
        for name in expected:
            literal = re.search(r"\b" + key + "_" + re.escape(name) + r"\s*=\s*([^;]+);", adapter)
            assert literal, (slug, "Expected input not frozen in shared adapter", name)
            value = re.sub(r"^\s*\([^()]+\)\s*", "", literal.group(1)).strip().strip('"')
            assert same_setting(value, expected[name]), (slug, "Frozen MQL literal differs", name, value, expected[name])
        changed = {name: dict(before=old["input_settings"].get(name, "source default false"), after=value)
                   for name, value in expected.items() if not same_setting(value, old["input_settings"].get(name, "false"))}
        assert changed == ({"InpRequireDIAgreement": dict(before="true", after="false")} if key == "N5" else {})
        comparisons.append(dict(slug=slug, source_and_set_hashes_match=True, effective_input_changes=changed,
                                explicit_adaptive_false=True, risk_percent=1))
    harness = (ROOT / "PortfolioHarness.mqh").read_text(encoding="utf-8")
    assert 'if(!MQLInfoInteger(MQL_TESTER) || forcedFinalization)return;' in harness
    assert 'if(officialStatus==0)' in harness and 'PositionsTotal()==0 && OrdersTotal()==0 && ArraySize(entryDays)>=4' in harness
    assert 'equity<9000.0-1e-7' in harness and 'equity<dayAnchor-500.0-1e-7' in harness
    assert 'dayAnchor=AccountInfoDouble(ACCOUNT_BALANCE)-delta' in harness
    assert 'StringFind(HistoryDealGetString(trans.deal,DEAL_COMMENT),"end of test")>=0){forcedFinalization=true;return;}' in adapter
    assert 'Observe();RefreshLedger(true);Observe();' in adapter
    assert 'EventSetTimer(1)' in adapter and 'N5_OnTick();' in adapter and 'RV_OnTick();' in adapter and 'E3_OnTick();' in adapter
    assert adapter.index('if(nq && Active(1))') < adapter.index('gold && Active(2)') < adapter.index('gold && Active(3)')
    assert 'if(!entry)return OrderSend(request,result)' in harness
    assert 'else if(existing+need>equity+1e-7)' in harness and 'OrderCalcMargin(' in harness
    assert 'No resize' in config["account_policy"]["margin"]
    assert 'Fresh $10k' in config["account_policy"]["phase2"]
    receipt = dict(verdict="PREFLIGHT_PASS", generated_at_utc=datetime.now(timezone.utc).isoformat(),
                   source_files_verified=len(frozen["production_hashes"]), frozen_dependencies_verified=len(frozen["files"]),
                   modules=comparisons, shared_account_not_sum_of_standalones=True, native_leverage=15,
                   account_policy=config["account_policy"], no_terminal_account_or_network_calls=True,
                   source_hashes={name: digest(ROOT / name) for name in ("PLAN.json", "FROZEN.json", "CONFIG.json", "PortfolioHarness.mqh", "SharedPortfolio.mq5", "independent_verify.py")},
                   limitations=["Static source and settings audit; native output accounting/parity is checked separately after execution.",
                                "Primary-symbol ticks plus one-second secondary latest-quote sampling do not certify every historical floating-equity excursion.",
                                "Gross notional/15 margin is an explicit conservative research proxy, not a certified FTMO contract model."])
    save("INDEPENDENT-PREFLIGHT.json", receipt)
    return receipt


class HtmlCells(HTMLParser):
    def __init__(self):
        super().__init__()
        self.cells, self.parts, self.active = [], [], False

    def handle_starttag(self, tag, attrs):
        if tag == "td":
            self.active, self.parts = True, []

    def handle_data(self, data):
        if self.active:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag == "td" and self.active:
            self.cells.append(" ".join("".join(self.parts).split()))
            self.active = False


def report_values(folder):
    raw = gzip.decompress((folder / "report.htm.gz").read_bytes())
    parser = HtmlCells()
    parser.feed(raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8-sig", errors="replace"))
    def item(label):
        values = [parser.cells[i + 1] for i, cell in enumerate(parser.cells[:-1]) if cell.rstrip(":") == label]
        assert len(values) == 1, (folder.name, label, values)
        match = re.search(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)", values[0].replace(" ", "").replace(",", ""))
        assert match, values
        return float(match.group())
    return raw, dict(net_profit=item("Total Net Profit"), equity_dd_pct=item("Equity Drawdown Relative"), balance_dd_pct=item("Balance Drawdown Relative"))


def verify_policy_files(folder, deals, manifest, member):
    status = rows(folder / "status.csv")[0]
    events = rows(folder / "events.csv")
    days = rows(folder / "days.csv")
    admissions = rows(folder / "admissions.csv")
    contracts = {row["symbol"]: row for row in rows(folder / "contracts.csv")}
    assert set(contracts) == {"USTEC", "XAUUSD"}
    assert all(int(row["account_leverage"]) == 15 and row["profit_currency"] == "USD" for row in contracts.values())
    for row in days:
        key = row["prague_day"]
        date_key = key[:4] + "-" + key[4:6] + "-" + key[6:8]
        anchor = INITIAL + sum((deal_cash(d) for d in deals if prague_day(deal_msc(d) / 1000) < date_key), Decimal("0"))
        near(row["day_start_balance"], anchor, (folder.name, date_key, "Prague day anchor"), .011)
        near(row["daily_equity_floor"], anchor - 500, (folder.name, date_key, "daily floor"), .011)
        near(row["max_equity_loss_from_day_start"], max(0, float(anchor) - float(row["minimum_observed_equity"])), (folder.name, date_key, "observed floating daily loss"), .011)
    terminals = [row for row in events if row["kind"] in ("natural_phase_pass", "permanent_phase_failure", "ledger_failure")]
    assert len(terminals) <= 1, (folder.name, "Terminal state reset or repeated")
    final_status = int(status["status"])
    if final_status:
        assert len(terminals) == 1 and int(terminals[0]["status"]) == final_status
        terminal = terminals[0]
        stamp = int(terminal["epoch"])
        known_days = {prague_day(deal_msc(d) / 1000) for d in deals if int(d["entry"]) == 0 and deal_msc(d) // 1000 <= stamp}
        assert int(terminal["entry_days"]) == len(known_days)
        expected = policy_status(float(terminal["equity"]), float(terminal["day_start_balance"]), float(terminal["balance"]), known_days,
                                 int(terminal["positions"]), int(terminal["orders"]), int(manifest["case"]["phase"]))
        assert expected == final_status, (folder.name, "FTMO terminal status", expected, final_status)
        if manifest["case"]["challenge"]:
            assert not [d for d in deals if int(d["entry"]) == 0 and deal_msc(d) // 1000 > stamp], (folder.name, "New entry after terminal status")
            if final_status == 1:
                assert not [d for d in deals if "end of test" in d["comment"].lower()], "Forced end closure cannot produce Challenge pass"
    else:
        assert not terminals
    observed = rows(folder / "equity.csv")
    terminal_seen = 0
    for point in observed:
        point_status = int(point["status"])
        if terminal_seen:
            assert point_status == terminal_seen, (folder.name, "Terminal status not permanent")
        elif point_status:
            terminal_seen = point_status
    risk_ratios = []
    for row in admissions:
        lots, contract = float(row["lots"]), float(row["contract_size"])
        allowed, required = admission(float(row["existing_margin15"]), lots, contract, float(row["requested_entry"]), float(row["bid"]), float(row["ask"]), float(row["equity"]))
        near(row["new_margin15"], required, (folder.name, "Admission notional/15"), .00001)
        near(row["nominal_budget"], float(row["equity"]) * .01, (folder.name, "Nominal 1% budget"), .000051)
        near(row["planned_stop_risk"], lots * contract * abs(float(row["requested_entry"]) - float(row["sl"])), (folder.name, "USD linear planned stop risk"), .011)
        if row["decision"] == "admitted":
            assert allowed, (folder.name, "Admitted above gross margin budget", row)
        elif row["decision"] == "gross_notional_15_margin":
            assert not allowed, (folder.name, "Spurious gross margin rejection", row)
        spec = contracts[row["symbol"]]
        minimum, step, maximum = (float(spec[name]) for name in ("volume_min", "volume_step", "volume_max"))
        assert minimum - 1e-8 <= lots <= maximum + 1e-8
        near(lots / step, round(lots / step), (folder.name, "Broker volume step"), .00001)
        budget = float(row["nominal_budget"])
        risk_ratios.append(float(row["planned_stop_risk"]) / budget if budget else None)
    if member is not None:
        assert member["status"]["status"] == final_status
        assert len(member["risk"]["admissions"]) == len(admissions)
        for row, derived in zip(days, member["daily_prague"], strict=True):
            for key in ("day_start_balance", "minimum_observed_equity", "max_equity_loss_from_day_start", "equity_peak_to_trough", "daily_equity_floor"):
                near(derived[key], row[key], (folder.name, "SUMMARY floating daily", key), .011)
        accepted = [row for row in admissions if row["decision"] == "admitted"]
        used = set()
        openings = {int(row["position_id"]): row for row in deals if int(row["entry"]) == 0}
        for trade in member["trades"]:
            opening = openings[int(trade["position_id"])]
            candidates = [(index, row) for index, row in enumerate(accepted) if index not in used
                          and int(row["magic"]) == int(opening["magic"]) and row["symbol"] == opening["symbol"]
                          and abs(float(row["lots"]) - float(opening["volume"])) < 1e-8
                          and 0 <= deal_msc(opening) / 1000 - int(row["epoch"]) <= 3]
            assert len(candidates) == 1, (folder.name, "Non-unique request-to-fill diagnostic", trade["position_id"])
            index, request = candidates[0]
            used.add(index)
            budget = float(request["nominal_budget"])
            contract = float(contracts[opening["symbol"]]["contract_size"])
            filled_risk = abs(float(opening["price"]) - float(opening["sl"])) * float(opening["volume"]) * contract
            near(trade["planned_stop_risk_cash"], request["planned_stop_risk"], (folder.name, "Canonical planned risk"))
            near(trade["initial_filled_stop_risk_cash"], filled_risk, (folder.name, "Canonical filled risk"))
            near(trade["planned_stop_risk_pct_of_request_equity"], float(request["planned_stop_risk"]) / budget, (folder.name, "Canonical risk percent"))
            near(trade["filled_stop_risk_pct_of_request_equity"], filled_risk / budget, (folder.name, "Canonical filled risk percent"))
            one_lot = abs(float(request["requested_entry"]) - float(request["sl"])) * contract
            raw_lots = budget / one_lot
            spec = contracts[opening["symbol"]]
            expected_lots = rounded_lots(raw_lots, float(spec["volume_min"]), float(spec["volume_step"]), float(spec["volume_max"]))
            near(request["lots"], expected_lots, (folder.name, "Original production lot rounding"), .0000001)
    after_fail = [d for d in deals if int(d["entry"]) == 1 and int(d["epoch"]) >= int(status["status_epoch"])] if final_status < 0 and manifest["case"]["challenge"] else []
    return dict(status=final_status, terminal_events=len(terminals), observed_prague_days=len(days),
                first_observed_callback_utc=utc(int(status["first_observed"])).isoformat(),
                last_observed_callback_utc=utc(int(status["last_observed"])).isoformat(),
                actual_first_or_last_historical_quote_certified=False,
                admissions_checked=len(admissions), policy_admitted_attempts=sum(a["decision"] == "admitted" for a in admissions),
                admitted_zero_quoted_spread_requests=sum(a["decision"] == "admitted" and float(a["bid"]) == float(a["ask"]) for a in admissions),
                max_planned_vs_nominal_risk_multiple=max((v for v in risk_ratios if v is not None), default=None),
                terminal_entry_days=int(terminals[0]["entry_days"]) if terminals else None,
                terminal_equity=float(status["status_equity"]) if terminals else None,
                terminal_balance=float(status["status_balance"]) if terminals else None,
                post_failure_exit_fills=len(after_fail),
                latest_post_failure_exit_utc=utc(max(deal_msc(d) for d in after_fail) / 1000).isoformat() if after_fail else None,
                seconds_from_failure_to_final_exit=max(deal_msc(d) for d in after_fail) / 1000 - int(status["status_epoch"]) if after_fail else None,
                market_closed_responses=read(folder / "results.json")["warnings"].get("market_closed", 0),
                no_new_entries_after_terminal_second=True if manifest["case"]["challenge"] and terminals else None,
                margin_and_cash_anchor_reconciled=True)


def inspect_native(folder, member=None):
    result = read(folder / "results.json")
    manifest = read(folder / "manifest.json")
    assert result["manifest"] == manifest
    assert manifest["deposit"] == 10000 and manifest["leverage"] == 15 and manifest["model"] == 4 and manifest["execution_delay_ms"] == 150
    assert manifest["end_exclusive"] == "2026-10-16"
    direct = manifest["case"].get("direct", False)
    build_name = "NasdaqDirect" if direct else "SharedPortfolio"
    build = read(ROOT / "BUILD.json")[build_name]
    assert digest(ROOT / (build_name + ".mq5")) == build["source_sha256"]
    assert digest(ROOT / (build_name + ".ex5")) == build["binary_sha256"]
    assert build["compile"] == "0 errors, 0 warnings"
    assert manifest["binary_sha256"] == build["binary_sha256"]
    process = read(folder / "owned-process.json")
    assert process["started"] >= datetime.fromisoformat(read(ROOT / "FROZEN.json")["frozen_at_utc"]).timestamp()
    raw_report, independent_native = report_values(folder)
    assert sha256(raw_report).hexdigest() == result["report_sha256"]
    report_text = raw_report.decode("utf-16") if raw_report[:2] in (b"\xff\xfe", b"\xfe\xff") else raw_report.decode("utf-8-sig", errors="replace")
    plain_report = re.sub(r"<[^>]+>", " ", report_text)
    for key, value in manifest["inputs"].items():
        assert re.search(r"\b" + re.escape(key) + r"\s*=\s*" + re.escape(str(value)) + r"(?=\s|$)", plain_report), (folder.name, "Native runtime input missing", key, value)
    deals = rows(folder / "deals.csv")
    positions = positions_from_deals(deals)
    metrics = position_metrics(positions)
    cash = cash_metrics(deals, manifest["start"], manifest["end_exclusive"])
    near(metrics["net_profit"], cash["net_profit"], (folder.name, "Whole-position and cash conservation"))
    near(metrics["net_profit"], result["native"]["net_profit"], (folder.name, "Native net cash"), .031)
    for key, value in independent_native.items():
        near(result["native"][key], value, (folder.name, "Independent HTML metric", key), .011)
    journal = gzip.decompress((folder / "journal.txt.gz").read_bytes()).decode("utf-8")
    invalid = re.findall(r"initialization failed|start time changed|not enough history|stop out|margin call|access violation|array out of range|zero divide|FTMO3_EXPORT_FAILED", journal, re.I)
    assert not invalid, (folder.name, "Native invalid data/runtime", invalid)
    history_quality = result["native"].get("history_quality")
    exact_real_ticks = history_quality is not None and "100%" in history_quality and "real ticks" in history_quality.lower()
    data_warnings = sorted(set(re.findall(r"[^\r\n]*(?:real ticks absent|ticks discarded|generated ticks)[^\r\n]*", journal, re.I)))
    traces = rows(folder / "equity.csv")
    observed_epochs = [int(row["epoch"]) for row in traces]
    start_epoch = datetime.fromisoformat(manifest["start"]).replace(tzinfo=timezone.utc).timestamp()
    end_epoch = datetime.fromisoformat(manifest["end_exclusive"]).replace(tzinfo=timezone.utc).timestamp()
    assert observed_epochs and all(start_epoch <= stamp < end_epoch for stamp in observed_epochs)
    expected_keys = {(int(row["inputs"]["InpMagic"]), row["symbol"]): row for row in read(ROOT / "CONFIG.json")["entries"]}
    assert all((position["magic"], position["symbol"]) in expected_keys for position in positions)
    module_nets = {row["slug"]: float(sum((p["net"] for p in positions if (p["magic"], p["symbol"]) == key), Decimal("0"))) for key, row in expected_keys.items()}
    near(sum(module_nets.values()), metrics["net_profit"], (folder.name, "Shared module cash total"))
    if member is not None:
        for key, value in metrics.items():
            near(member["metrics"][key], value, (folder.name, "SUMMARY positions", key))
        for key, value in cash.items():
            if key not in ("daily", "calendar_days", "net_profit", "max_daily_closed_drawdown_pct"):
                near(member["metrics"][key], value, (folder.name, "SUMMARY cash", key))
        assert len(member["daily"]) == cash["calendar_days"]
        for expected_day, actual_day in zip(cash["daily"], member["daily"], strict=True):
            assert expected_day["date"] == actual_day["date"]
            for key, value in expected_day.items():
                if key != "date" and key in actual_day:
                    near(actual_day[key], value, (folder.name, expected_day["date"], key))
        for contribution in member["contributions"]:
            cfg_row = next(row for row in expected_keys.values() if row["slug"] == contribution["id"])
            module_positions = [p for p in positions if p["magic"] == int(cfg_row["inputs"]["InpMagic"]) and p["symbol"] == cfg_row["symbol"]]
            for key, value in position_metrics(module_positions).items():
                near(contribution["metrics"][key], value, (folder.name, contribution["id"], key))
            expected_inputs = dict(cfg_row["input_settings"])
            if cfg_row["key"] == "N5":
                expected_inputs["InpRequireDIAgreement"] = str(manifest["case"]["di"]).lower()
            assert contribution["inputs"] == expected_inputs
        for month in member["monthly"]:
            key = month["month"]
            month_positions = [p for p in positions if utc(p["close_msc"] / 1000).date().isoformat()[:7] == key]
            for name, value in position_metrics(month_positions).items():
                output_key = "whole_position_return_pct_of_initial" if name == "return_pct" else name
                near(month[output_key], value, (folder.name, key, output_key))
            expected_days = [day for day in cash["daily"] if day["date"][:7] == key]
            near(month["cash_net_profit"], sum(day["net_profit"] for day in expected_days), (folder.name, key, "Monthly actual cash"))
            near(month["cash_return_pct"], 100 * (expected_days[-1]["ending_balance"] / expected_days[0]["opening_balance"] - 1), (folder.name, key, "Monthly cash return"))
        near(member["metrics"]["native_equity_drawdown_pct"], independent_native["equity_dd_pct"], (folder.name, "Floating DD label"))
        natural = position_metrics([p for p in positions if not p["boundary"]])
        for key, value in natural.items():
            near(member["metrics"]["natural_close_subset"][key], value, (folder.name, "Natural-close subset", key))
    policy = None if direct else verify_policy_files(folder, deals, manifest, member)
    return dict(tag=folder.name, metrics=metrics, cash_metrics={k: v for k, v in cash.items() if k != "daily"},
                module_net_cash=module_nets, policy=policy, native_equity_dd_pct=independent_native["equity_dd_pct"],
                history_quality=history_quality, native_reports_100_percent_real_ticks=exact_real_ticks,
                native_data_warnings=data_warnings, native_runtime_or_history_errors=invalid,
                first_captured_snapshot_utc=utc(min(observed_epochs)).isoformat(), last_captured_snapshot_utc=utc(max(observed_epochs)).isoformat(),
                raw_deal_count=len(deals), positions=len(positions), exit_fills=sum(p["exit_fills"] for p in positions),
                unique_core01_failed_market_closed_close_messages=len({line for line in journal.splitlines() if "\tCore 01\t" in line and "failed market" in line.lower() and "market closed" in line.lower()}),
                forced_boundary_positions=[p["position_id"] for p in positions if p["boundary"]],
                actual_final_calendar_day_observed=utc(max(observed_epochs)).date().isoformat() == "2026-10-15")


def final_audit():
    preflight()
    plan = read(ROOT / "PLAN.json")
    summary = read(ROOT / "SUMMARY.json") if (ROOT / "SUMMARY.json").exists() else None
    member_by_tag = {row["id"]: row for row in summary["scenarios"]} if summary else {}
    completed = [path.parent for path in (ROOT / "native").glob("*/results.json")]
    reports = [inspect_native(folder, member_by_tag.get(folder.name)) for folder in sorted(completed)]
    final = "--final" in sys.argv
    if final:
        assert summary and {row["tag"] for row in reports} >= {row["tag"] for row in plan["cases"]}
        assert summary["meta"]["native_simultaneous_portfolio"] and summary["meta"]["not_summed_standalone"]
        assert summary["parity"]["passed"] is True
        adapter = rows(ROOT / "native" / "N5-alone" / "deals.csv")
        direct = rows(ROOT / "native" / "N5-direct-parity" / "deals.csv")
        parity_fields = ("time_msc", "entry", "type", "volume", "price", "gross", "commission", "swap", "fee", "sl", "tp", "comment")
        assert [[d[key] for key in parity_fields] for d in adapter] == [[d[key] for key in parity_fields] for d in direct], "Independent raw Nasdaq direct parity failed"
        phase1 = next(row for row in reports if row["tag"] == "noDI-challenge")
        phase2 = next((row for row in reports if row["tag"] == "noDI-verification"), None)
        if phase2:
            assert phase1["policy"]["status"] == 1
            assert read(ROOT / "native" / "noDI-verification" / "manifest.json")["deposit"] == 10000
        elif phase1["policy"]["status"] != 1:
            assert summary["verification"] is None, "Phase 2 cannot follow a failed or incomplete Challenge"
        near(summary["comparison"]["net_cash_difference"], summary["baseline"]["metrics"]["net_profit"] - summary["control"]["metrics"]["net_profit"], "DI comparison cash")
        near(summary["comparison"]["return_percentage_point_difference_noDI_minus_DI"], summary["baseline"]["metrics"]["return_pct"] - summary["control"]["metrics"]["return_pct"], "DI comparison percentage points")
    receipt = dict(verdict="FINAL_PASS" if final else "PARTIAL_NATIVE_AUDIT", generated_at_utc=datetime.now(timezone.utc).isoformat(),
                   cases_verified=len(reports), fixed_cases_required=7, all_cases_native_100_percent_real_ticks=all(row["native_reports_100_percent_real_ticks"] and not row["native_data_warnings"] for row in reports),
                   shared_cash_and_module_conservation_verified=True, cases=reports,
                   source_hashes={name: digest(ROOT / name) for name in ("FROZEN.json", "PLAN.json", "CONFIG.json", "independent_verify.py")},
                   no_terminal_account_or_network_calls=True,
                   limitations=["Floating daily-loss checks are independently audited from emitted native observer receipts; latest-secondary-quote sampling is not every secondary historical tick.",
                                "A native 100% real-tick history label is not independent certification of historical spread/slippage completeness or genuine FTMO execution.",
                                "Each scenario is a separately reset native account; standalone controls are never summed into portfolio performance.",
                                "Request-to-fill risk diagnostics use a unique magic/symbol/volume/0-to-3-second match because request receipts do not export the returned native order ID. Lifecycle accounting itself uses exact position IDs."])
    if summary:
        receipt["source_hashes"].update({name: digest(ROOT / name) for name in ("SUMMARY.json", "analyze.py")})
    save("INDEPENDENT-VERIFICATION.json", receipt)
    return receipt


def main():
    if "--native" in sys.argv or "--final" in sys.argv:
        result = final_audit()
        print(json.dumps({key: result[key] for key in ("verdict", "cases_verified", "all_cases_native_100_percent_real_ticks")}, indent=2))
    else:
        result = preflight()
        print(json.dumps({key: result[key] for key in ("verdict", "source_files_verified", "frozen_dependencies_verified", "modules")}, indent=2))


if __name__ == "__main__":
    main()
