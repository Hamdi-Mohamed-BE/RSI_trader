"""Parse the native MT5 Strategy Tester HTML reports of this study into NATIVE_RESULTS.json.

Copied from US100 H1 ORB ADX RR1 Research 2026-09-23/parse_native.py (parse() only; see summarize.py).
Metrics come from the report header; trades/streaks/costs/late exits are rebuilt from the deal table.
Run with: uv run --with beautifulsoup4 python parse_native.py
"""
import json, re
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / "run-config.json").read_text(encoding="utf-8"))
FLAT_UTC_MINUTES = 20 * 60  # installed SET: flat 20:00 UTC (tester server offset 0)


def num(s):
    s = (s or "").replace("\xa0", " ").replace(" ", "")
    m = re.match(r"-?[\d.]+", s)
    return float(m.group()) if m else None


def parse(path: Path):
    raw = path.read_bytes()
    t = raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8", "replace")
    rows = [[c.get_text(" ", strip=True) for c in r.find_all(["td", "th"])] for r in BeautifulSoup(t, "html.parser").find_all("tr")]
    kv = {}
    for r in rows:
        c = [x for x in r if x]
        for i in range(len(c) - 1):
            if c[i].endswith(":") and not c[i + 1].endswith(":"):
                kv.setdefault(c[i][:-1], c[i + 1])
    deals, in_deals = [], False
    for c in rows:
        if c and c[0] == "Deals":
            in_deals = True
            continue
        if in_deals and len(c) == 13 and re.match(r"\d{4}\.\d\d\.\d\d", c[0] or ""):
            deals.append(dict(time=c[0], type=c[3], dir=c[4], vol=num(c[5]), price=num(c[6]),
                              commission=num(c[8]) or 0.0, swap=num(c[9]) or 0.0, profit=num(c[10]) or 0.0,
                              balance=num(c[11]), comment=c[12]))
    dep = next(d for d in deals if d["type"] == "balance")["balance"]
    trades, open_ = [], None
    for d in deals:
        if d["dir"] == "in":
            open_ = dict(entry=d["time"], side=d["type"], entry_price=d["price"], vol=d["vol"],
                         net=d["commission"] + d["swap"] + d["profit"], comm=d["commission"], swap=d["swap"])
        elif d["dir"] == "out" and open_:
            open_["net"] += d["commission"] + d["swap"] + d["profit"]
            open_["comm"] += d["commission"]
            open_["swap"] += d["swap"]
            open_.update(exit=d["time"], exit_price=d["price"], exit_comment=d["comment"], bal_after=d["balance"])
            trades.append(open_)
            open_ = None

    def streak(vals, pos):
        best = cur = 0
        for v in vals:
            cur = cur + 1 if (v > 0 if pos else v < 0) else 0
            best = max(best, cur)
        return best

    nets = [x["net"] for x in trades]
    late = overnight = 0
    for x in trades:
        e = datetime.strptime(x["entry"], "%Y.%m.%d %H:%M:%S")
        q = datetime.strptime(x["exit"], "%Y.%m.%d %H:%M:%S")
        if q.date() != e.date():
            overnight += 1
        if q.date() != e.date() or q.hour * 60 + q.minute > FLAT_UTC_MINUTES + 1:
            late += 1
    exits = {"tp": 0, "sl": 0, "time/other": 0}
    for x in trades:
        c = (x["exit_comment"] or "").lower()
        exits["tp" if c.startswith("tp") else "sl" if c.startswith("sl") else "time/other"] += 1
    final = deals[-1]["balance"] if deals else dep
    gp = sum(v for v in nets if v > 0)
    gl = -sum(v for v in nets if v < 0)
    summary = dict(
        report=str(path), quality=kv.get("History Quality"), ticks=kv.get("Ticks"), bars=kv.get("Bars"),
        period=kv.get("Period"), expert=kv.get("Expert"),
        net_profit=num(kv.get("Total Net Profit")), return_pct=round((final / dep - 1) * 100, 2), final_balance=final,
        profit_factor=num(kv.get("Profit Factor")), trades=len(trades), report_trades=int(num(kv.get("Total Trades")) or 0),
        win_rate_pct=round(100 * sum(v > 0 for v in nets) / len(nets), 2) if nets else 0.0,
        long_trades=kv.get("Long Trades (won %)"), short_trades=kv.get("Short Trades (won %)"),
        max_win_streak=streak(nets, True), max_loss_streak=streak(nets, False),
        balance_dd_rel=kv.get("Balance Drawdown Relative"), equity_dd_rel=kv.get("Equity Drawdown Relative"),
        balance_dd_max=kv.get("Balance Drawdown Maximal"), equity_dd_max=kv.get("Equity Drawdown Maximal"),
        expected_payoff=kv.get("Expected Payoff"), recovery=kv.get("Recovery Factor"), sharpe=kv.get("Sharpe Ratio"),
        avg_win=round(gp / max(1, sum(v > 0 for v in nets)), 2), avg_loss=round(-gl / max(1, sum(v < 0 for v in nets)), 2),
        commission=round(sum(x["comm"] for x in trades), 2), swap=round(sum(x["swap"] for x in trades), 2),
        pf_from_deals=round(gp / gl, 3) if gl else None, exits=exits,
        exits_after_flat_or_overnight=late, overnight_holds=overnight,
    )
    return summary, trades


def main():
    raise SystemExit("Use summarize.py in this folder.")


if __name__ == "__main__":
    main()
