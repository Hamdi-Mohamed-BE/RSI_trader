# Vault Break optimisation: result (2026-11-11)

**Verdict: REJECTED AT VALIDATION. Keep the current (raw) rules for now.** Plan frozen 2026-11-10 (PLAN.md); 158 native runs (RUNS.jsonl).
Parity: 1,659/1,659 trades identical to the raw EA (3 extra research trades on 2026-11-09 excluded: the raw run had only part of that day; PARITY.json).
USTEC M30, native, 150 ms, $10k, 1%. Windows: dev 2019-07-16 -> 2023-11-11 (51.9 months), validation -> 2024-11-11 (12), OOS -> 2026-11-11 (24, previously viewed). 21 trading days per month.

| Version | Window | Return | PF | Trades | /month | /day | Win | Equity DD | Return/DD |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Current | dev | +14.9% | 1.06 | 904 | 17.4 | 0.83 | 62.4% | 11.7% | 1.28 |
| Finalist 1 (3R target, 1 trade/day, trail 1.5R/1R, flat 15:55) | dev | +77.7% | 1.33 | 503 | 9.7 | 0.46 | 56.1% | 7.8% | 10.03 |
| Finalist 2 (same, no trail) | dev | +75.5% | 1.32 | 503 | 9.7 | 0.46 | 54.5% | 7.6% | 9.88 |
| Finalist 3 (3R, trail, flat 15:55, 3 trades/day) | dev | +79.3% | 1.27 | 599 | 11.5 | 0.55 | 54.9% | 8.9% | 8.88 |
| Current | validation | -10.7% | 0.85 | 238 | 19.8 | 0.94 | 58.0% | 15.9% | -0.67 |
| Finalist 1 | validation | -10.1% | 0.82 | 118 | 9.8 | 0.47 | 40.7% | 15.0% | -0.68 |
| Finalist 2 | validation | -11.6% | 0.80 | 118 | 9.8 | 0.47 | 39.8% | 16.7% | -0.70 |
| Finalist 3 | validation | -4.9% | 0.93 | 152 | 12.7 | 0.60 | 45.4% | 12.3% | -0.40 |
| Current | OOS | +25.1% | 1.14 | 520 | 21.7 | 1.03 | 66.2% | 10.7% | 2.34 |
| Finalist 3 (diagnostic only) | OOS | +19.5% | 1.11 | 327 | 13.6 | 0.65 | 48.9% | 19.2% | 1.01 |
| Current | all 2019-07 -> 2026-11 | +28.5% | 1.05 | 1,662 | 18.9 | 0.90 | 62.9% | 16.6% | 1.71 |
| Finalist 3 | all (includes its fitted dev years) | +103.7% | 1.14 | 1,078 | 12.3 | 0.58 | 51.8% | 19.2% | 5.40 |
| Buy and hold USTEC CFD | all | +43.2% | - | 1 | - | - | - | 75.2% | 0.57 |

Plateau: 100% of 16-19 neighbours profitable for all three finalists. Validation: all three lose (need PF >= 1.15 and positive), so none goes to OOS.
Monte Carlo, all years: current resample 14.1% red, randomize 100% red -> FAIL (its edge is thinner than the +0.10R cost assumption); finalist 3 resample 0.9%, randomize 1.9% -> pass,
but its all-years result includes the development years it was fitted on, and it did worse than the current rules in both validation and OOS-diagnostic return/DD, so it is not qualified.
Buy and hold USTEC: dev -26.9%, validation +21.9%, OOS +10.1%; price +252% but swap -208% of the account. Both Vault versions beat buy and hold on return/DD.
The current Vault rules already failed the raw gate and were kept only by owner approval; this search found nothing that holds up after 2023. Nothing installed or changed.
