"""FTMO 2-Step simulation for Nasdaq 5M Candle Momentum alone, with the Recommended Adaptive risk governor.

Research only (2026-09-24). Reuses simulate.py (same folder) for costs, weekly bootstrap and constants.

Trades: the audited native MT5 5y ledger `nasdaq-5m-candle-momentum/standard` from
../FTMO Combination Study 2026-09-19/prepared.json (1,267 trades 2021-09 -> 2026-08, original stops, commission, swap).
It includes the known Friday/holiday late exits of the production EA as they happened in the tester.

Sizing, as the EA does it: risk = current balance x risk% x multiplier, fixed at entry (never resized later).
Recommended Adaptive governor, copied from _Shared/CalyxAdaptivePortfolio.mqh:
  - new entries blocked for the day when today's closed P/L <= -5% of the reference (phase start) balance;
  - drawdown from the closed-balance peak of the current account: >= 4% -> x0.50, >= 7% -> x0.25;
  - consecutive closed losses of this EA: >= 3 -> x0.50, >= 5 -> x0.25; factors multiply.
  - The installer's Recommended Adaptive profile additionally applies a 0.25x base factor to this EA
    (_Auto Deploy/Install-BMTradingPortfolio.ps1, AdaptiveBaseMultiplier).
Each FTMO phase and the funded account are new accounts, so peak/streak/reference reset at each start.
FTMO rules and account model are identical to simulate.py (see its docstring).
"""
from __future__ import annotations

import heapq
import json
import random
import statistics
from datetime import datetime
from pathlib import Path

import simulate as S

KEY = "nasdaq-5m-candle-momentum/standard"
PATHS = 5000
SEED = 20260925
SCENARIOS = {
    "A. 1% + adaptive governor": dict(risk=1.0, base=1.0, adaptive=True),
    "B. Recommended Adaptive as installed (1% x 0.25 + governor)": dict(risk=1.0, base=0.25, adaptive=True),
    "C. Flat 1% (no governor)": dict(risk=1.0, base=1.0, adaptive=False),
    "D. 0.5% + adaptive governor": dict(risk=0.5, base=1.0, adaptive=True),
}
POOLS = {"full 5y": (None, S.END), "post-2024-09 (recent)": (S.SPLIT, S.END)}


def load(stress):
    data = json.loads((S.STUDY / "prepared.json").read_text(encoding="utf-8-sig"))
    out = []
    for r in data["rows"][KEY]:
        g, c, s, x = S.costs(r, stress)
        out.append(dict(key=KEY, op=r["op"], cl=max(r["cl"], r["op"] + 1), R=(g + c + s - x) / r["unit_risk"]))
    return out


def governor(bal, peak, streak, day_pl, reference):
    if day_pl <= -0.05 * reference:
        return 0.0
    dd = 100 * (peak - bal) / peak if peak > 0 else 0.0
    m = 0.25 if dd >= 7 else 0.5 if dd >= 4 else 1.0
    m *= 0.25 if streak >= 5 else 0.5 if streak >= 3 else 1.0
    return m


def run_account(stream, sc, target_pct, max_days, funded=False, envelope=1.0):
    cap = S.CAPITAL
    bal = peak = anchor = cap
    open_pos, days, payouts, heap = {}, set(), [], []
    streak = pid = trades = 0
    anchor_day = None
    day_pl = 0.0
    mults = []
    start, wk = stream.next_week()
    last_pay, next_week, limit = start, start + S.WEEK, start + max_days * S.DAY

    def push(week_trades):
        nonlocal pid
        for op, cl, R in week_trades:
            pid += 1
            heapq.heappush(heap, (op, 1, pid, R))
            heapq.heappush(heap, (cl, 2, pid, R))

    push(wk)
    while True:
        while not heap or heap[0][0] >= next_week:
            if next_week >= limit:
                break
            push(stream.next_week()[1])
            next_week += S.WEEK
        if not heap or heap[0][0] >= limit:
            return ("survived" if funded else "timeout"), max_days, payouts, trades, mults
        t, kind, p, R = heapq.heappop(heap)
        d = datetime.fromtimestamp(t, S.PRAGUE).date()
        if d != anchor_day:
            anchor_day, anchor, day_pl = d, bal, 0.0
        if kind == 1:
            m = sc["base"] * (governor(bal, peak, streak, day_pl, cap) if sc["adaptive"] else 1.0)
            if m <= 0:
                continue  # entry blocked by the daily closed-P/L stop; the close event is then ignored
            open_pos[p] = bal * sc["risk"] / 100 * m
            mults.append(m)
            days.add(d)
        else:
            if p not in open_pos:
                continue
            risk_usd = open_pos.pop(p)
            pnl = R * risk_usd
            bal += pnl
            day_pl += pnl
            peak = max(peak, bal)
            streak = streak + 1 if pnl < 0 else 0
            trades += 1
        equity_low = bal - envelope * sum(open_pos.values())
        if equity_low < 0.90 * cap or equity_low < anchor - 0.05 * cap:
            return "breach", (t - start) / S.DAY, payouts, trades, mults
        if not open_pos:
            if not funded and bal >= cap * (1 + target_pct / 100) and len(days) >= 4:
                return "pass", (t - start) / S.DAY, payouts, trades, mults
            if funded and t - last_pay >= 30 * S.DAY:
                last_pay = t
                if bal > cap:
                    payouts.append(0.8 * (bal - cap))
                    bal = cap
                    peak = max(peak, bal)


def pct(v, q):
    v = sorted(v)
    return round(v[min(len(v) - 1, int(q * (len(v) - 1)))], 0) if v else None


def simulate(weeks, sc, rng, envelope):
    n = PATHS
    p1d, p2d, both, pays, mult_all = [], [], [], [], []
    c = dict(p1=0, both=0, b1=0, b2=0, t1=0, t2=0, surv=0)
    for _ in range(n):
        s = S.Stream(weeks, rng)
        o1, d1, _, _, m1 = run_account(s, sc, 10, 365, envelope=envelope)
        mult_all += m1
        if o1 != "pass":
            c["b1" if o1 == "breach" else "t1"] += 1
            pays.append(0.0)
            continue
        c["p1"] += 1; p1d.append(d1)
        o2, d2, _, _, m2 = run_account(s, sc, 5, 365, envelope=envelope)
        mult_all += m2
        if o2 != "pass":
            c["b2" if o2 == "breach" else "t2"] += 1
            pays.append(0.0)
            continue
        c["both"] += 1; p2d.append(d2); both.append(d1 + d2)
        o3, _, pay, _, _ = run_account(s, sc, 0, 365, funded=True, envelope=envelope)
        c["surv"] += o3 == "survived"
        pays.append(sum(pay))
    within = lambda lim: round(100 * sum(x <= lim for x in both) / n, 1)
    return dict(
        pass_phase1_pct=round(100 * c["p1"] / n, 1),
        pass_phase2_given_phase1_pct=round(100 * c["both"] / c["p1"], 1) if c["p1"] else None,
        pass_both_pct=round(100 * c["both"] / n, 1),
        breach_phase1_pct=round(100 * c["b1"] / n, 1), unfinished_phase1_365d_pct=round(100 * c["t1"] / n, 1),
        breach_phase2_pct=round(100 * c["b2"] / n, 1), unfinished_phase2_365d_pct=round(100 * c["t2"] / n, 1),
        phase1_days_p25_median_p75=[pct(p1d, .25), pct(p1d, .5), pct(p1d, .75)],
        phase2_days_p25_median_p75=[pct(p2d, .25), pct(p2d, .5), pct(p2d, .75)],
        both_days_p25_median_p75=[pct(both, .25), pct(both, .5), pct(both, .75)],
        funded_within_30d_pct=within(30), within_60d_pct=within(60), within_90d_pct=within(90),
        within_180d_pct=within(180), within_365d_pct=within(365),
        funded_year_survival_pct=round(100 * c["surv"] / c["both"], 1) if c["both"] else None,
        expected_payout_per_attempt_usd=round(statistics.fmean(pays)),
        average_risk_multiplier=round(statistics.fmean(mult_all), 3) if mult_all else None,
    )


def main():
    rng = random.Random(SEED)
    out = dict(seed=SEED, paths=PATHS, ea=KEY, scenarios=SCENARIOS, results=[])
    for costs_label, stress in (("reference costs", False), ("stressed costs", True)):
        trades = load(stress)
        for pool, (a, b) in POOLS.items():
            weeks = S.pool_weeks(trades, a, b)
            meanR = statistics.fmean(t["R"] for w in weeks for t in w)
            for name, sc in SCENARIOS.items():
                for env, eq in ((1.0, "conservative"), (0.0, "optimistic")):
                    r = simulate(weeks, sc, rng, env)
                    row = dict(scenario=name, costs=costs_label, pool=pool, equity_model=eq,
                               pool_trades=sum(len(w) for w in weeks), pool_mean_R=round(meanR, 3), **r)
                    out["results"].append(row)
                    print(f"{costs_label:<15} {pool:<22} {eq:<12} {name[:48]:<48} P1 {r['pass_phase1_pct']:>5}%  P2|P1 {r['pass_phase2_given_phase1_pct']}%  "
                          f"both {r['pass_both_pct']:>5}%  days P1 {r['phase1_days_p25_median_p75']} P2 {r['phase2_days_p25_median_p75']} "
                          f"both {r['both_days_p25_median_p75']}  <=90d {r['within_90d_pct']}%  surv {r['funded_year_survival_pct']}%  "
                          f"E ${r['expected_payout_per_attempt_usd']:,}  avg mult {r['average_risk_multiplier']}  meanR {round(meanR, 3)}", flush=True)
                    (S.ROOT / "RESULTS_N5_ADAPTIVE.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
