"""FTMO 2-Step pass / funded-survival simulation for EA portfolios (research only, 2026-09-24).

Follows the user's framework: pass Phase 1, pass both phases, a zero-edge control, one funded year of survival,
a risk-per-trade sweep and expected payout.

Inputs: native MT5 trade ledgers with original stops and costs, prepared and audited by
  ../FTMO Combination Study 2026-09-19/prepare.py  (prepared.json, audit.json; not modified here).
Portfolio: the EAs that pass that study's frozen pre-2024-09-19 eligibility rule (>= 50 training trades,
positive stressed R, PF > 1.05). Selection used ONLY pre-2024-09-19 data.

Trade result in R = (gross + commission + swap - stress extra) / original stop risk, per lot, using that study's
FTMO-style STRESSED costs (winners -10%, losers +10%, asset slippage, doubled negative swap).

Account model ($100,000, fixed risk per trade as a % of initial capital, lots not rounded):
- Equity check at every trade open/close event. Two brackets are reported:
  "conservative" reserves every open trade at its full stop (-1R each; correlated positions can breach together);
  "optimistic" counts closed trades only. Real FTMO floating equity lies between. Gaps beyond the stop are in R.
- Breach: equity < 90% of initial, or equity < (balance at 00:00 Europe/Prague) - 5% of initial.
- Phase 1 target +10%, Phase 2 +5% (balance, flat, >= 4 distinct trading days). Each phase capped at 365 days.
  2 business days between phases are not modelled (small); no time limit is assumed beyond the cap.
- Funded: 365 days, same limits; every 30 days, if flat and in profit, 80% of profit is paid and the balance is
  reset to $100,000. Breach ends the account.
- Timeline: weekly block bootstrap (Monday-start weeks, trades keep their in-week times and cross-EA timing).
- Zero-edge control: each EA's mean R over the pool is subtracted from each of its trades.
"""
from __future__ import annotations

import heapq
import json
import math
import random
import statistics
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
STUDY = ROOT.parent / "FTMO Combination Study 2026-09-19"

# Verbatim copy of costs() and SPECS from ../FTMO Combination Study 2026-09-19/prepare.py (importing that module
# would also import the EA Store app, which is avoided on purpose). Values are per target-broker lot.
SPECS = {'XAUUSD': (100, 15), 'XAGUSD': (5000, 15), 'USTEC': (1, 15), 'USDJPY': (100000, 30), 'EURUSD': (100000, 30), 'BTCUSD': (1, 1), 'ETHUSD': (10, 1)}


def costs(r, stress=False):
    sym = r['symbol']; contract = SPECS[sym][0]
    g = r['unit_gross']; c = r['unit_comm']; s = r['unit_swap']
    if sym in ('BTCUSD', 'ETHUSD'): c = min(c, -.000325 * contract * (r['open_price'] + r['close_price']))
    else: c = min(c, -(47.5 if sym == 'XAGUSD' else .7 if sym == 'USTEC' else 7.))
    extra = 0.
    if stress:
        news = r['news']
        g *= .9 if g > 0 else 1.1
        slip = {'XAUUSD': 1. if news else .2, 'XAGUSD': .04, 'USTEC': 2., 'EURUSD': .0002, 'USDJPY': .02, 'BTCUSD': 30., 'ETHUSD': 3.}[sym]
        extra = slip * contract / (r['open_price'] if sym == 'USDJPY' else 1.)
        s = min(s * 2, 0.)
        if r['cl'] - r['op'] > 86400:
            notional = contract * (1 if sym == 'USDJPY' else r['open_price'])
            s = min(s, -notional * .00015 * math.ceil((r['cl'] - r['op']) / 86400))
    return g, c, s, extra

PRAGUE = ZoneInfo("Europe/Prague")
DAY, WEEK = 86400, 7 * 86400
CAPITAL = 100_000.0
SPLIT = datetime(2024, 9, 19, tzinfo=timezone.utc).timestamp()
END = datetime(2026, 8, 31, tzinfo=timezone.utc).timestamp()
POOLS = {"full 5y": (None, END), "pre-2024-09 (selection period)": (None, SPLIT), "post-2024-09 (unseen)": (SPLIT, END)}
RISKS = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0]
PATHS = 5000
SEED = 20260924


def load(keys):
    data = json.loads((STUDY / "prepared.json").read_text(encoding="utf-8-sig"))
    out = []
    for k in keys:
        for r in data["rows"][k]:
            g, c, s, x = costs(r, True)
            out.append(dict(key=k, op=r["op"], cl=max(r["cl"], r["op"] + 1), R=(g + c + s - x) / r["unit_risk"]))
    return out


def week_start(t):
    d = datetime.fromtimestamp(t, timezone.utc)
    d = (d - timedelta(days=d.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    return d.timestamp()


def pool_weeks(trades, start, end):
    first = week_start(min(t["op"] for t in trades)) if start is None else week_start(start)
    weeks = defaultdict(list)
    for t in trades:
        if (start is None or t["op"] >= start) and t["op"] < end:
            weeks[week_start(t["op"])].append(t)
    n = int((week_start(end) - first) // WEEK)
    return [weeks.get(first + i * WEEK, []) for i in range(n)]  # empty weeks are real no-trade weeks


def zero_edge(weeks):
    by = defaultdict(list)
    for w in weeks:
        for t in w:
            by[t["key"]].append(t["R"])
    mean = {k: statistics.fmean(v) for k, v in by.items()}
    return [[dict(t, R=t["R"] - mean[t["key"]]) for t in w] for w in weeks]


class Stream:
    """Endless bootstrapped week stream on an arbitrary future calendar (Mondays from 2027-01-04 UTC).
    Each account phase continues the same stream, so the timeline is continuous across phases."""

    def __init__(self, weeks, rng):
        self.weeks, self.rng, self.i = weeks, rng, 0
        self.base = datetime(2027, 1, 4, tzinfo=timezone.utc).timestamp()

    def next_week(self):
        src = self.rng.choice(self.weeks)
        target = self.base + self.i * WEEK
        self.i += 1
        if not src:
            return target, []
        off = target - week_start(src[0]["op"])
        return target, [(t["op"] + off, t["cl"] + off, t["R"]) for t in src]


def run_account(stream, risk_pct, target_pct, max_days, funded=False, envelope=1.0):
    """Return (outcome, days, payouts, trades). outcome: pass / breach / timeout / survived."""
    risk = CAPITAL * risk_pct / 100
    bal = anchor = CAPITAL
    open_pos, days, payouts, heap = {}, set(), [], []
    ntr = pid = 0
    anchor_day = None
    start, trades = stream.next_week()
    last_pay = start
    next_week = start + WEEK

    def push(week_trades):
        nonlocal pid
        for op, cl, R in week_trades:
            pid += 1
            heapq.heappush(heap, (op, 1, pid, R))
            heapq.heappush(heap, (cl, 2, pid, R))

    push(trades)
    limit = start + max_days * DAY
    while True:
        # Load every week whose start is not after the next pending event (keeps time order across weekends).
        while not heap or heap[0][0] >= next_week:
            if next_week >= limit:
                break
            _, wk = stream.next_week()
            push(wk)
            next_week += WEEK
        if not heap or heap[0][0] >= limit:
            return ("survived" if funded else "timeout"), max_days, payouts, ntr
        t, kind, p, R = heapq.heappop(heap)
        d = datetime.fromtimestamp(t, PRAGUE).date()
        if d != anchor_day:
            anchor_day, anchor = d, bal
        if kind == 1:
            open_pos[p] = R
            days.add(d)
        else:
            if p not in open_pos:
                continue
            open_pos.pop(p)
            bal += R * risk
            ntr += 1
        equity_low = bal - envelope * risk * len(open_pos)
        if equity_low < 0.90 * CAPITAL or equity_low < anchor - 0.05 * CAPITAL:
            return "breach", (t - start) / DAY, payouts, ntr
        if not open_pos:
            if not funded and bal >= CAPITAL * (1 + target_pct / 100) and len(days) >= 4:
                return "pass", (t - start) / DAY, payouts, ntr
            if funded and t - last_pay >= 30 * DAY:
                last_pay = t
                if bal > CAPITAL:
                    payouts.append(0.8 * (bal - CAPITAL))
                    bal = CAPITAL
                    anchor = min(anchor, bal)


def simulate(weeks, risk, rng, envelope=1.0):
    res = dict(p1=0, both=0, funded_survive=0, p1_days=[], both_days=[], payouts=[], breach_p1=0, breach_p2=0,
               timeout=0, within30=0, within60=0, within90=0, within180=0)
    for _ in range(PATHS):
        s = Stream(weeks, rng)
        o1, d1, _, _ = run_account(s, risk, 10, 365, envelope=envelope)
        if o1 != "pass":
            res["breach_p1" if o1 == "breach" else "timeout"] += 1
            res["payouts"].append(0.0)
            continue
        res["p1"] += 1
        res["p1_days"].append(d1)
        o2, d2, _, _ = run_account(s, risk, 5, 365, envelope=envelope)
        if o2 != "pass":
            res["breach_p2" if o2 == "breach" else "timeout"] += 1
            res["payouts"].append(0.0)
            continue
        total = d1 + d2
        res["both"] += 1
        res["both_days"].append(total)
        for lim in (30, 60, 90, 180):
            res[f"within{lim}"] += total <= lim
        o3, _, pay, _ = run_account(s, risk, 0, 365, funded=True, envelope=envelope)
        res["funded_survive"] += o3 == "survived"
        res["payouts"].append(sum(pay))
    n = PATHS
    med = lambda v: round(statistics.median(v), 1) if v else None
    return dict(
        pass_phase1_pct=round(100 * res["p1"] / n, 1), pass_both_pct=round(100 * res["both"] / n, 1),
        pass_both_within_30d_pct=round(100 * res["within30"] / n, 1), within_60d_pct=round(100 * res["within60"] / n, 1),
        within_90d_pct=round(100 * res["within90"] / n, 1), within_180d_pct=round(100 * res["within180"] / n, 1),
        median_days_phase1=med(res["p1_days"]), median_days_both=med(res["both_days"]),
        breach_phase1_pct=round(100 * res["breach_p1"] / n, 1), breach_phase2_pct=round(100 * res["breach_p2"] / n, 1),
        unfinished_365d_pct=round(100 * res["timeout"] / n, 1),
        funded_year_survival_pct_of_funded=round(100 * res["funded_survive"] / res["both"], 1) if res["both"] else None,
        expected_payout_per_attempt_usd=round(statistics.fmean(res["payouts"])),
    )


PORTFOLIOS = {
    "Top 5 (pre-2024 rule)": ["xau-squeeze-momentum-standard/standard", "usdjpy-london-open-momentum/standard",
                              "xau-trend-progression/standard", "us100-orb-new-york-m30/standard",
                              "xau-elliott-wave-1-2-3/standard"],
    "Top 3 (pre-2024 rule)": ["xau-squeeze-momentum-standard/standard", "usdjpy-london-open-momentum/standard",
                              "xau-trend-progression/standard"],
}


def main():
    out = dict(seed=SEED, paths=PATHS, capital=CAPITAL, risks_pct=RISKS, pools=list(POOLS), results=[])
    rng = random.Random(SEED)
    for pname, keys in PORTFOLIOS.items():
        trades = load(keys)
        for pool, (a, b) in POOLS.items():
            weeks = pool_weeks(trades, a, b)
            ntr = sum(len(w) for w in weeks)
            meanR = statistics.fmean(t["R"] for w in weeks for t in w)
            for edge, env in (("real edge", 1.0), ("real edge", 0.0), ("zero edge", 1.0), ("zero edge", 0.0)):
                ws = weeks if edge == "real edge" else zero_edge(weeks)
                equity_model = "conservative" if env else "optimistic"
                for risk in RISKS:
                    if edge == "zero edge" and pool != "full 5y":
                        continue
                    r = simulate(ws, risk, rng, envelope=env)
                    row = dict(portfolio=pname, pool=pool, edge=edge, equity_model=equity_model, risk_pct=risk, pool_weeks=len(weeks),
                               pool_trades=ntr, pool_trades_per_week=round(ntr / len(weeks), 2),
                               pool_mean_R=round(meanR if edge == "real edge" else 0.0, 3), **r)
                    out["results"].append(row)
                    print(f"{pname:<22} {pool:<31} {edge:<9} {equity_model:<12} {risk:>4}%  P1 {r['pass_phase1_pct']:>5}%  both {r['pass_both_pct']:>5}%  "
                          f"<=30d {r['pass_both_within_30d_pct']:>4}% <=90d {r['within_90d_pct']:>5}%  med days {r['median_days_both']}  "
                          f"funded-yr survive {r['funded_year_survival_pct_of_funded']}%  E[payout] ${r['expected_payout_per_attempt_usd']:,}", flush=True)
                    (ROOT / "RESULTS.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
