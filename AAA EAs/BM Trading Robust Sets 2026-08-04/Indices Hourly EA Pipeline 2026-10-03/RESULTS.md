# Hourly EA pipeline — 2026-10-03

Research only. Fixed one-lot index CFDs, no SL; no live deployment.

| Asset | Period | Trades | PF | Win rate | Return | Native equity DD |
|---|---|---:|---:|---:|---:|---:|
| US30 | 1y | 1229 | 1.333 | 53.38% | +74.51% | 9.53% |
| US100 | 1y | 1171 | 1.301 | 54.91% | +62.05% | 8.29% |
| SP500 | 1y | 206 | 1.423 | 50.97% | +1.70% | 0.70% |
| US30 | 3m | 315 | 1.297 | 51.75% | +15.43% | 6.56% |
| US100 | 3m | 300 | 1.070 | 51.67% | +4.32% | 6.51% |
| SP500 | 3m | 53 | 0.890 | 45.28% | -0.14% | 0.47% |
| US30 | 3y | 1262 | 0.556 | 38.03% | -99.79% | 99.92% |
| US100 | 3y | 3515 | 1.038 | 47.85% | +21.08% | 61.81% |
| SP500 | 3y | 621 | 0.796 | 40.58% | -2.54% | 4.64% |
| US30 | 5y | 1542 | 0.765 | 42.54% | -100.21% | 100.21% |
| US100 | 5y | 2423 | 0.736 | 43.17% | -100.04% | 100.06% |
| SP500 | 5y | 1031 | 0.678 | 36.66% | -7.28% | 9.79% |
| US30 | real2026 | 934 | 1.341 | 53.32% | +60.85% | 10.48% |
| US100 | real2026 | 888 | 1.399 | 56.31% | +64.54% | 5.27% |
| SP500 | real2026 | 157 | 1.523 | 54.14% | +1.61% | 0.48% |

All three fail the long-window raw gate. Year and quarter were used for selection; not untouched holdout. US30/US100 5-year $10k accounts stopped out early. Full-period hour breakdown uses separate $1m execution diagnostics. Earlier ticks are generated; real ticks start 2026-01-01. Historical broker-session definitions may differ from actual historical availability. MC is conditional resampling, not a forecast.

See Results.html, DECISIONS.json, MONTE-CARLO.json, native reports and reconciliation hashes.
