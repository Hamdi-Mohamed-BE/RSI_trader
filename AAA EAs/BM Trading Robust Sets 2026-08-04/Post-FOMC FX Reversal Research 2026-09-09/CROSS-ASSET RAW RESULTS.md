# Post-FOMC reversal — raw cross-asset CFD transfer

Status: **raw transfer test complete; awaiting review; no production action**

## What was tested

The untouched FX timing rule was transferred to four non-FX CFDs:

- Sell XAUUSD, XAGUSD, BTCUSD and USTEC 12 hours after each scheduled 14:00 New York FOMC statement.
- Close the position 24 hours after the statement.
- No take-profit, trailing stop, breakeven, direction filter, regime filter or parameter optimization.
- A 10x H1 ATR emergency stop is used only to size each event at 1% equity risk.
- Native MT5 Every Tick execution with Exness spread, commission, swap and random execution delay.
- Test periods: 2021-09-01 to 2026-09-01, 2023-09-01 to 2026-09-01, and 2025-09-01 to 2026-09-01.

This is exploratory research outside the original paper's currency-market scope. It tests whether the same post-FOMC USD-strength or risk-off window transfers to metals, Bitcoin and US100.

## Cross-asset summary

The return is the equal-weight average of four separately funded $10,000 tests. Pooled PF and win rate combine their trade outcomes. Because every asset trades the same FOMC window, these are highly overlapping signals; the drawdown column is the worst single-asset drawdown and is not a reconstructed portfolio drawdown.

| Period | Avg return | Pooled PF | Pooled win rate | Trades | Avg Sharpe | Avg recovery | Worst asset DD |
|---|---:|---:|---:|---:|---:|---:|---:|
| 5 years | +2.32% | 1.53 | 50.62% | 160 | 3.56 | 1.23 | 4.83% |
| 3 years | +2.04% | 1.74 | 55.21% | 96 | 3.63 | 0.99 | 4.82% |
| 1 year | +1.37% | 1.83 | 43.75% | 32 | 0.51 | 0.82 | 4.85% |

## Five-year results

| Asset | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery | Quality |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| XAUUSD | +3.85% | 1.79 | 57.50% | 2.68% | 40 | 3.74 | 1.37 | 98% |
| XAGUSD | +2.40% | 1.41 | 45.00% | 4.83% | 40 | 1.45 | 0.47 | 98% |
| BTCUSD | +2.06% | 2.02 | 57.50% | 0.85% | 40 | 6.96 | 2.37 | 100% |
| USTEC | +0.99% | 1.20 | 42.50% | 1.33% | 40 | 2.11 | 0.73 | 98% |

## Three-year results

| Asset | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery | Quality |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| XAUUSD | +3.48% | 2.12 | 66.67% | 2.69% | 24 | 4.14 | 1.24 | 98% |
| XAGUSD | +2.67% | 1.63 | 54.17% | 4.82% | 24 | 1.92 | 0.53 | 98% |
| BTCUSD | +1.18% | 1.99 | 58.33% | 0.86% | 24 | 5.76 | 1.36 | 100% |
| USTEC | +0.85% | 1.34 | 41.67% | 1.01% | 24 | 2.69 | 0.83 | 98% |

## Latest-year results

| Asset | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery | Quality |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| XAUUSD | +3.01% | 2.38 | 50.00% | 2.70% | 8 | 0.79 | 1.07 | 99% |
| XAGUSD | +2.02% | 1.67 | 37.50% | 4.85% | 8 | 0.31 | 0.40 | 99% |
| BTCUSD | +0.79% | 3.52 | 50.00% | 0.36% | 8 | 1.34 | 2.13 | 100% |
| USTEC | -0.33% | 0.70 | 37.50% | 0.99% | 8 | -0.39 | -0.33 | 100% |

## Review conclusion

The raw transfer is materially stronger than the raw FX basket. XAUUSD and BTCUSD are the cleanest candidates because both remain profitable in every window, exceed PF 1.79 over five years and retain positive latest-year results. XAGUSD is positive but has the largest drawdown and weakest latest-year win rate. USTEC fails the latest-year test.

The sample is only eight scheduled events per year and all four positions overlap in time, so these results are promising research evidence rather than production proof. Recommended review decision: retain XAUUSD and BTCUSD for a tightly controlled robustness pipeline, keep XAGUSD as a secondary comparison, and reject USTEC. Do not deploy or stack four separate 1% positions around one FOMC event.
