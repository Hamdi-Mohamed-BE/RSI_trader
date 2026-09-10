# Calyx evidence audit — News Pulse XAG — current

**Verdict: WATCH ONLY**

This is an evidence-quality decision, not a profit guarantee.

## Observed and uncertainty metrics

| Metric | Result |
|---|---:|
| Closed trades | 19 |
| Return | +90.95% |
| Profit factor | 32.91 |
| Win rate | 73.68% |
| Win-rate 95% interval | 51.21% – 88.19% |
| Annualized Sharpe | 2.55 |
| Deflated Sharpe probability | 99.90% |
| Daily expected shortfall (95%) | 0.01% |
| Recent-half PF | 46.44 |
| Max win / loss streak | 7 / 2 |

## 10,000-path block bootstrap

| Metric | Result |
|---|---:|
| Probability profitable | 99.99% |
| Return P5 / median / P95 | +28.39% / +85.55% / +222.81% |
| PF P5 / median / P95 | 13.49 / 31.94 / 92.21 |
| Max DD median / P95 | 0.87% / 1.73% |
| Closed-P&L daily / total rule breach | 0.00% / 0.00% |

## Chronological stability

| Third | Dates | Trades | Net | PF | Win rate |
|---:|---|---:|---:|---:|---:|
| 1 | 2025-08-12 to 2026-01-13 | 6 | +4675.00 | 18.00 | 83.33% |
| 2 | 2026-01-28 to 2026-06-10 | 7 | +25850.00 | 55.42 | 71.43% |
| 3 | 2026-06-17 to 2026-08-12 | 6 | +14950.00 | 23.15 | 66.67% |

## Gates

- FAIL — minimum 30 closed trades
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
