# Calyx evidence audit — XAUUSD — baseline

**Verdict: WATCH ONLY**

This is an evidence-quality decision, not a profit guarantee.

## Observed and uncertainty metrics

| Metric | Result |
|---|---:|
| Closed trades | 8 |
| Return | +25.71% |
| Profit factor | 15.73 |
| Win rate | 75.00% |
| Win-rate 95% interval | 40.93% – 92.85% |
| Annualized Sharpe | 6.01 |
| Deflated Sharpe probability | 95.24% |
| Daily expected shortfall (95%) | -0.00% |
| Recent-half PF | 4.67 |
| Max win / loss streak | 4 / 1 |

## 10,000-path block bootstrap

| Metric | Result |
|---|---:|
| Probability profitable | 99.91% |
| Return P5 / median / P95 | +11.56% / +25.67% / +42.17% |
| PF P5 / median / P95 | 6.39 / 15.73 / 43.26 |
| Max DD median / P95 | 0.00% / 0.00% |
| Closed-P&L daily / total rule breach | 0.00% / 0.00% |

## Chronological stability

| Third | Dates | Trades | Net | PF | Win rate |
|---:|---|---:|---:|---:|---:|
| 1 | 2026-06-17 to 2026-07-14 | 3 | +1562.67 | inf | 100.00% |
| 2 | 2026-07-29 to 2026-08-07 | 2 | +278.52 | 4.15 | 50.00% |
| 3 | 2026-08-07 to 2026-08-12 | 3 | +729.61 | 9.47 | 66.67% |

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
