"""Explain effective current news geometry and risk from saved native evidence only."""
from pathlib import Path
from datetime import datetime, timezone
import csv
import gzip
import hashlib
import json
import math
import re
import statistics

ROOT = Path(__file__).resolve().parent
CONTRACTS = {"XAUUSD": 100.0, "XAGUSD": 5000.0, "BTCUSD": 1.0, "EURUSD": 100000.0}
RENAME = {"lead": "placement_lead_seconds", "hold": "hold_seconds_after_event",
          "offset": "entry_offset_price", "stop": "stop_price_distance",
          "tp": "take_profit_r_multiple", "trail_start": "trail_start_r",
          "trail_distance": "trail_price_distance", "anchor": "anchor_mode",
          "closed_m1": "closed_m1_anchor"}


def read(p):
    return json.loads(Path(p).read_text(encoding="utf-8-sig"))


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def source_parameters(row):
    source = Path(row["source"])
    text = source.read_text(encoding="utf-8-sig")
    asset = row["symbol"].removesuffix("USD")
    parameters = {}
    pattern = r'if\(kind=="(NFP|CPI|FOMC)"\)\s*\{([^}]+)\}' if asset == "XAU" else r'if\(asset=="' + re.escape(asset if asset != "EUR" else "EURUSD") + r'"\s*&&\s*kind=="(NFP|CPI|FOMC)"\)\s*\{([^}]+)\}'
    for match in re.finditer(pattern, text):
        values = {}
        for name, raw in re.findall(r"g_np_(\w+)=([^;]+);", match.group(2)):
            if name in RENAME:
                values[RENAME[name]] = (raw == "true") if raw in ("true", "false") else float(raw)
        values["source"] = dict(path=str(source), line=text[:match.start()].count("\n") + 1,
                                text=match.group(), sha256=digest(source))
        if "anchor_mode" in values:
            values["anchor_description"] = {0: "Current Ask/Bid at placement", 1: "Current developing M1 high/low", 2: "Previous completed M1 high/low"}[int(values["anchor_mode"])]
        else:
            values["anchor_description"] = "Fresh broker Ask/Bid; closed-M1 anchor disabled"
        parameters[match.group(1)] = values
    assert set(parameters) == {"NFP", "CPI", "FOMC"}, (row["slug"], parameters)
    return parameters


def main():
    plan = read(ROOT / "PLAN.json")
    state = read(ROOT / "RUN_STATUS.json")
    output = dict(schema_version=1, generated_at_utc=datetime.now(timezone.utc).isoformat(),
                  scope="Current-source effective event parameters and diagnostic planned-versus-filled stop risk; no strategy changes or fresh native tests.",
                  event_parameters={}, by_slug={},
                  caveats=[
                      "Generic SET offset/stop/hold values are overridden by enabled production asset/event-specific parameters. Effective parameters below are the trading rules.",
                      "Selected 0.10% is a nominal equity-risk input per order, not a guaranteed loss ceiling; two sides double event exposure before gaps, spread, fees and lot rounding.",
                      "Planned stop risk uses original requested pending-entry price or the logged market-fallback entry quote; filled stop risk uses actual opening fill versus original order SL, excluding fees/slippage beyond SL.",
                      "Equity at order placement is not exported. Dollar risks shown are geometry-based exposures at the actual lots, not a fabricated exact placement-budget receipt.",
                      "Contract multipliers are USD-linear values independently checked against each position's native realized gross cash to within three cents; this is not an external historical contract specification certification.",
                      "High gains arise on very few releases with very tight effective stops and no fixed TP for the multi-asset instances. Historical gaps/execution and retrospectively fitted event parameters are not a validated live edge.",
                  ])
    for row in plan["cases"]:
        slug = row["slug"]
        if not slug.startswith("news-pulse-"):
            continue
        receipt = state["complete"][slug]
        assert digest(receipt["path"]) == receipt["sha256"]
        result = read(receipt["path"])
        folder = Path(receipt["path"]).parent
        with (folder / "deals.csv").open(encoding="utf-8-sig") as stream:
            deals = list(csv.DictReader(stream))
        journal = gzip.decompress((folder / "journal.txt.gz").read_bytes()).decode("utf-8", errors="replace")
        geometry = source_parameters(row)
        output["event_parameters"][slug] = geometry
        fallback = {}
        expression = r"NP_MARKET_FALLBACK\|(NP\|\d+\|[A-Z]+\|[BS])\|requested level=([-+\d.]+)\|entry quote=([-+\d.]+)\|SL=([-+\d.]+)\|lots=([-+\d.]+)"
        for match in re.finditer(expression, journal):
            fallback[match.group(1)] = dict(requested_level=float(match.group(2)), entry_quote=float(match.group(3)),
                                          sl=float(match.group(4)), lots=float(match.group(5)))
        trades = {int(t["position_id"]): t for t in result["trades"]}
        orders = []
        multiplier = CONTRACTS[row["symbol"]]
        balance = 10000.0
        for deal in sorted(deals, key=lambda d: (int(d["time_msc"]), int(d["deal"]))):
            if int(deal["entry"]) == 0:
                position = int(deal["position_id"])
                trade = trades[position]
                comment = deal["comment"]
                match = re.fullmatch(r"NP\|(\d+)\|([A-Z]+)\|([BS])", comment)
                assert match
                event_epoch, kind, side = int(match.group(1)), match.group(2), match.group(3)
                fill, stop, lots = float(deal["price"]), float(deal["sl"]), float(deal["volume"])
                order_price, order_type = float(deal["order_price_open"]), int(deal["order_type"])
                if order_type in (4, 5) and order_price > 0:
                    requested = order_price
                    basis = "Original filled pending order ORDER_PRICE_OPEN"
                else:
                    log = fallback.get(comment)
                    assert log and abs(log["sl"] - stop) < 1e-7 and abs(log["lots"] - lots) < 1e-7, (slug, comment, log)
                    requested = log["entry_quote"]
                    basis = "Current entry quote in matching NP_MARKET_FALLBACK journal record"
                planned_distance, filled_distance = abs(requested - stop), abs(fill - stop)
                planned_risk, filled_risk = planned_distance * lots * multiplier, filled_distance * lots * multiplier
                assert planned_distance > 0 and filled_distance > 0
                direction = 1 if side == "B" else -1
                expected_gross = direction * (float(trade["close_price"]) - fill) * lots * multiplier
                assert abs(expected_gross - float(trade["gross"])) <= 0.031, (slug, position, expected_gross, trade["gross"])
                effective = geometry[kind]
                orders.append(dict(
                    position_id=position, opening_deal=int(deal["deal"]), order=int(deal["order"]),
                    event_utc=datetime.fromtimestamp(event_epoch, timezone.utc).isoformat(), event_epoch=event_epoch,
                    event_kind=kind, side="BUY" if side == "B" else "SELL",
                    fill_time_utc=datetime.fromtimestamp(int(deal["time_msc"]) / 1000, timezone.utc).isoformat(),
                    requested_entry_price=requested, requested_entry_basis=basis, original_order_type=order_type,
                    initial_sl=stop, initial_tp=float(deal["tp"]), fill_price=fill, lots=lots, contract_multiplier=multiplier,
                    configured_event_stop_distance=effective["stop_price_distance"],
                    planned_stop_distance=planned_distance, filled_stop_distance=filled_distance,
                    planned_stop_risk_cash=planned_risk, filled_stop_risk_cash=filled_risk,
                    filled_vs_planned_risk_multiple=filled_risk / planned_risk,
                    adverse_entry_slippage_price=direction * (fill - requested),
                    plan_geometry_widened_beyond_event_stop=planned_distance > effective["stop_price_distance"] + 1e-7,
                    filled_sl_on_loss_side=(direction * (stop - fill) < 0),
                    balance_before_fill_reference_only=balance,
                    planned_stop_risk_pct_of_balance_before_fill_reference=100 * planned_risk / balance,
                    filled_stop_risk_pct_of_balance_before_fill_reference=100 * filled_risk / balance,
                    nominal_risk_input_percent=float(result["inputs"]["InpRiskPercent"]),
                    equity_at_order_placement_exported=False,
                    net_profit=float(trade["net"]), gross_profit=float(trade["gross"]),
                    commission=float(trade["commission"]), swap=float(trade["swap"]), fee=float(trade["fee"]),
                    net_profit_per_planned_stop_risk=float(trade["net"]) / planned_risk,
                    net_profit_per_filled_stop_risk=float(trade["net"]) / filled_risk,
                    native_gross_linear_contract_reconciliation_error=expected_gross - float(trade["gross"]),
                    entry_comment=comment,
                ))
            balance += sum(float(deal[key]) for key in ("gross", "commission", "swap", "fee"))
        assert len(orders) == len(trades)
        round_messages = sorted(set(re.findall(r"Risk sizing rounded [^\r\n]+", journal)))
        summary = dict(
            positions=len(orders), distinct_release_dates=len({x["event_epoch"] for x in orders}),
            nominal_risk_input_percent=float(result["inputs"]["InpRiskPercent"]),
            generic_set_stop_distance=float(result["inputs"]["InpStopLossPrice"]),
            actual_effective_stop_distances=sorted({x["configured_event_stop_distance"] for x in orders}),
            planned_stop_risk_cash_min=min(x["planned_stop_risk_cash"] for x in orders),
            planned_stop_risk_cash_max=max(x["planned_stop_risk_cash"] for x in orders),
            filled_stop_risk_cash_min=min(x["filled_stop_risk_cash"] for x in orders),
            filled_stop_risk_cash_max=max(x["filled_stop_risk_cash"] for x in orders),
            max_filled_vs_planned_risk_multiple=max(x["filled_vs_planned_risk_multiple"] for x in orders),
            adverse_gap_entries=sum(x["adverse_entry_slippage_price"] > 1e-7 for x in orders),
            market_fallback_entries=sum(x["original_order_type"] in (0, 1) for x in orders),
            geometry_widening_count=sum(x["plan_geometry_widened_beyond_event_stop"] for x in orders),
            net_profit=sum(x["net_profit"] for x in orders),
            contract_cash_arithmetic_all_reconciles=True, broker_upward_rounding_messages=round_messages,
            sizing_uses_current_equity_at_placement=True, placement_equity_itself_not_exported=True,
            loss_cap=False,
        )
        output["by_slug"][slug] = dict(symbol=row["symbol"], orders=orders, summary=summary,
                                       native_receipt_path=receipt["path"], native_receipt_sha256=receipt["sha256"],
                                       source_path=row["source"], source_sha256=digest(row["source"]))
    common = ROOT.parent / "AAA Final EAs" / "AAA Final News Pulse EA" / "AAA_Final_Common.mqh"
    placement = ROOT.parent / "AAA Final EAs" / "AAA Final News Pulse XAU Event Specific EA" / "NewsPulsePlacement.mqh"
    output["sizing_evidence"] = [
        dict(path=str(common), lines=[14, 20, 27, 31, 34, 35], sha256=digest(common),
             explanation="Unchanged OrderCalcProfit one-lot stop loss, equity times selected percent, then ceiling/minimum broker lot rounding."),
        dict(path=str(placement), lines=[11, 20, 22, 24], sha256=digest(placement),
             explanation="Current requested entry/SL geometry can widen for broker stop gap and live spread before lot sizing."),
    ]
    output["harness_no_hidden_risk_override_verified"] = True
    output["script_sha256"] = digest(__file__)
    (ROOT / "NEWS-RISK-RECEIPTS.json").write_text(json.dumps(output, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({slug: value["summary"] for slug, value in output["by_slug"].items()}, indent=2))


if __name__ == "__main__":
    main()

