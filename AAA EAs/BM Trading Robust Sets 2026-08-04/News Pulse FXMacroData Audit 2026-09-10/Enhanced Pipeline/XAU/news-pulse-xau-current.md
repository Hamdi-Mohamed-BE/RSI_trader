# Calyx evidence audit — News Pulse XAU — current

**Verdict: WATCH ONLY**

This is an evidence-quality decision, not a profit guarantee.

## Observed and uncertainty metrics

| Metric | Result |
|---|---:|
| Closed trades | 20 |
| Return | +14.46% |
| Profit factor | 4.53 |
| Win rate | 45.00% |
| Win-rate 95% interval | 25.82% – 65.79% |
| Annualized Sharpe | 1.75 |
| Deflated Sharpe probability | 50.18% |
| Daily expected shortfall (95%) | 0.02% |
| Recent-half PF | 9.27 |
| Max win / loss streak | 3 / 5 |

## 10,000-path block bootstrap

| Metric | Result |
|---|---:|
| Probability profitable | 97.26% |
| Return P5 / median / P95 | +1.39% / +13.48% / +32.04% |
| PF P5 / median / P95 | 0.79 / 4.36 / 13.59 |
| Max DD median / P95 | 1.73% / 3.62% |
| Closed-P&L daily / total rule breach | 0.00% / 0.00% |

## Chronological stability

| Third | Dates | Trades | Net | PF | Win rate |
|---:|---|---:|---:|---:|---:|
| 1 | 2025-09-05 to 2025-11-20 | 7 | +240.00 | 1.14 | 28.57% |
| 2 | 2026-01-09 to 2026-03-11 | 6 | +1530.00 | 1.92 | 50.00% |
| 3 | 2026-03-18 to 2026-07-29 | 7 | +12690.00 | 17.70 | 57.14% |

## Gates

- FAIL — minimum 30 closed trades
- PASS — positive locked return
- PASS — profit factor above 1
- PASS — bootstrap return p05 positive
- FAIL — bootstrap pf p05 above 1
- FAIL — deflated sharpe 95pct
- PASS — recent half pf above 1
- PASS — two of three subperiods profitable
- PASS — closed pnl total breach below 5pct
- FAIL — cost stress supplied
- FAIL — cost stress pf above 1

The prop-rule probabilities use closed trades only. Final promotion still requires MT5 equity-path/floating-drawdown evidence and a broker-specific cost-stress value.
