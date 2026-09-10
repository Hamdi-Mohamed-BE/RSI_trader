# Calyx evidence audit — News Pulse EURUSD — current

**Verdict: WATCH ONLY**

This is an evidence-quality decision, not a profit guarantee.

## Observed and uncertainty metrics

| Metric | Result |
|---|---:|
| Closed trades | 35 |
| Return | +55.31% |
| Profit factor | 8.97 |
| Win rate | 68.57% |
| Win-rate 95% interval | 52.02% – 81.45% |
| Annualized Sharpe | 3.52 |
| Deflated Sharpe probability | 100.00% |
| Daily expected shortfall (95%) | 0.01% |
| Recent-half PF | 7.32 |
| Max win / loss streak | 7 / 3 |

## 10,000-path block bootstrap

| Metric | Result |
|---|---:|
| Probability profitable | 100.00% |
| Return P5 / median / P95 | +28.92% / +54.59% / +90.88% |
| PF P5 / median / P95 | 4.62 / 9.01 / 18.84 |
| Max DD median / P95 | 0.80% / 1.60% |
| Closed-P&L daily / total rule breach | 0.00% / 0.00% |

## Chronological stability

| Third | Dates | Trades | Net | PF | Win rate |
|---:|---|---:|---:|---:|---:|
| 1 | 2025-08-12 to 2025-12-16 | 12 | +1569.12 | 9.25 | 83.33% |
| 2 | 2025-12-18 to 2026-04-10 | 11 | +1347.39 | 22.51 | 63.64% |
| 3 | 2026-04-29 to 2026-08-12 | 12 | +2614.73 | 6.92 | 58.33% |

## Gates

- PASS — minimum 30 closed trades
- PASS — positive locked return
- PASS — profit factor above 1
- PASS — bootstrap return p05 positive
- PASS — bootstrap pf p05 above 1
- PASS — deflated sharpe 95pct
- PASS — recent half pf above 1
- PASS — two of three subperiods profitable
- PASS — closed pnl total breach below 5pct
- FAIL — cost stress supplied
- FAIL — cost stress pf above 1

The prop-rule probabilities use closed trades only. Final promotion still requires MT5 equity-path/floating-drawdown evidence and a broker-specific cost-stress value.
