# Post-FOMC FX Reversal — raw CFD results

Status: **raw test complete; awaiting review; no production action**

## Paper and tested implication

Lee and Wang's 2025 paper, *Jumps and Post-FOMC Announcement Returns in Currency Markets*, reports that the US dollar tends to appreciate after scheduled FOMC announcements, with much of the reversal occurring from 12 to 24 hours after the statement.

This study tests that public timing implication directly:

- Enter long USD 12 hours after every scheduled 14:00 New York FOMC statement.
- Exit 24 hours after the statement.
- Sell EURUSD, GBPUSD, AUDUSD and NZDUSD.
- Buy USDJPY, USDCHF and USDCAD.
- No take-profit, trailing stop, breakeven, direction filter, regime filter or parameter optimization.
- A 10x H1 ATR emergency stop is used only to size each event at 1% equity risk.
- Native MT5 Every Tick execution with broker spread, commission, swap and random execution delay.
- Scheduled dates come from the Federal Reserve's official FOMC calendars.

This is a faithful test of the paper's public timing result, but it is not a replication of the paper's proprietary signed-jump-volatility estimator.

## Cross-pair summary

The return is the equal-weight average of seven separate $10,000 CFD tests. Pooled PF and win rate combine the constituent trade outcomes. The drawdown column is the worst single-pair drawdown, not a reconstructed portfolio drawdown.

| Period | Dates | Avg return | Pooled PF | Pooled win rate | Trades | Avg Sharpe | Avg recovery | Worst pair DD |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 5 years | 2021-09-01 to 2026-09-01 | +0.12% | 1.02 | 50.71% | 280 | 0.09 | 0.14 | 2.68% |
| 3 years | 2023-09-01 to 2026-09-01 | -0.38% | 0.90 | 48.21% | 168 | -1.14 | -0.17 | 2.53% |
| 1 year | 2025-09-01 to 2026-09-01 | -1.46% | 0.35 | 46.43% | 56 | -1.53 | -0.71 | 2.55% |

## Five-year results

| Pair | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| EURUSD | +0.64% | 1.10 | 55.00% | 1.97% | 40 | 1.18 | 0.32 |
| GBPUSD | +3.16% | 1.50 | 57.50% | 1.96% | 40 | 5.08 | 1.53 |
| AUDUSD | +1.22% | 1.28 | 52.50% | 1.59% | 40 | 3.03 | 0.74 |
| NZDUSD | -0.06% | 0.99 | 47.50% | 1.53% | 40 | -0.14 | -0.04 |
| USDJPY | -1.84% | 0.72 | 42.50% | 2.55% | 40 | -3.98 | -0.72 |
| USDCHF | -0.49% | 0.93 | 55.00% | 2.33% | 40 | -0.77 | -0.21 |
| USDCAD | -1.79% | 0.71 | 45.00% | 2.68% | 40 | -3.79 | -0.66 |

## Three-year results

| Pair | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| EURUSD | -0.10% | 0.97 | 50.00% | 1.89% | 24 | -0.31 | -0.05 |
| GBPUSD | +0.54% | 1.13 | 58.33% | 1.99% | 24 | 1.48 | 0.26 |
| AUDUSD | +0.31% | 1.12 | 50.00% | 1.61% | 24 | 1.16 | 0.19 |
| NZDUSD | -0.09% | 0.97 | 41.67% | 1.53% | 24 | -0.36 | -0.06 |
| USDJPY | -0.98% | 0.75 | 45.83% | 2.53% | 24 | -3.38 | -0.38 |
| USDCHF | -0.67% | 0.85 | 54.17% | 2.34% | 24 | -1.57 | -0.28 |
| USDCAD | -1.69% | 0.61 | 37.50% | 1.92% | 24 | -5.00 | -0.88 |

## Latest-year results

| Pair | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| EURUSD | -1.42% | 0.35 | 50.00% | 1.92% | 8 | -1.54 | -0.73 |
| GBPUSD | -1.57% | 0.37 | 50.00% | 2.10% | 8 | -1.63 | -0.75 |
| AUDUSD | -1.06% | 0.36 | 50.00% | 1.63% | 8 | -1.23 | -0.65 |
| NZDUSD | -0.90% | 0.47 | 50.00% | 1.54% | 8 | -1.15 | -0.58 |
| USDJPY | -2.03% | 0.34 | 37.50% | 2.55% | 8 | -1.94 | -0.79 |
| USDCHF | -1.91% | 0.29 | 50.00% | 2.43% | 8 | -1.92 | -0.78 |
| USDCAD | -1.31% | 0.30 | 37.50% | 1.92% | 8 | -1.27 | -0.68 |

## Review conclusion

The raw post-FOMC effect does **not** pass the Calyx production standard. GBPUSD is the only notable five-year result, but its PF drops from 1.50 over five years to 1.13 over three years and 0.37 in the latest year. Every pair lost money in the latest year. This is evidence of weak or decaying transfer after CFD costs, not a stable deployable edge.

Recommended decision for review: **do not add the raw strategy to the system**. If retained for further research, restrict the next stage to a small, predeclared GBPUSD/AUDUSD robustness experiment using the paper's jump-volatility condition; do not run a broad parameter search.
