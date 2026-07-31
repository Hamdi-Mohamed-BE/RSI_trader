# Nasdaq weakness bot — implementation and 2% research report

## Implemented rule

The strongest deterministic interpretation of the supplied notes is:

1. Use `America/New_York` for all New York times.
2. At 10:00 New York time, inspect the fully closed 09:45–10:00 M15 candle.
3. Continue only when that candle is red.
4. Place a sell limit 50 Nasdaq price units above its close.
5. Place the initial stop 100 price units above entry.
6. Target 3R.
7. Expire the order at 12:00 New York time.
8. Risk 2% of current account equity on the complete idea.
9. Reject stale signals, excessive spread, missing candles, and invalid prices.

The source's alternative midpoint/low pair, S1 open short, direct green-candle
fade, 0.1 conversion, 0.25 conversion, 0.5 conversion, and targets from 1.5R to
4R were retained as research variants. They are not the forward default.

## Data

- Source: connected broker M1 history preserved from the continuous `UT100`
  CFD.
- Period: 2025-07-30 through 2026-07-29.
- Bars: 353,771.
- Model: bid OHLC plus historical spread; short exits reconstruct ask.
- Same-minute stop/target ambiguity: stop first.
- Entry slippage: 1.0 Nasdaq price unit.
- Starting balance for percentage-risk comparison: $10,000.
- Risk: 2% compounded per idea.

## Chronological results

Parameters were selected on the first 60% only. The final 20% was untouched
until after selection.

| Segment | Ideas | Win rate | Profit factor | Expectancy | Net | Max DD |
|---|---:|---:|---:|---:|---:|---:|
| Training | 31 | 32.26% | 1.66 | +0.258R | +8.00R | 6.82% |
| Validation | 4 | 50.00% | 3.85 | +0.881R | +3.52R | 2.00% |
| Untouched holdout | 9 | 44.44% | 2.32 | +0.622R | +5.60R | 4.44% |
| Full year, descriptive | 44 | 36.36% | 1.98 | +0.389R | +17.11R | 7.35% |

At 2% compounded risk, the full-year simulation changed $10,000 to
approximately **$13,780.08**. This is a model result, not a guaranteed return.

## Current broker contract check

The same frozen profile was then run without retuning on the connected
broker's currently discovered `NAS100U6` contract. Available M1 history was
2026-06-15 through 2026-07-31.

| Ideas | Win rate | Profit factor | Net | Ending balance | Max DD |
|---:|---:|---:|---:|---:|---:|
| 7 | 57.14% | 4.91 | +7.84R / +$1,632.32 | $11,632.32 | 3.96% |

This is encouraging but is only a seven-idea confirmation sample.

## Cost stress

| Scenario | Ideas | Win rate | PF | Net | Max DD |
|---|---:|---:|---:|---:|---:|
| Baseline | 44 | 36.36% | 1.98 | +17.11R | 7.35% |
| Additional 2 points slippage | 44 | 34.09% | 1.90 | +15.93R | 7.54% |
| Additional 5 points slippage | 44 | 34.09% | 1.79 | +14.23R | 7.80% |

## Decision

The rule is **approved for forward demo testing**, not unattended live
execution. The sample has only 44 ideas, and the currently discovered
`NAS100U6` dated contract is not identical to the historical continuous
`UT100` CFD. Collect at least 30–50 current-contract forward signals and verify
fill quality before considering live deployment.
