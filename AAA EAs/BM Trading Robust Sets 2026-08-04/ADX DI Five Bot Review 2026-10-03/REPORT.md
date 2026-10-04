# Five-EA ADX / DI comparison

Native filter-only exploratory screen: 2 Oct 2025–1 Oct 2026. $10,000, 1% equity-risk target; separate runs, not a portfolio. 150 ms delay, broker costs. No live changes.

Both XAUUSD and USDJPY report 75% real ticks, with real tick history beginning 1 Jan 2026; older part is generated. Same-year selection is not untouched validation.

## XAU Trend Progression

Frozen screen selection: **Unchanged**. Highest filtered PF: DI only. This is descriptive only.

| Variant | Return | PF | Win rate | Equity DD | Trades | / month | / weekday | Sharpe¹ | W / L streak | Gate rejects | Trade Δ |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Unchanged | 4.36% | 1.240 | 71.1% | 5.23% | 38 | 3.17 | 0.146 | 0.63 | 9 / 3 | 0 | +0 |
| DI only | 5.62% | 1.424 | 75.9% | 4.72% | 29 | 2.42 | 0.111 | 0.86 | 10 / 2 | 10 | -9 |
| ADX >=20 | 1.31% | 1.072 | 67.6% | 6.14% | 34 | 2.84 | 0.130 | 0.22 | 7 / 3 | 6 | -4 |
| ADX >=25 | 1.12% | 1.078 | 67.9% | 5.13% | 28 | 2.33 | 0.107 | 0.21 | 7 / 3 | 14 | -10 |
| ADX >=20 + DI | 2.40% | 1.181 | 72.0% | 5.85% | 25 | 2.08 | 0.096 | 0.39 | 8 / 3 | 15 | -13 |
| ADX >=25 + DI | 2.46% | 1.228 | 72.7% | 4.81% | 22 | 1.83 | 0.084 | 0.44 | 7 / 2 | 20 | -16 |

Highest-PF filter exclusions: fewer than 30 trades.

## EMA3 Gold

Frozen screen selection: **ADX >=25**. Highest filtered PF: ADX >=25. This is descriptive only.

| Variant | Return | PF | Win rate | Equity DD | Trades | / month | / weekday | Sharpe¹ | W / L streak | Gate rejects | Trade Δ |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Unchanged | 23.20% | 1.745 | 63.6% | 7.01% | 44 | 3.67 | 0.169 | 1.71 | 7 / 3 | 0 | +0 |
| DI only | 24.85% | 1.798 | 63.6% | 7.01% | 44 | 3.67 | 0.169 | 1.79 | 7 / 3 | 1 | +0 |
| ADX >=20 | 24.89% | 1.832 | 65.9% | 6.91% | 44 | 3.67 | 0.169 | 1.85 | 11 / 3 | 4 | +0 |
| ADX >=25 | 27.33% | 1.966 | 69.0% | 6.85% | 42 | 3.50 | 0.161 | 2.01 | 10 / 2 | 12 | -2 |
| ADX >=20 + DI | 26.54% | 1.887 | 65.9% | 6.91% | 44 | 3.67 | 0.169 | 1.93 | 11 / 3 | 5 | +0 |
| ADX >=25 + DI | 25.13% | 1.870 | 69.0% | 7.35% | 42 | 3.50 | 0.161 | 1.87 | 10 / 2 | 15 | -2 |

Highest-PF filter exclusions: none under descriptive criteria.

## Asia Breakout Gold

Frozen screen selection: **DI only**. Highest filtered PF: ADX >=20 + DI. This is descriptive only.

| Variant | Return | PF | Win rate | Equity DD | Trades | / month | / weekday | Sharpe¹ | W / L streak | Gate rejects | Trade Δ |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Unchanged | 14.60% | 1.280 | 40.3% | 7.44% | 67 | 5.59 | 0.257 | 1.00 | 5 / 6 | 0 | +0 |
| DI only | 18.09% | 1.368 | 41.5% | 7.44% | 65 | 5.42 | 0.249 | 1.21 | 5 / 6 | 3 | -2 |
| ADX >=20 | 14.78% | 1.318 | 40.0% | 8.72% | 60 | 5.00 | 0.230 | 1.03 | 4 / 6 | 10 | -7 |
| ADX >=25 | 11.11% | 1.293 | 37.5% | 9.77% | 48 | 4.00 | 0.184 | 0.86 | 3 / 6 | 27 | -19 |
| ADX >=20 + DI | 16.50% | 1.369 | 40.7% | 8.72% | 59 | 4.92 | 0.226 | 1.14 | 4 / 6 | 12 | -8 |
| ADX >=25 + DI | 11.11% | 1.293 | 37.5% | 9.77% | 48 | 4.00 | 0.184 | 0.86 | 3 / 6 | 27 | -19 |

Highest-PF filter exclusions: equity DD worse than baseline.

## USDJPY London Momentum

Frozen screen selection: **ADX >=20 + DI**. Highest filtered PF: ADX >=20 + DI. This is descriptive only.

| Variant | Return | PF | Win rate | Equity DD | Trades | / month | / weekday | Sharpe¹ | W / L streak | Gate rejects | Trade Δ |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Unchanged | 11.65% | 1.287 | 43.4% | 7.71% | 136 | 11.34 | 0.521 | 1.05 | 8 / 13 | 0 | +0 |
| DI only | 14.11% | 1.457 | 41.6% | 5.99% | 101 | 8.42 | 0.387 | 1.31 | 6 / 7 | 35 | -35 |
| ADX >=20 | 20.63% | 1.644 | 47.4% | 5.64% | 114 | 9.51 | 0.437 | 1.81 | 8 / 10 | 22 | -22 |
| ADX >=25 | 16.24% | 1.666 | 48.2% | 3.89% | 83 | 6.92 | 0.318 | 1.56 | 9 / 6 | 53 | -53 |
| ADX >=20 + DI | 21.95% | 1.947 | 45.8% | 4.57% | 83 | 6.92 | 0.318 | 2.01 | 6 / 5 | 53 | -53 |
| ADX >=25 + DI | 16.88% | 1.907 | 46.0% | 3.35% | 63 | 5.25 | 0.241 | 1.70 | 8 / 4 | 73 | -73 |

Highest-PF filter exclusions: none under descriptive criteria.

## XAU RSI VWAP

Frozen screen selection: **Unchanged**. Highest filtered PF: ADX <=20. This is descriptive only.

| Variant | Return | PF | Win rate | Equity DD | Trades | / month | / weekday | Sharpe¹ | W / L streak | Gate rejects | Trade Δ |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Unchanged | 3.98% | 1.210 | 71.4% | 5.36% | 49 | 4.09 | 0.188 | 0.65 | 7 / 3 | 0 | +0 |
| DI only | -1.19% | 0.931 | 65.8% | 5.50% | 38 | 3.17 | 0.146 | -0.17 | 7 / 2 | 13 | -11 |
| ADX <=20 | 0.65% | 1.617 | 75.0% | 1.05% | 4 | 0.33 | 0.015 | 0.46 | 2 / 1 | 50 | -45 |
| ADX <=25 | 2.73% | 1.502 | 75.0% | 2.98% | 16 | 1.33 | 0.061 | 0.76 | 4 / 1 | 38 | -33 |
| ADX <=20 + DI | 0.65% | 1.617 | 75.0% | 1.05% | 4 | 0.33 | 0.015 | 0.46 | 2 / 1 | 50 | -45 |
| ADX <=25 + DI | 0.99% | 1.181 | 71.4% | 3.00% | 14 | 1.17 | 0.054 | 0.30 | 3 / 1 | 40 | -35 |

Highest-PF filter exclusions: fewer than 30 trades; retains less than half the baseline trade count; return below baseline.

## Interpretation

Thirty searched settings, five original controls. Every trial is shown. No untouched out-of-sample test, no claim of proven edge or full-pipeline completion. Do not deploy these research binaries: they refuse non-tester initialization.

¹ Sharpe: annualized calendar-day closed-balance returns, including zero days, zero risk-free rate; not native trade-level Sharpe and not floating-equity Sharpe.

Equity DD is native MT5 peak-to-trough relative drawdown. PF and win rate use net trade P&L including commission and swap. Gates rejected count candidate attempts on each resulting exposure path; trade Δ is the actual trade-count change, not a one-for-one filtered baseline subset. Upward/minimum lot rounding can exceed the 1% target.

Selection criteria: >=30 trades, >=half baseline count, PF>=1.20 and >=baseline+0.05, positive net, return>=baseline, equity DD<=baseline. Otherwise retain BASE. Win streaks and higher win rate alone are not sufficient.

Verified 1822 ledger trades and 1488 entry fills. Original files unchanged.

## Conditional block-bootstrap uncertainty

10,000 circular paths, five-trade blocks; historical net cash amounts. Not search-adjusted, not an untouched test, not prospective dynamic sizing. These intervals do not establish an improvement over baseline. Fewer than 20 trades: no meaningful interval reported.

| Candidate | PF p05 | PF p95 | Net cash p05 |
|---|---:|---:|---:|
| XAU Trend Progression · Unchanged | 0.701 | 2.602 | $-792.24 |
| EMA3 Gold · ADX >=25 | 1.146 | 3.832 | $571.95 |
| Asia Breakout Gold · DI only | 0.919 | 2.021 | $-468.04 |
| USDJPY London Momentum · ADX >=20 + DI | 1.103 | 3.447 | $291.04 |
| XAU RSI VWAP · Unchanged | 0.804 | 1.925 | $-489.27 |