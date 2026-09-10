# Calyx evidence audit — XAUUSD — fxmacrodata_schedule

**Verdict: WATCH ONLY**

This is an evidence-quality decision, not a profit guarantee.

## Observed and uncertainty metrics

| Metric | Result |
|---|---:|
| Closed trades | 9 |
| Return | +35.32% |
| Profit factor | 21.23 |
| Win rate | 77.78% |
| Win-rate 95% interval | 45.26% – 93.68% |
| Annualized Sharpe | 5.37 |
| Deflated Sharpe probability | 98.25% |
| Daily expected shortfall (95%) | -0.00% |
| Recent-half PF | 10.18 |
| Max win / loss streak | 4 / 1 |

## 10,000-path block bootstrap

| Metric | Result |
|---|---:|
| Probability profitable | 99.97% |
| Return P5 / median / P95 | +14.14% / +34.38% / +63.24% |
| PF P5 / median / P95 | 7.32 / 21.23 / inf |
| Max DD median / P95 | 0.00% / 0.00% |
| Closed-P&L daily / total rule breach | 0.00% / 0.00% |

## Chronological stability

| Third | Dates | Trades | Net | PF | Win rate |
|---:|---|---:|---:|---:|---:|
| 1 | 2026-06-17 to 2026-07-14 | 3 | +1562.67 | inf | 100.00% |
| 2 | 2026-07-29 to 2026-08-07 | 3 | +842.23 | 10.52 | 66.67% |
| 3 | 2026-08-12 to 2026-09-04 | 3 | +1126.81 | 14.08 | 66.67% |

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
