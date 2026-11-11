# Overnight Bias ORB optimisation: result (2026-11-11)

**Verdict: REJECTED AT VALIDATION. Keep the current (raw) rules.** Plan frozen 2026-11-10 (PLAN.md); 173 native runs (RUNS.jsonl); research EA parity with the raw EA 782/782 trades.
USTEC M15, native, 150 ms, $10k, 1%. Development: Model 1 screen + Model 4 confirmation; validation, OOS and all-years: Model 4. Windows (data_split): dev 2019-07-16 -> 2023-11-11
(51.9 months), validation -> 2024-11-11 (12), OOS -> 2026-11-11 (24, previously viewed in the raw study). Trades/day uses 21 trading days per month.

| Version | Window | Return | PF | Trades | /month | /day | Win | Equity DD | Return/DD |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Current | dev | +54.1% | 1.22 | 462 | 8.9 | 0.42 | 48.1% | 10.7% | 5.04 |
| Finalist 1 (trail 1R/1R, flat 15:55) | dev | +82.9% | 1.42 | 358 | 6.9 | 0.33 | 55.0% | 8.1% | 10.30 |
| Finalist 2 (break-even 1R, flat 15:55) | dev | +110.8% | 1.52 | 358 | 6.9 | 0.33 | 36.0% | 11.1% | 9.98 |
| Finalist 3 (break-even 1R, flat 15:30) | dev | +100.8% | 1.50 | 358 | 6.9 | 0.33 | 36.3% | 10.5% | 9.65 |
| Current | validation | **+28.8%** | **1.56** | 111 | 9.3 | 0.44 | 46.8% | 8.2% | 3.50 |
| Finalist 1 | validation | -5.6% | 0.88 | 92 | 7.7 | 0.37 | 48.9% | 11.1% | -0.50 |
| Finalist 2 | validation | +1.1% | 1.02 | 92 | 7.7 | 0.37 | 26.1% | 8.6% | 0.13 |
| Finalist 3 | validation | +1.0% | 1.02 | 92 | 7.7 | 0.37 | 28.3% | 10.1% | 0.10 |
| Current | OOS | **+54.1%** | **1.58** | 209 | 8.7 | 0.41 | 53.6% | 10.2% | 5.30 |
| Finalist 2 (diagnostic only) | OOS | +10.0% | 1.12 | 177 | 7.4 | 0.35 | 31.6% | 12.5% | 0.80 |
| Current | all 2019-07 -> 2026-11 | +205.3% | 1.40 | 782 | 8.9 | 0.42 | 49.4% | 10.7% | 19.13 |
| Finalist 2 | all | +134.3% | 1.28 | 627 | 7.1 | 0.34 | 33.3% | 12.5% | 10.76 |
| Buy and hold USTEC CFD | all | +44.7% | - | 1 | - | - | - | 75.2% | 0.59 |

All finalists share ADX > 30, stop 0.20 x 15-day average daily range, 5R target, last entry 14:00 NY. They pass the plateau (100% of 12-13 neighbours profitable on dev) but all three
fail validation (need PF >= 1.15, positive and better return/DD than current), so none goes to OOS. The search fitted 2019-23 and gave up the edge after it.

Monte Carlo (three-way, 1,000 runs, all years): current resample 0.0% red, randomize 0.0% red -> PASS; diagnostic finalist 0.5% / 0.0%.
Buy and hold: USTEC CFD price +252.6% but swap -207.9% of the account -> +44.7%, equity DD 75%; dev -26.9%, validation +21.9%, OOS +10.6%. The current ONB beats it in every window.
Execution note: the flat-time close is refused while the market is shut (US holidays); 6 of 782 current trades were held past the flat time (net -$950), 3 of 627 for finalist 2.
The current rules come from a video and were first tested on this same history, so its OOS is not untouched. Nothing installed or changed.
