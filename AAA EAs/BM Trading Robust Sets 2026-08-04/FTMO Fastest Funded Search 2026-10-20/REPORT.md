# FTMO fastest-funded search, 70% pass-rate requirement (2026-10-20)

Owner request: find the best portfolio to get funded fastest with an average pass rate of 70% or more, on an FTMO 2-step Swing $10k account.

**Result: no configuration meets the 70% requirement in development**, which runs over starts from 2021-10 to 2023-04 (392 starts). The best development average pass rate was 63.9%.

The rule declared in advance therefore took the 5 highest-pass finalists forward:
- **Validation, starts 2023-10 to 2024-04:** every finalist collapsed to 6-28% pass.
- **Final out-of-sample window, starts 2024-10 to 2026-04:** the same finalists passed 71-97%.

The choice made by the validation rule is **CORE4_PLUS_FIVE_ORBS_05R at $100**, which is Prop Ready at $100. It did NOT meet 70% in validation. In the out-of-sample window it reached **97.0%** pass, with a median of 73 days to funded.

So the pass rate depends on the market regime, not on which portfolio you pick. No single portfolio reached 70% across all periods. The out-of-sample window was also previously inspected by earlier studies, so its 97% is a retrospective check, not untouched data.

Method:
- **Engine and data:** the Faster Screen engine through the dial-study subclass, fed with parity-checked native streams for 16 FTMO-package EAs (3 Way Gold excluded).
- **Menu:** 18 baskets × 4 caps ($50 / $75 / $100 / $150) = 72 configurations.
- **Scenarios:** recorded costs and cost stress, with next-day phase handover.
- **Split:** chronological development / validation / out-of-sample, as in PIPELINE 5.1. Everything was pre-declared in `PLAN.json` and hash-frozen in `FROZEN.json`.
- **Pass definition:** both phases done within 180 days without a breach.

## Development (all 72 configurations, top 20 by average pass)

| Portfolio | Cap | EAs | Avg pass ≤180 d (recorded / stress) | Avg passed ≤90 d | Avg median days to funded | Breaches | Hit $9,200 buffer | Worst equity DD $ | Worst day $ | Trades /month / weekday | Distinct pass dates |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|---|---:|
| CORE4_PLUS_EMA3 | $150 | 5 | 63.9% (74.0% / 53.8%) | 39.7% | 84.8 | 0 | 50.8% | 1,738 | 290 | 12.77 / 0.587 | 24 |
| CORE4_PLUS_H1_ORB_05R | $100 | 5 | 59.8% (67.3% / 52.3%) | 33.9% | 94.0 | 0 | 46.6% | 1,753 | 244 | 32.23 / 1.482 | 19 |
| CORE4_PLUS_FIVE_ORBS_05R | $100 | 9 | 57.9% (66.3% / 49.5%) | 30.9% | 93.5 | 0 | 53.2% | 1,740 | 242 | 35.11 / 1.615 | 17 |
| PR9_PLUS_NASDAQ_OVERNIGHT | $100 | 10 | 57.9% (66.3% / 49.5%) | 30.9% | 93.5 | 0 | 53.2% | 1,740 | 242 | 35.15 / 1.617 | 17 |
| CORE4 | $100 | 4 | 56.5% (61.5% / 51.5%) | 30.5% | 96.0 | 0 | 45.0% | 1,712 | 241 | 27.87 / 1.282 | 17 |
| ALL12 | $150 | 12 | 55.6% (59.7% / 51.5%) | 37.2% | 72.8 | 0 | 51.0% | 1,778 | 290 | 14.88 / 0.684 | 21 |
| CORE4_PLUS_GOLD_VA_H1_ORB | $100 | 6 | 52.5% (58.2% / 46.9%) | 36.1% | 80.8 | 0 | 44.9% | 1,660 | 222 | 39.85 / 1.833 | 11 |
| CORE4_PLUS_EMA3 | $100 | 5 | 51.8% (64.0% / 39.5%) | 29.1% | 90.5 | 0 | 56.2% | 1,746 | 246 | 24.18 / 1.112 | 15 |
| CORE4_PLUS_GOLD_VA | $100 | 5 | 51.1% (57.6% / 44.6%) | 35.2% | 82.8 | 0 | 41.1% | 1,649 | 222 | 36.74 / 1.69 | 10 |
| PR9_PLUS_GOLDVA | $100 | 10 | 50.9% (58.2% / 43.6%) | 37.4% | 77.2 | 0 | 60.5% | 1,740 | 243 | 41.43 / 1.906 | 9 |
| CORE4_PLUS_TREND_06R | $100 | 5 | 50.5% (61.2% / 39.8%) | 27.9% | 92.5 | 0 | 50.0% | 1,787 | 258 | 30.44 / 1.4 | 14 |
| CORE4_PLUS_EMA3 | $75 | 5 | 50.4% (57.9% / 42.9%) | 16.3% | 115.2 | 0 | 29.8% | 1,548 | 241 | 32.97 / 1.517 | 13 |
| CORE4_MINUS_MONTH_END | $100 | 3 | 49.4% (54.9% / 43.9%) | 25.5% | 96.2 | 0 | 50.8% | 1,626 | 247 | 25.61 / 1.178 | 15 |
| CORE4_PLUS_H1_ORB_05R | $75 | 5 | 48.7% (58.2% / 39.3%) | 15.2% | 115.8 | 0 | 44.8% | 1,815 | 244 | 35.05 / 1.612 | 15 |
| CORE4_PLUS_FIVE_ORBS_05R | $75 | 9 | 48.6% (61.5% / 35.7%) | 16.8% | 117.0 | 0 | 50.8% | 1,877 | 255 | 38.69 / 1.78 | 14 |
| PR9_PLUS_NASDAQ_OVERNIGHT | $75 | 10 | 48.6% (61.5% / 35.7%) | 16.8% | 117.0 | 0 | 50.6% | 1,877 | 255 | 39.26 / 1.806 | 14 |
| ALL12 | $75 | 12 | 47.6% (57.4% / 37.8%) | 21.8% | 100.5 | 0 | 43.8% | 1,532 | 242 | 49.53 / 2.278 | 6 |
| CORE3 | $100 | 3 | 47.4% (53.6% / 41.3%) | 26.2% | 90.5 | 0 | 47.1% | 1,933 | 241 | 24.84 / 1.142 | 14 |
| CORE4_PLUS_GOLD_VA | $75 | 5 | 44.8% (54.6% / 34.9%) | 12.9% | 123.2 | 0 | 27.3% | 1,487 | 242 | 41.94 / 1.929 | 6 |
| CORE4_MINUS_NASDAQ_PLUS_GOLD_VA | $150 | 4 | 44.5% (55.6% / 33.4%) | 7.9% | 135.0 | 0 | 51.5% | 1,636 | 200 | 22.19 / 1.021 | 7 |

## Validation (finalists)

| Portfolio | Cap | EAs | Avg pass ≤180 d (recorded / stress) | Avg passed ≤90 d | Avg median days to funded | Breaches | Hit $9,200 buffer | Worst equity DD $ | Worst day $ | Trades /month / weekday | Distinct pass dates |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|---|---:|
| CORE4_PLUS_EMA3 | $150 | 5 | 6.4% (8.3% / 4.5%) | 3.0% | 112.8 | 0 | 95.1% | 1,839 | 218 | 7.78 / 0.358 | 1 |
| CORE4_PLUS_H1_ORB_05R | $100 | 5 | 20.7% (24.8% / 16.5%) | 15.8% | 75.5 | 0 | 84.6% | 1,796 | 236 | 16.4 / 0.754 | 5 |
| CORE4_PLUS_FIVE_ORBS_05R | $100 | 9 | 28.2% (42.1% / 14.3%) | 21.8% | 73.5 | 0 | 79.7% | 1,725 | 237 | 19.28 / 0.887 | 4 |
| PR9_PLUS_NASDAQ_OVERNIGHT | $100 | 10 | 26.7% (39.1% / 14.3%) | 21.4% | 72.8 | 0 | 80.5% | 1,725 | 237 | 19.28 / 0.887 | 4 |
| CORE4 | $100 | 4 | 23.7% (31.6% / 15.8%) | 17.3% | 85.8 | 0 | 79.7% | 1,761 | 237 | 15.39 / 0.708 | 5 |

## Out-of-sample, previously inspected (finalists, evaluated once)

| Portfolio | Cap | EAs | Avg pass ≤180 d (recorded / stress) | Avg passed ≤90 d | Avg median days to funded | Breaches | Hit $9,200 buffer | Worst equity DD $ | Worst day $ | Trades /month / weekday | Distinct pass dates |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|---|---:|
| CORE4_PLUS_EMA3 | $150 | 5 | 71.3% (74.6% / 68.0%) | 33.5% | 103.0 | 0 | 41.6% | 1,345 | 303 | 13.74 / 0.632 | 18 |
| CORE4_PLUS_H1_ORB_05R | $100 | 5 | 93.8% (92.9% / 94.7%) | 69.4% | 74.5 | 0 | 9.8% | 1,166 | 271 | 31.65 / 1.456 | 39 |
| CORE4_PLUS_FIVE_ORBS_05R | $100 | 9 | 97.0% (96.5% / 97.5%) | 69.9% | 73.0 | 0 | 7.7% | 1,120 | 271 | 34.71 / 1.596 | 42 |
| PR9_PLUS_NASDAQ_OVERNIGHT | $100 | 10 | 95.4% (96.5% / 94.4%) | 71.6% | 69.0 | 0 | 9.0% | 1,214 | 271 | 38.67 / 1.779 | 42 |
| CORE4 | $100 | 4 | 94.3% (95.9% / 92.6%) | 69.4% | 78.5 | 0 | 9.0% | 1,207 | 271 | 28.44 / 1.308 | 36 |

## What this does NOT prove

- **Previously inspected.** All windows were inspected before, and the EA settings were developed on overlapping years.
- **Simulated execution.** Prices are generated-tick Exness tester data before 2026, equity is sampled every 5 minutes, and costs are modelled rather than FTMO's own.
- **Overlapping starts.** Pass rates are shares of overlapping start dates, not independent probabilities.
- **Stalled accounts count as not passed.** Passing at 180 days excludes accounts stalled at the $9,200 entry buffer, which FTMO would not fail but which cannot trade under the guard.

## Files

- [PLAN.json](PLAN.json), [FROZEN.json](FROZEN.json), [ELIGIBILITY.json](ELIGIBILITY.json).
- [DEV.json](DEV.json), [VAL.json](VAL.json), [OOS.json](OOS.json).
- [run.py](run.py).
