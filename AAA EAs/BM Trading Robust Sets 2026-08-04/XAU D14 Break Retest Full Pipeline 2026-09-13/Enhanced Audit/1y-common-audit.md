# Calyx evidence audit — XAU D14 selected 1y

**Verdict: WATCH ONLY**

This is an evidence-quality decision, not a profit guarantee.

## Observed and uncertainty metrics

| Metric | Result |
|---|---:|
| Closed trades | 30 |
| Return | +3.68% |
| Profit factor | 1.27 |
| Win rate | 53.33% |
| Win-rate 95% interval | 36.14% – 69.77% |
| Annualized Sharpe | 0.64 |
| Deflated Sharpe probability | 2.62% |
| Daily expected shortfall (95%) | 1.03% |
| Recent-half PF | 1.24 |
| Max win / loss streak | 6 / 8 |

## 10,000-path block bootstrap

| Metric | Result |
|---|---:|
| Probability profitable | 70.17% |
| Return P5 / median / P95 | -6.46% / +3.44% / +15.39% |
| PF P5 / median / P95 | 0.51 / 1.28 / 3.22 |
| Max DD median / P95 | 4.77% / 9.91% |
| Closed-P&L daily / total rule breach | 0.00% / 2.28% |

## Chronological stability

| Third | Dates | Trades | Net | PF | Win rate |
|---:|---|---:|---:|---:|---:|
| 1 | 2025-09-05 to 2025-10-20 | 10 | +15.58 | 1.03 | 50.00% |
| 2 | 2025-10-23 to 2026-03-03 | 10 | -348.03 | 0.48 | 30.00% |
| 3 | 2026-04-09 to 2026-08-24 | 10 | +699.96 | 4.86 | 80.00% |

## Gates

- PASS — minimum 30 closed trades
- PASS — positive locked return
- PASS — profit factor above 1
- FAIL — bootstrap return p05 positive
- FAIL — bootstrap pf p05 above 1
- FAIL — deflated sharpe 95pct
- PASS — recent half pf above 1
- PASS — two of three subperiods profitable
- PASS — closed pnl total breach below 5pct
- PASS — cost stress supplied
- PASS — cost stress pf above 1

The prop-rule probabilities use closed trades only. Final promotion still requires MT5 equity-path/floating-drawdown evidence and a broker-specific cost-stress value.
