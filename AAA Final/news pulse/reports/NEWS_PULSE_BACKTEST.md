# XAUUSD News Pulse Backtest

PPI-only OCO, 5R, one re-entry; 1% compounded risk.

| Sample | Trades | Win rate | PF | Net | Max DD |
|---|---:|---:|---:|---:|---:|
| Development | 20 | 45.00% | 3.07 | +16.05R | 3.09% |
| Untouched holdout | 4 | 50.00% | 2.89 | +3.78R | 1.22% |
| Full | 24 | 45.83% | 3.03 | +19.83R | 3.09% |
| Unfiltered stress | 106 | 23.58% | 1.03 | +1.91R | 12.89% |

**Status:** provisional/selection-biased; small holdout. Live execution is disabled by default.

Historical simulation includes bid/ask triggers, spread, pessimistic M1 ordering, and compounding. It is not a guarantee.
