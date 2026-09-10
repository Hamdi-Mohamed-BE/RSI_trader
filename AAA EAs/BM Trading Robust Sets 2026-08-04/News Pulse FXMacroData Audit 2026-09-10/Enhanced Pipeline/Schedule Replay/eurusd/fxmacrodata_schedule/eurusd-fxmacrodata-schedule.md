# Calyx evidence audit — EURUSD — fxmacrodata_schedule

**Verdict: WATCH ONLY**

This is an evidence-quality decision, not a profit guarantee.

## Observed and uncertainty metrics

| Metric | Result |
|---|---:|
| Closed trades | 9 |
| Return | +24.90% |
| Profit factor | 13.67 |
| Win rate | 77.78% |
| Win-rate 95% interval | 45.26% – 93.68% |
| Annualized Sharpe | 5.23 |
| Deflated Sharpe probability | 95.62% |
| Daily expected shortfall (95%) | 0.00% |
| Recent-half PF | 14.17 |
| Max win / loss streak | 3 / 1 |

## 10,000-path block bootstrap

| Metric | Result |
|---|---:|
| Probability profitable | 99.86% |
| Return P5 / median / P95 | +9.32% / +24.11% / +45.30% |
| PF P5 / median / P95 | 6.42 / 13.67 / 36.70 |
| Max DD median / P95 | 0.21% / 0.42% |
| Closed-P&L daily / total rule breach | 0.00% / 0.00% |

## Chronological stability

| Third | Dates | Trades | Net | PF | Win rate |
|---:|---|---:|---:|---:|---:|
| 1 | 2026-06-17 to 2026-07-14 | 3 | +1411.00 | inf | 100.00% |
| 2 | 2026-07-29 to 2026-08-07 | 3 | +647.30 | 7.08 | 66.67% |
| 3 | 2026-08-12 to 2026-09-04 | 3 | +431.25 | 5.79 | 66.67% |

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
