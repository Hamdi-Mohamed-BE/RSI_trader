# XAU Closing Momentum — Raw Result

Decision: **skip the full pipeline**. The unoptimized signal is negative in every evidence window and fails most clearly in the fully clean six-month sample.

## Rule tested

- Instrument: Exness `XAUUSD` CFD on M1 data.
- At 13:00 New York, compare price with the previous trading day's 13:30 COMEX close.
- Positive return opens long; negative return opens short.
- Flatten during the final tradable minute before 13:30 New York.
- No momentum threshold, trend filter, weekday selection, take-profit, trailing stop, or tuned exit.
- Common execution wrapper: USD 10,000 balance, 1% equity risk sized against a 2% emergency price stop.
- MT5 Every Tick, random execution delay, recorded spread and commission.

## Clean evidence

| Window | Dates | Return | Net P/L | PF | Win rate | Max DD | Trades | Max W/L streak | Commission |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 6m | 2026-03-05 to 2026-09-05 | -4.16% | -$416.43 | ~0.55 | 44.19% | 4.69% | 129 | 6 / 6 | -$13.79 |
| 1y | 2025-09-05 to 2026-09-05 | -2.08% | -$208.22 | ~0.87 | 49.16% | 6.63% | 238 | 6 / 6 | -$25.83 |
| 3y | 2023-09-05 to 2026-09-05 | -2.57% | -$257.24 | ~0.92 | 48.60% | 6.39% | 714 | 9 / 8 | -$91.23 |
| 5y | 2021-09-05 to 2026-09-05 | -7.71% | -$771.20 | ~0.81 | 46.08% | 8.09% | 1,187 | 9 / 9 | -$166.40 |

Net P/L includes commissions. Valid trades have zero swap because they are intraday. Profit factor and drawdown in this table are reconstructed from the rounded MT5 deal ledger; the untouched six-month native report shows PF 0.56 and DD 4.84%.

## Data-quality audit

The older Exness archive rejected some closes at the COMEX boundary as `market closed`, creating overnight positions that are not part of the paper rule. Trades held for more than 60 minutes were excluded: 0 in 6m, 18 in 1y, 57 in 3y, and 98 in 5y. They are retained in the native reports for auditability but are not used in the clean result above.

Every Tick and 1-minute-OHLC control runs were materially identical. The clean six-month window contains no exclusions and is already decisively negative, so the rejection does not depend on the older archive issue.

## Interpretation

The standalone XAU CFD translation does not reproduce a durable close-to-close continuation edge. Long trades lost $597.19 over the clean five-year set and short trades lost $174.01. This is consistent with the idea that a pooled futures result does not automatically become a profitable single-instrument CFD EA after spread and commission.

No website, BAT, or live portfolio files were changed.
