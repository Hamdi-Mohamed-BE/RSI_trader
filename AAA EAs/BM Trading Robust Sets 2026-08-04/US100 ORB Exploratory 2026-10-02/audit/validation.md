# Calyx evidence audit — US100 ORB exploratory validation

**Verdict: WATCH ONLY**

This is an evidence-quality decision, not a profit guarantee.

## Observed and uncertainty metrics

| Metric | Result |
|---|---:|
| Closed trades | 83 |
| Return | +17.90% |
| Profit factor | 1.49 |
| Win rate | 54.22% |
| Win-rate 95% interval | 43.55% – 64.51% |
| Annualized Sharpe | 1.63 |
| Deflated Sharpe probability | 38.87% |
| Daily expected shortfall (95%) | 1.01% |
| Recent-half PF | 1.31 |
| Max win / loss streak | 4 / 4 |

## 10,000-path block bootstrap

| Metric | Result |
|---|---:|
| Probability profitable | 94.82% |
| Return P5 / median / P95 | -0.13% / +17.44% / +40.83% |
| PF P5 / median / P95 | 1.02 / 1.50 / 2.12 |
| Max DD median / P95 | 5.57% / 10.44% |
| Closed-P&L daily / total rule breach | 0.00% / 1.60% |

## Chronological stability

| Third | Dates | Trades | Net | PF | Win rate |
|---:|---|---:|---:|---:|---:|
| 1 | 2024-10-08 to 2025-01-30 | 28 | +1153.90 | 1.95 | 53.57% |
| 2 | 2025-01-31 to 2025-06-17 | 27 | +432.81 | 1.39 | 55.56% |
| 3 | 2025-06-24 to 2025-09-29 | 28 | +203.14 | 1.15 | 53.57% |

## Gates

- PASS — minimum 30 closed trades
- PASS — positive locked return
- PASS — profit factor above 1
- FAIL — bootstrap return p05 positive
- PASS — bootstrap pf p05 above 1
- FAIL — deflated sharpe 95pct
- PASS — recent half pf above 1
- PASS — two of three subperiods profitable
- PASS — closed pnl total breach below 5pct
- FAIL — cost stress supplied
- FAIL — cost stress pf above 1

The prop-rule probabilities use closed trades only. Final promotion still requires MT5 equity-path/floating-drawdown evidence and a broker-specific cost-stress value.
