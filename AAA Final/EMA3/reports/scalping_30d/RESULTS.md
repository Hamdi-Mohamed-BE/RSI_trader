# EMA3 Gold Scalping — 30-Day Result

Data: connected-MT5 `XAUUSD..`, 2026-07-05 13:06 UTC through 2026-08-04
13:06 UTC. Starting balance: $1,000. Flat risk: 1% per trade. Historical
broker spread is included. Targets and trailing exits are capped at 1.7R.

The first 75% selected each timeframe's configuration. The final 25% was left
untouched for validation.

| TF | Selected setup | Full trades | Full WR | Full PF | Full net | Full max DD | Untouched trades | Untouched WR | Untouched PF | Untouched net | Untouched max DD |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| M1 | pivot 8, EMA200 slope 6, trail 1R/0.5R, 1.7R cap | 623 | 40.77% | 0.88 | -39.81R | 49.91% | 153 | 39.22% | 0.81 | -16.37R | 22.26% |
| M5 | pivot 6, no EMA filter, trail 1R/0.5R, 1.7R cap | 572 | 40.73% | 0.91 | -19.15R | 37.13% | 146 | 39.04% | 0.87 | -7.76R | 12.84% |
| M15 | pivot 6, no EMA filter, fixed 1R | 207 | 47.34% | 1.11 | +7.08R | 8.10% | 55 | 40.00% | 0.70 | -6.19R | 7.23% |

None passed the untouched-validation rules. M15's positive full-period result
comes from the training portion and reversed during the final week. The live
EMA3 profile therefore remains on its previously selected H4 configuration.

Maximum drawdown above is realized balance drawdown; it does not claim to be a
tick-level intratrade equity drawdown.
