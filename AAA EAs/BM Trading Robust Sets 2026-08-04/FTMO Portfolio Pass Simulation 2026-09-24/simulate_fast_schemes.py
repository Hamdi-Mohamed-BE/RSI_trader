"""FTMO 2-Step: can the selected 8-EA combination get funded in 2-4 months? Dynamic risk schemes (research, 2026-09-24).

Portfolio: the 8 EAs chosen by select_portfolio.py (pre-2024-09 greedy selection). Same ledgers, costs, bootstrap and
FTMO rules as simulate.py. Risk is a % of the $100k initial capital, set at entry, never resized later.
Schemes (all frozen before running):
  flat X%            : constant risk.
  floor-scaled X%    : risk = X% * clamp((balance - $90k) / $10k, 0.25, 1)  -> shrinks toward the max-loss floor.
  daily brake        : no new entries once today's closed P/L <= -2.5% of initial (FTMO limit is -5% on equity).
  phase split        : Phase 1 at X% until balance >= +6%, then 0.5%; Phase 2 at 0.5%.
Funded account always runs at flat 0.5% with the daily brake (the challenge setting is not carried into funding).
Reported: pass both phases (within the 365-day cap per phase), funded within 60 / 90 / 120 / 180 days, median days,
funded-year survival and expected payout per attempt.
"""
from __future__ import annotations

import heapq
import json
import random
import statistics
from datetime import datetime

import simulate as S
from select_portfolio import all_rows

CHOSEN = json.loads((S.ROOT / "SELECTION_RESULTS.json").read_text(encoding="utf-8"))["chosen"]
PATHS = 5000
SEED = 20260928
SCHEMES = {
    "flat 0.75%": dict(base=0.75, floor=False, brake=False, split=False),
    "flat 1.0%": dict(base=1.0, floor=False, brake=False, split=False),
    "flat 1.0% + daily brake": dict(base=1.0, floor=False, brake=True, split=False),
    "floor-scaled 1.0% + brake": dict(base=1.0, floor=True, brake=True, split=False),
    "floor-scaled 1.25% + brake": dict(base=1.25, floor=True, brake=True, split=False),
    "floor-scaled 1.5% + brake": dict(base=1.5, floor=True, brake=True, split=False),
    "phase split 1.25% -> 0.5% + brake": dict(base=1.25, floor=False, brake=True, split=True),
    "phase split 1.5% -> 0.5%, floor-scaled + brake": dict(base=1.5, floor=True, brake=True, split=True),
}
FUNDED = dict(base=0.5, floor=False, brake=True, split=False)


def risk_pct(sc, bal, phase):
    r = sc["base"]
    if sc["split"] and (phase == 2 or bal >= S.CAPITAL * 1.06):
        r = 0.5
    if sc["floor"]:
        r *= min(1.0, max(0.25, (bal - 0.9 * S.CAPITAL) / (0.1 * S.CAPITAL)))
    return r


def run_account(stream, sc, phase, target_pct, max_days, funded=False):
    cap = S.CAPITAL
    bal = anchor = cap
    open_pos, days, payouts, heap = {}, set(), [], []
    pid = 0
    anchor_day = None
    day_pl = 0.0
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
            return ("survived" if funded else "timeout"), max_days, payouts
        t, kind, p, R = heapq.heappop(heap)
        d = datetime.fromtimestamp(t, S.PRAGUE).date()
        if d != anchor_day:
            anchor_day, anchor, day_pl = d, bal, 0.0
        if kind == 1:
            if sc["brake"] and day_pl <= -0.025 * cap:
                continue
            open_pos[p] = cap * risk_pct(sc, bal, phase) / 100
            days.add(d)
        else:
            if p not in open_pos:
                continue
            pnl = R * open_pos.pop(p)
            bal += pnl
            day_pl += pnl
        eq = bal - sum(open_pos.values())          # conservative: every open trade at its full stop
        if eq < 0.90 * cap or eq < anchor - 0.05 * cap:
            return "breach", (t - start) / S.DAY, payouts
        if not open_pos:
            if not funded and bal >= cap * (1 + target_pct / 100) and len(days) >= 4:
                return "pass", (t - start) / S.DAY, payouts
            if funded and t - last_pay >= 30 * S.DAY:
                last_pay = t
                if bal > cap:
                    payouts.append(0.8 * (bal - cap))
                    bal = cap
                    anchor = min(anchor, bal)  # a withdrawal is not a trading loss for the daily limit


def simulate(weeks, sc, rng):
    both, pays = [], []
    c = dict(p1=0, surv=0, b1=0, b2=0)
    for _ in range(PATHS):
        s = S.Stream(weeks, rng)
        o1, d1, _ = run_account(s, sc, 1, 10, 365)
        if o1 != "pass":
            c["b1"] += o1 == "breach"; pays.append(0.0); continue
        c["p1"] += 1
        o2, d2, _ = run_account(s, sc, 2, 5, 365)
        if o2 != "pass":
            c["b2"] += o2 == "breach"; pays.append(0.0); continue
        both.append(d1 + d2)
        o3, _, pay = run_account(s, FUNDED, 3, 0, 365, funded=True)
        c["surv"] += o3 == "survived"
        pays.append(sum(pay))
    n = PATHS
    w = lambda lim: round(100 * sum(x <= lim for x in both) / n, 1)
    return dict(pass_phase1_pct=round(100 * c["p1"] / n, 1), pass_both_pct=round(100 * len(both) / n, 1),
                breach_pct=round(100 * (c["b1"] + c["b2"]) / n, 1),
                funded_within_60d_pct=w(60), within_90d_pct=w(90), within_120d_pct=w(120), within_180d_pct=w(180),
                median_days_both=round(statistics.median(both)) if both else None,
                funded_year_survival_pct=round(100 * c["surv"] / len(both), 1) if both else None,
                expected_payout_usd=round(statistics.fmean(pays)))


def main():
    rng = random.Random(SEED)
    out = dict(seed=SEED, paths=PATHS, portfolio=CHOSEN, schemes=SCHEMES, funded_scheme=FUNDED, results=[])
    for label, stress in (("stressed", True), ("reference", False)):
        rows = all_rows(stress)
        trades = [t for k in CHOSEN for t in rows[k]]
        for pool_name, pool in (("full 5y", (None, S.END)), ("post-2024-09 (unseen)", (S.SPLIT, S.END))):
            weeks = S.pool_weeks(trades, *pool)
            for name, sc in SCHEMES.items():
                r = simulate(weeks, sc, rng)
                out["results"].append(dict(costs=label, pool=pool_name, scheme=name, **r))
                print(f"{label:<9} {pool_name:<22} {name:<46} both {r['pass_both_pct']:>5}%  <=60d {r['funded_within_60d_pct']:>5}%  "
                      f"<=90d {r['within_90d_pct']:>5}%  <=120d {r['within_120d_pct']:>5}%  <=180d {r['within_180d_pct']:>5}%  "
                      f"med {r['median_days_both']}d  breach {r['breach_pct']}%  surv {r['funded_year_survival_pct']}%  E ${r['expected_payout_usd']:,}", flush=True)
                (S.ROOT / "RESULTS_FAST_SCHEMES.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
