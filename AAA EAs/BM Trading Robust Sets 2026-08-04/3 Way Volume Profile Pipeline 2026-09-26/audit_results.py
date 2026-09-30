"""Independent trade/report reconciliation and qualification report. Never starts MT5."""
from collections import defaultdict
from datetime import datetime, timedelta
import gzip
import json
from pathlib import Path
import re
import statistics

import run_qualification as q

ROOT = Path(__file__).resolve().parent


def extra(r):
    folder = ROOT / "native" / r["case"]
    trades = sorted(json.loads(gzip.decompress((folder / "trades.json.gz").read_bytes())),
                    key=lambda t: (t["close_time"], t["number"]))
    body = gzip.decompress(next(folder.glob("*.htm.gz")).read_bytes()).decode("utf-16")
    metrics = r["metrics"]
    net = sum(t["net_profit"] for t in trades)
    a, b = (datetime.strptime(r[k], "%Y.%m.%d") for k in ("start", "end"))
    days = (b-a).days
    trading_days = days if r["symbol"] == "BTCUSD" else sum((a+timedelta(days=i)).weekday() < 5 for i in range(days))
    groups = {"W": [], "L": []}
    last, count = None, 0
    for t in trades:
        side = "W" if t["net_profit"] > 0 else "L" if t["net_profit"] < 0 else None
        if side == last:
            count += 1
        else:
            if last:
                groups[last].append(count)
            last, count = side, 1
    if last:
        groups[last].append(count)
    months = defaultdict(lambda: {"trades": 0, "net_usd": 0.0})
    date = a.replace(day=1)
    while date < b:
        months[date.strftime("%Y-%m")]
        date = date.replace(year=date.year+(date.month == 12), month=date.month % 12+1)
    for t in trades:
        key = t["close_time"][:7]
        months[key]["trades"] += 1
        months[key]["net_usd"] += t["net_profit"]
    balance = 10000.0
    for month, x in sorted(months.items()):
        x["net_usd"] = round(x["net_usd"], 2)
        x["return_pct"] = round(100*x["net_usd"]/balance, 3) if balance else None
        x["start_balance"] = round(balance, 2)
        balance += x["net_usd"]
        x["end_balance"] = round(balance, 2)
    ledger_pf = sum(max(t["net_profit"], 0) for t in trades)/max(0.01, -sum(min(t["net_profit"], 0) for t in trades))
    return dict(
        reconciled=abs(net-metrics["net_profit"]) < 0.05 and len(trades) == metrics["trades"],
        ledger_net_usd=round(net, 2), ledger_pf=round(ledger_pf, 4),
        first_entry=trades[0]["open_time"] if trades else None,
        last_exit=trades[-1]["close_time"] if trades else None,
        trades_per_month=round(len(trades)/(days/30.4375), 2),
        trades_per_trading_day=round(len(trades)/trading_days, 3),
        max_win_streak=max(groups["W"], default=0), max_loss_streak=max(groups["L"], default=0),
        avg_win_streak=round(statistics.mean(groups["W"]), 2) if groups["W"] else 0,
        avg_loss_streak=round(statistics.mean(groups["L"]), 2) if groups["L"] else 0,
        profitable_months=sum(m["net_usd"] > 0 for m in months.values()), months_including_partial=len(months),
        max_equity_relative_dd_pct=q.h._number(q.h._metric(body, "Equity Drawdown Relative")),
        max_balance_relative_dd_pct=q.h._number(q.h._metric(body, "Balance Drawdown Relative")),
        monthly=dict(months),
    )


def main():
    rows = q.rows()
    audit = [r | {"audit": extra(r)} for r in rows]
    q.dump(ROOT / "AUDIT.json", audit)
    native = [r for r in audit if r["model"] == 4 and r["control_seed"] is None]
    judgments = []
    for c in q.CFG["candidates"]:
        baselines = [r for r in native if r["symbol"] == c["symbol"] and r["variant"] == c["variant"]
                     and r["period"] in ("3y", "5y")]
        detail = []
        for r in baselines:
            controls = [x for x in audit if x["symbol"] == c["symbol"] and x["variant"] == c["variant"]
                        and x["period"] == r["period"] and x["model"] == 4 and x["control_seed"] is not None]
            complete = len(controls) == len(q.CFG["control_seeds"]) and all(x["ok"] and x["audit"]["reconciled"] for x in controls)
            ref = {k: statistics.median(x["metrics"][k] for x in controls) for k in ("return_pct", "profit_factor")} if complete else None
            detail.append(dict(period=r["period"], absolute_pass=q.qualifies(r) and r["audit"]["reconciled"],
                               median_control=ref,
                               beats_control=bool(ref and all(r["metrics"][k] > ref[k] for k in ref))))
        approved = len(detail) == 2 and all(x["absolute_pass"] and x["beats_control"] for x in detail)
        failed = any(not x["absolute_pass"] for x in detail)
        judgments.append(dict(symbol=c["symbol"], variant=c["variant"], periods=detail,
                              status="QUALIFIED" if approved else "FAIL" if failed else "PENDING_CONTROL_OR_CONFIRMATION"))
    q.dump(ROOT / "qualification.json", judgments)
    progress_path=ROOT / 'Optimization' / 'progress.json'
    optimization=json.loads(progress_path.read_text()) if progress_path.exists() else {'state':'not started'}
    lines = ["# 3 Way Volume Profile — audited qualification", "",
             "Research only. Optimization status at report build: " + json.dumps(optimization) + ". No production changes.", "",
             "## Tick-mode confirmations", "",
             "Model 4 native MT5, M15, $10,000, target 1% equity risk, 2R, configured 150ms delay. Real-tick coverage can be partial; older ticks are generated. This is not FTMO execution evidence.", "",
             "| Asset / setup | Window | Return | PF | Trades | /month | /trading day | Win rate | Max equity DD | Max balance DD | Avg W/L streak | Longest W/L streak | Profitable months* |",
             "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|"]
    for r in native:
        m, e = r["metrics"], r["audit"]
        lines.append(f"| {r['symbol']} {r['variant']} | {r['period']} | {m['return_pct']:+.2f}% | {m['profit_factor']:.2f} | {m['trades']} | "
                     f"{e['trades_per_month']:.2f} | {e['trades_per_trading_day']:.3f} | {m['win_rate_pct']:.2f}% | "
                     f"{e['max_equity_relative_dd_pct']:.2f}% | {e['max_balance_relative_dd_pct']:.2f}% | "
                     f"{e['avg_win_streak']}/{e['avg_loss_streak']} | {e['max_win_streak']}/{e['max_loss_streak']} | "
                     f"{e['profitable_months']}/{e['months_including_partial']} |")
    lines += ["", "*Calendar months include the partial first and last September. BTC /day uses calendar days; gold and FX use weekdays. Equity/balance DD use MT5's maximum RELATIVE percentage, not the percentage at the largest dollar drawdown.",
              "", "## Decisions", ""]
    for x in judgments:
        lines.append(f"- {x['symbol']} {x['variant']}: **{x['status']}**.")
        for p in x["periods"]:
            lines.append(f"  - {p['period']}: absolute gate {p['absolute_pass']}; median random control {p['median_control']}; beats control {p['beats_control']}.")
    lines += ["", "## Integrity and limitations", "",
              f"- Trades and net P/L reconcile to the report in {sum(x['audit']['reconciled'] for x in audit)}/{len(audit)} runs.",
              "- Original gold one-year parity: all 78 trade records and every summary metric matched. Only the parser's report-label field differed.",
              "- Broker lot rounding is upward: especially at the minimum lot, actual initial risk can exceed the nominal 1%.",
              "- Account leverage and contract conditions are from the saved Exness research binding, not a simulated FTMO Swing account.",
              "- No-signal controls use 2 ATR stops instead of profile structure stops. They are a sanity reference, not a perfectly matched causal experiment.",
              "- Absolute PF is rounded to two decimals in the native report; exact trade-ledger PF is retained in AUDIT.json.",
              "- No website, BAT, active EA, live account or Git publication was changed.",
              "", "## Tick coverage and order exceptions", ""]
    for r in native:
        coverage = sorted(set(re.sub(r"^.*?(?=(?:BTCUSD|XAUUSD|USDJPY))", "", line) for line in r["journal"]["coverage"]))
        orders = sorted(set(re.sub(r"^.*?(?=20\d\d\.\d\d\.\d\d )", "", line) for line in r["journal"]["orders"]))
        lines.append(f"### {r['case']}")
        lines += ["", f"Report history quality: {r['metrics']['history_quality']}. First entry: {r['audit']['first_entry']}; last exit: {r['audit']['last_exit']}.", ""]
        lines += ["- " + x for x in coverage + orders] or ["No journal coverage/order exceptions captured."]
        lines.append("")
    (ROOT / "AUDITED RESULTS.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(judgments, indent=2))


if __name__ == "__main__":
    main()
