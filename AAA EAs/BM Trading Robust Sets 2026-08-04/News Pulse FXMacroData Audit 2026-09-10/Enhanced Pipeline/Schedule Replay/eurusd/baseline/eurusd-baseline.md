# Calyx evidence audit — EURUSD — baseline

**Verdict: WATCH ONLY**

This is an evidence-quality decision, not a profit guarantee.

## Observed and uncertainty metrics

| Metric | Result |
|---|---:|
| Closed trades | 8 |
| Return | +20.33% |
| Profit factor | 11.35 |
| Win rate | 75.00% |
| Win-rate 95% interval | 40.93% – 92.85% |
| Annualized Sharpe | 5.64 |
| Deflated Sharpe probability | 89.05% |
| Daily expected shortfall (95%) | 0.01% |
| Recent-half PF | 9.09 |
| Max win / loss streak | 3 / 1 |

## 10,000-path block bootstrap

| Metric | Result |
|---|---:|
| Probability profitable | 99.91% |
| Return P5 / median / P95 | +8.91% / +20.06% / +33.77% |
| PF P5 / median / P95 | 5.39 / 11.35 / 29.48 |
| Max DD median / P95 | 0.21% / 0.21% |
| Closed-P&L daily / total rule breach | 0.00% / 0.00% |

## Chronological stability

| Third | Dates | Trades | Net | PF | Win rate |
|---:|---|---:|---:|---:|---:|
| 1 | 2026-06-17 to 2026-07-14 | 3 | +1411.00 | inf | 100.00% |
| 2 | 2026-07-29 to 2026-07-29 | 2 | +211.58 | 2.99 | 50.00% |
| 3 | 2026-08-07 to 2026-08-12 | 3 | +410.22 | 5.56 | 66.67% |

## Gates

- FAIL — minimum 30 closed trades
- PASS — positive locked return
- PASS — profit factor above 1
- PASS — bootstrap return p05 positive
- PASS — bootstrap pf p05 above 1
- FAIL — deflated sharpe 95pct
- PASS — recent half pf above 1
- PASS — two of three subperiods profitable
- PASS — closed pnl total breach below 5pct
- FAIL — cost stress supplied
- FAIL — cost stress pf above 1

The prop-rule probabilities use closed trades only. Final promotion still requires MT5 equity-path/floating-drawdown evidence and a broker-specific cost-stress value.
