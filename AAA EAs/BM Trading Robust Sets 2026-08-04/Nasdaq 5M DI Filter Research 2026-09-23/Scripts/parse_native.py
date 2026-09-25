"""Parse native MT5 Strategy Tester HTML reports (UTF-16) for the N5 current vs DI comparison."""
import json, re, sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup

NY = ZoneInfo("America/New_York"); UTC = ZoneInfo("UTC")

def num(s):
    s = s.replace("\xa0", " ").replace(" ", "")
    m = re.match(r"-?[\d.]+", s)
    return float(m.group()) if m else None

def parse(path):
    raw = Path(path).read_bytes()
    t = raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8", "replace")
    rows = [[c.get_text(" ", strip=True) for c in r.find_all(["td", "th"])] for r in BeautifulSoup(t, "html.parser").find_all("tr")]
    kv = {}
    for r in rows:
        c = [x for x in r if x]
        for i in range(0, len(c) - 1):
            if c[i].endswith(":") and not c[i + 1].endswith(":"):
                kv.setdefault(c[i][:-1], c[i + 1])
    # deals table
    deals, in_deals = [], False
    for r in rows:
        c = r
        if c and c[0] == "Deals":
            in_deals = True; continue
        if in_deals and len(c) == 13 and re.match(r"\d{4}\.\d\d\.\d\d", c[0] or ""):
            deals.append(dict(time=c[0], type=c[3], dir=c[4], vol=num(c[5]) if c[5] else None, price=num(c[6]) if c[6] else None,
                              commission=num(c[8]) or 0.0, swap=num(c[9]) or 0.0, profit=num(c[10]) or 0.0, balance=num(c[11]), comment=c[12]))
    dep = next(d for d in deals if d["type"] == "balance")["balance"]
    trades, open_ = [], None
    for d in deals:
        if d["dir"] == "in":
            open_ = dict(entry=d["time"], side=d["type"], net=d["commission"] + d["swap"] + d["profit"], comm=d["commission"], swap=d["swap"])
        elif d["dir"] == "out" and open_:
            open_["net"] += d["commission"] + d["swap"] + d["profit"]
            open_["comm"] += d["commission"]; open_["swap"] += d["swap"]
            open_.update(exit=d["time"], exit_comment=d["comment"], bal_after=d["balance"])
            trades.append(open_); open_ = None
    def streak(vals, pos):
        best = cur = 0
        for v in vals:
            cur = cur + 1 if (v > 0 if pos else v < 0) else 0
            best = max(best, cur)
        return best
    nets = [x["net"] for x in trades]
    late = weekend = 0; max_hold = 0.0
    for x in trades:
        e = datetime.strptime(x["entry"], "%Y.%m.%d %H:%M:%S").replace(tzinfo=UTC).astimezone(NY)
        q = datetime.strptime(x["exit"], "%Y.%m.%d %H:%M:%S").replace(tzinfo=UTC).astimezone(NY)
        cutoff = e.replace(hour=15, minute=56, second=0)
        if q > cutoff: late += 1
        if q.date() != e.date() and (q.weekday() < e.weekday() or (q - e).days >= 5): weekend += 1
        max_hold = max(max_hold, (q - e).total_seconds() / 3600)
    final = deals[-1]["balance"] if deals else dep
    gp = sum(v for v in nets if v > 0); gl = -sum(v for v in nets if v < 0)
    return dict(
        report=str(path), quality=kv.get("History Quality"), ticks=kv.get("Ticks"), bars=kv.get("Bars"),
        period=kv.get("Period"), expert=kv.get("Expert"),
        net_profit=num(kv["Total Net Profit"]), return_pct=round((final / dep - 1) * 100, 2), final_balance=final,
        profit_factor=num(kv["Profit Factor"]), trades=int(num(kv["Total Trades"])),
        win_rate_pct=round(100 * sum(v > 0 for v in nets) / len(nets), 2) if nets else 0,
        long_trades=kv.get("Long Trades (won %)"), short_trades=kv.get("Short Trades (won %)"),
        max_win_streak=streak(nets, True), max_loss_streak=streak(nets, False),
        report_consec_wins=kv.get("Maximum consecutive wins ($)"), report_consec_losses=kv.get("Maximum consecutive losses ($)"),
        balance_dd=kv.get("Balance Drawdown Maximal"), equity_dd=kv.get("Equity Drawdown Maximal"),
        balance_dd_rel=kv.get("Balance Drawdown Relative"), equity_dd_rel=kv.get("Equity Drawdown Relative"),
        sharpe=kv.get("Sharpe Ratio"), recovery=kv.get("Recovery Factor"), expected_payoff=kv.get("Expected Payoff"),
        largest_win=kv.get("Largest profit trade"), largest_loss=kv.get("Largest loss trade"),
        commission=round(sum(x["comm"] for x in trades), 2), swap=round(sum(x["swap"] for x in trades), 2),
        pf_from_deals=round(gp / gl, 3) if gl else None,
        late_exits_after_1555ny=late, weekend_holds=weekend, max_hold_hours=round(max_hold, 1),
        max_hold_report=kv.get("Maximal position holding time"),
        overnight_holds=sum(1 for x in trades if x['exit'][:10] != x['entry'][:10]),
    ), trades

if __name__ == "__main__":
    out = {}
    for p in sys.argv[1:]:
        s, _ = parse(p); out[Path(p).stem] = s
    print(json.dumps(out, indent=1))
