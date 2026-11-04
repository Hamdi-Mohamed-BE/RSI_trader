# Three-way Monte Carlo on the picked portfolio (2026-11-04)

**Owner request:** add the clip's three Monte Carlo tests to the pipeline and rerun them on the picked portfolio.

**What changed in the pipeline:**
- **`PIPELINE.md` stage 6:** the separate reshuffle / trade-removal / cost-stress lines are replaced by the three-way Monte Carlo.
- **`Calyx Research Pipeline/robustness.py`:** new function `three_monte_carlo` (+2 tests; `test_robustness.py` 7/7 pass).
- **`pipeline-policy.json`:** new block `three_way_monte_carlo`.

The three tests:
1. **Reshuffle** (order luck): the same trades in a random order. Shows where the real drawdown ranks among the shuffles. If it is
   worse than 95% of them, losses come in clumps. Diagnostic only.
2. **Resample** (trade luck): trades drawn with replacement. Gate: at most 5% of full-sample runs end ≤ 0.
3. **Randomize** (the broker): drop 1 trade in 10 and charge every kept trade an extra cost from [0, 2 × 0.05R], on top of the
   recorded Exness costs. Gate: at most 10% of full-sample runs end ≤ 0. Unlike the clip, the drop-only and cost-only runs are also
   reported separately.

The gates and the 0.05R cost were written into the policy before this run.

## Picked portfolio and data
- **Portfolio:** FTMO17 (`Prop Portfolio Selection 2026-11-03/CHOICE.json` pick; also the `ftmo 1_step` roster).
- **Trades:** frozen stream `INPUTS-FTMO17.json`, native Model 4, 2021-10-07 → 2026-10-06, recorded costs. **5,128 closed trades: 85.5 per
  month, 3.94 per weekday.** Two trades still open at the data end are excluded.
- **Summary:** win rate 58.2%, PF 1.26, mean +0.092R per trade, total +470R. Recorded commission averages only 0.005R; the spread is
  already inside the fill prices.
- **Runs:** 1,000 per test, seed 20261104.
- **R** = trade net / initial stop risk. Fixed risk per trade, no compounding, **no guard admission**. % of balance = R × risk.

## Results — full 5 years (5,128 trades)
| Test | Runs ending ≤ 0 | Total R p05 / p50 / p95 | Max drawdown R p50 / p95 | DD p95 at 0.5% / 1% risk |
|---|---:|---|---|---|
| Real run | — | +470 | 24.3 (real) | 12.2% / 24.3% (real) |
| Reshuffle | 0% (total fixed) | +470 | 24.0 / 35.9 | 18.0% / 35.9% |
| Resample | **0.0%** (gate ≤ 5%: PASS) | +360 / +471 / +600 | 24.1 / 38.1 | 19.0% / 38.1% |
| Randomize (drop 10% + 0.05R) | **0.0%** (gate ≤ 10%: PASS) | +157 / +192 / +227 | 54.0 / 74.2 | 37.1% / 74.2% |
| — drop only | 0.0% | +391 / +424 / +458 | 24.8 / 31.7 | |
| — cost only | 0.0% | +211 / +214 / +218 | 56.6 / 58.6 | |

**Reshuffle:** the real drawdown (24.3R) is worse than only **52.4%** of the shuffles, so it sits in the middle. The real losing
streak (11) is longer than 82.4% of the shuffles. No CLUMPED LOSSES flag.

## Results — one-year horizons (1,026 trades each, resampled)
| Test | Runs ending ≤ 0 | Total R p05 / p50 / p95 | Max drawdown R p50 / p95 |
|---|---:|---|---|
| Resample | 0.0% | +40 / +94 / +144 | 16.8 / 29.5 |
| Randomize (drop 10% + 0.05R) | **8.2%** | −8 / +38 / +93 | 22.4 / 40.8 |
| — drop only | 0.1% | +37 / +85 / +140 | 16.0 / 28.0 |
| — cost only | 9.1% | −10 / +42 / +102 | 23.5 / 44.8 |

## Cost ladder (randomize, drop 10% + extra cost)
| Extra cost per trade (mean) | Full 5 years: runs ≤ 0 | Median total R | One year: runs ≤ 0 | Median total R |
|---|---:|---:|---:|---:|
| 0.02R | 0.0% | +330 | 1.1% | +66 |
| 0.05R (declared) | 0.0% | +192 | 8.2% | +38 |
| 0.10R | **96.0%** | −39 | **60.6%** | −8 |
| 0.20R | 100% | −501 | 99.9% | −100 |

The **break-even extra cost is 0.092R per trade**, the portfolio's mean result.

## What it means
- **Luck is not the problem.** Neither order nor trade selection turns it red: 0% of runs over 5 years, 0% for one-year resamples.
  The real drawdown is a typical one, not a lucky one.
- **The broker is.** Just like the clip, randomize is the one that breaks it:
  - At +0.05R extra cost, about 1 year in 12 ends ≤ 0.
  - At +0.10R, 5 years end red 96% of the time.
  - Almost all of the damage is cost. Missing 1 trade in 10 barely matters (0.1% red in a year).
- **Plan drawdowns from the shuffles, not the real run.** The reshuffle p95 is 35.9R (18% at 0.5% risk, without the guard), against
  24.3R in the real run.

## Limits
- Python replay of the native trade stream, in-sample. Every EA and setting was chosen after seeing this history.
- No guard admission: the installed guard skips or cuts entries, so the guarded account's path differs. The prop pass / breach
  numbers stay in `Prop Portfolio Selection 2026-11-03/RESULTS.md`.
- Fixed R per trade, no compounding.
- The trades overlap in time, but each is treated as independent; correlation across EAs on the same day is lost in reshuffle /
  resample (the day-block bootstrap of stage 6 keeps it).
- Extra costs are declared assumptions, not measured broker costs.

Run: `python run.py` → `RESULTS.json` (about 1 minute).
