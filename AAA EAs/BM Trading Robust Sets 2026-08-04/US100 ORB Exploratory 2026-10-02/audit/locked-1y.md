# Calyx evidence audit — US100 ORB exploratory locked-1y

**Verdict: REJECT**

This is an evidence-quality decision, not a profit guarantee.

## Observed and uncertainty metrics

| Metric | Result |
|---|---:|
| Closed trades | 89 |
| Return | -1.69% |
| Profit factor | 0.96 |
| Win rate | 49.44% |
| Win-rate 95% interval | 39.29% – 59.63% |
| Annualized Sharpe | -0.12 |
| Deflated Sharpe probability | 1.58% |
| Daily expected shortfall (95%) | 1.12% |
| Recent-half PF | 0.80 |
| Max win / loss streak | 4 / 7 |

## 10,000-path block bootstrap

| Metric | Result |
|---|---:|
| Probability profitable | 41.57% |
| Return P5 / median / P95 | -17.31% / -2.28% / +18.83% |
| PF P5 / median / P95 | 0.62 / 0.95 / 1.47 |
| Max DD median / P95 | 10.87% / 20.30% |
| Closed-P&L daily / total rule breach | 0.00% / 35.36% |

## Chronological stability

| Third | Dates | Trades | Net | PF | Win rate |
|---:|---|---:|---:|---:|---:|
| 1 | 2025-10-06 to 2026-02-25 | 30 | -104.86 | 0.90 | 53.33% |
| 2 | 2026-03-04 to 2026-05-29 | 29 | +322.32 | 1.24 | 44.83% |
| 3 | 2026-06-02 to 2026-09-30 | 30 | -386.47 | 0.75 | 50.00% |

## Gates

- PASS — minimum 30 closed trades
- FAIL — positive locked return
- FAIL — profit factor above 1
- FAIL — bootstrap return p05 positive
- FAIL — bootstrap pf p05 above 1
- FAIL — deflated sharpe 95pct
- FAIL — recent half pf above 1
- FAIL — two of three subperiods profitable
- FAIL — closed pnl total breach below 5pct
- FAIL — cost stress supplied
- FAIL — cost stress pf above 1

The prop-rule probabilities use closed trades only. Final promotion still requires MT5 equity-path/floating-drawdown evidence and a broker-specific cost-stress value.
