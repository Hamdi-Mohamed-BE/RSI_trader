# Calyx evidence audit — XAU Squeeze Momentum — recommended locked

**Verdict: WATCH ONLY**

This is an evidence-quality decision, not a profit guarantee.

## Observed and uncertainty metrics

| Metric | Result |
|---|---:|
| Closed trades | 21 |
| Return | +2.79% |
| Profit factor | 1.37 |
| Win rate | 42.86% |
| Win-rate 95% interval | 24.47% – 63.45% |
| Annualized Sharpe | 0.72 |
| Deflated Sharpe probability | 2.68% |
| Daily expected shortfall (95%) | 0.02% |
| Recent-half PF | 0.45 |
| Max win / loss streak | 6 / 6 |

## 10,000-path block bootstrap

| Metric | Result |
|---|---:|
| Probability profitable | 73.46% |
| Return P5 / median / P95 | -4.02% / +2.68% / +10.41% |
| PF P5 / median / P95 | 0.45 / 1.33 / 3.95 |
| Max DD median / P95 | 2.92% / 6.23% |
| Closed-P&L daily / total rule breach | 0.00% / 0.10% |

## Chronological stability

| Third | Dates | Trades | Net | PF | Win rate |
|---:|---|---:|---:|---:|---:|
| 1 | 2025-09-15 to 2025-11-13 | 7 | +570.25 | 9.96 | 85.71% |
| 2 | 2025-11-28 to 2026-03-01 | 7 | -39.83 | 0.86 | 28.57% |
| 3 | 2026-04-07 to 2026-07-22 | 7 | -251.90 | 0.38 | 14.29% |

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
