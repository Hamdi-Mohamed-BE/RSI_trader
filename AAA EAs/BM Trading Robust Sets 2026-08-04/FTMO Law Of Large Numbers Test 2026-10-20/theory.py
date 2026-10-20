"""Part A: does 'PF > 0.95 + many bets' pass FTMO? Pure maths: i.i.d. 1:1 bets under FTMO 2-step Swing $10k rules.

Rules modelled: phase 1 +10%, phase 2 +5%, static floor -10% of the phase start, daily loss 5% of initial measured from
the day-start balance, >= 4 trading days per phase (once the target is hit the account stops risking money and only
places a token trade per day until 4 days are reached), 128 trading days (~180 calendar days) to finish both phases.
Funded stage illustration: 40 trading days, 80% of profit paid at day 20 and 40 if positive (balance reset to start),
fee refunded with the first payout. Win probability p = PF/(1+PF) for 1:1 bets (costs folded into PF).
python theory.py -> THEORY.json + THEORY.md
"""
import json
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parent
PATHS, SEED, DAYS, FUNDED_DAYS = 20000, 20261020, 128, 40
FEE = 170.0          # FTMO 10k fee is EUR 155 per data/prop-rules/ftmo-2step-swing.json; ~USD 170 assumed for illustration
PFS = [0.90, 0.95, 1.00, 1.05, 1.20]
RISKS = [0.0025, 0.005, 0.01, 0.02]
BETS_PER_DAY = [3, 10]


def simulate(pf, risk, k, rng):
    p = pf / (1 + pf); n = PATHS; start = 10000.0
    phase = np.ones(n, int)            # 1, 2 = evaluation; 3 = funded; 0 = failed; 9 = unfinished
    bal = np.full(n, start); days = np.zeros(n, int); reached = np.zeros(n, bool)
    passed_day = np.full(n, -1); payout = np.zeros(n); refunded = np.zeros(n, bool); funded_day = np.zeros(n, int)
    eval_fail = np.zeros(n, bool); funded_fail = np.zeros(n, bool)
    for d in range(DAYS + FUNDED_DAYS):
        anchor = bal.copy()
        evaluating = (phase == 1) | (phase == 2)
        if d >= DAYS:
            phase[evaluating] = 9; evaluating[:] = False
        trading = (evaluating & ~reached) | (phase == 3)
        days[evaluating] += 1                     # a traded day (token trade if target already reached)
        for _ in range(k):
            win = rng.random(n) < p
            step = np.where(win, risk, -risk) * start
            bal = np.where(trading, bal + step, bal)
            dead = trading & ((bal <= start * 0.90 + 1e-9) | (bal <= anchor - 0.05 * start + 1e-9))
            eval_fail |= dead & (phase != 3); funded_fail |= dead & (phase == 3)
            phase[dead] = 0; trading &= ~dead
            target = np.where(phase == 1, start * 1.10, start * 1.05)
            hit = trading & ((phase == 1) | (phase == 2)) & (bal >= target - 1e-9)
            reached |= hit; trading &= ~hit
        done = ((phase == 1) | (phase == 2)) & reached & (days >= 4)
        p1 = done & (phase == 1); p2 = done & (phase == 2)
        phase[p1] = 2; bal[p1] = start; days[p1] = 0; reached[p1] = False
        phase[p2] = 3; bal[p2] = start; passed_day[p2] = d; funded_day[p2] = 0
        f = phase == 3
        funded_day[f] += 1
        pay = f & ((funded_day == 20) | (funded_day == 40)) & (bal > start)
        payout[pay] += 0.8 * (bal[pay] - start) + np.where(refunded[pay], 0, FEE); refunded |= pay; bal[pay] = start
        phase[f & (funded_day >= FUNDED_DAYS)] = 7   # funded window ended
    passed = passed_day >= 0
    cal = (passed_day[passed] + 1) * 7 / 5 + 7      # trading days -> calendar days, + ~5 business days review
    ev = payout.mean() - FEE
    return dict(pf=pf, risk_pct=risk * 100, bets_per_day=k, p_win=round(p, 4), pass_both=round(passed.mean(), 4),
                failed=round(float(eval_fail.mean()), 4), funded_breach=round(float(funded_fail.mean()), 4), median_days_to_funded=round(float(np.median(cal)), 1) if passed.any() else None,
                funded_within_90=round(float(((passed_day >= 0) & ((passed_day + 1) * 7 / 5 + 7 <= 90)).mean()), 4),
                avg_payout_per_attempt=round(float(payout.mean()), 2), ev_per_attempt_usd=round(float(ev), 2))


def main():
    rng = np.random.default_rng(SEED); rows = []
    for pf in PFS:
        for risk in RISKS:
            for k in BETS_PER_DAY:
                rows.append(simulate(pf, risk, k, rng))
    (R / 'THEORY.json').write_text(json.dumps(dict(paths=PATHS, seed=SEED, fee_usd_assumed=FEE, rows=rows), indent=1), encoding='utf-8')
    md = ['| PF | Risk / bet | Bets / day | P(pass both ≤ ~6 months) | P(funded ≤ 90 days) | Median days to funded | P(fail evaluation) | P(funded then breached ≤40 d) | EV per attempt (fee $170, 40 funded days) |',
          '|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        md.append(f"| {r['pf']:.2f} | {r['risk_pct']:g}% | {r['bets_per_day']} | {100 * r['pass_both']:.1f}% | {100 * r['funded_within_90']:.1f}% | "
                  f"{r['median_days_to_funded'] if r['median_days_to_funded'] is not None else '—'} | {100 * r['failed']:.1f}% | {100 * r['funded_breach']:.1f}% | {r['ev_per_attempt_usd']:+,.0f} $ |")
    (R / 'THEORY.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
    print('\n'.join(md))


if __name__ == '__main__':
    main()
