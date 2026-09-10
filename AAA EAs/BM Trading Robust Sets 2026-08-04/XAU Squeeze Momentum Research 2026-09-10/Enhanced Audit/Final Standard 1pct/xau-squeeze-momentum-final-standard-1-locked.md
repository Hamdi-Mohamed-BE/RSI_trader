# Calyx evidence audit — XAU Squeeze Momentum — final standard 1% locked

**Verdict: WATCH ONLY**

This is an evidence-quality decision, not a profit guarantee.

## Observed and uncertainty metrics

| Metric | Result |
|---|---:|
| Closed trades | 18 |
| Return | +3.87% |
| Profit factor | 1.79 |
| Win rate | 50.00% |
| Win-rate 95% interval | 29.03% – 70.97% |
| Annualized Sharpe | 1.16 |
| Deflated Sharpe probability | 7.47% |
| Daily expected shortfall (95%) | 0.02% |
| Recent-half PF | 0.93 |
| Max win / loss streak | 6 / 4 |

## 10,000-path block bootstrap

| Metric | Result |
|---|---:|
| Probability profitable | 86.42% |
| Return P5 / median / P95 | -1.80% / +3.81% / +10.14% |
| PF P5 / median / P95 | 0.64 / 1.71 / 5.45 |
| Max DD median / P95 | 1.90% / 4.16% |
| Closed-P&L daily / total rule breach | 0.00% / 0.00% |

## Chronological stability

| Third | Dates | Trades | Net | PF | Win rate |
|---:|---|---:|---:|---:|---:|
| 1 | 2025-09-15 to 2025-11-10 | 6 | +499.64 | 11.47 | 83.33% |
| 2 | 2025-11-13 to 2026-02-20 | 6 | -84.29 | 0.63 | 33.33% |
| 3 | 2026-03-01 to 2026-07-22 | 6 | -28.47 | 0.87 | 33.33% |

## Gates

- FAIL — minimum 30 closed trades
- PASS — positive locked return
- PASS — profit factor above 1
- FAIL — bootstrap return p05 positive
- FAIL — bootstrap pf p05 above 1
- FAIL — deflated sharpe 95pct
- FAIL — recent half pf above 1
- FAIL — two of three subperiods profitable
- PASS — closed pnl total breach below 5pct
- PASS — cost stress supplied
- PASS — cost stress pf above 1

The prop-rule probabilities use closed trades only. Final promotion still requires MT5 equity-path/floating-drawdown evidence and a broker-specific cost-stress value.
