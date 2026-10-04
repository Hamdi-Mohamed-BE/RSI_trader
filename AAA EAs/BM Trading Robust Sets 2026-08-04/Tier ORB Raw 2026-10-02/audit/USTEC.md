# Calyx evidence audit — USTEC raw 5y

**Verdict: WATCH ONLY**

This is an evidence-quality decision, not a profit guarantee.

## Observed and uncertainty metrics

| Metric | Result |
|---|---:|
| Closed trades | 1285 |
| Return | +63.06% |
| Profit factor | 1.06 |
| Win rate | 44.28% |
| Win-rate 95% interval | 41.59% – 47.01% |
| Annualized Sharpe | 0.59 |
| Deflated Sharpe probability | 79.51% |
| Daily expected shortfall (95%) | 1.09% |
| Recent-half PF | 1.06 |
| Max win / loss streak | 7 / 9 |

## 10,000-path block bootstrap

| Metric | Result |
|---|---:|
| Probability profitable | 87.65% |
| Return P5 / median / P95 | -18.32% / +63.49% / +238.31% |
| PF P5 / median / P95 | 0.96 / 1.06 / 1.18 |
| Max DD median / P95 | 27.99% / 47.00% |
| Closed-P&L daily / total rule breach | 0.00% / 53.06% |

## Chronological stability

| Third | Dates | Trades | Net | PF | Win rate |
|---:|---|---:|---:|---:|---:|
| 1 | 2021-10-04 to 2023-06-02 | 428 | +3891.01 | 1.14 | 45.09% |
| 2 | 2023-06-05 to 2025-01-31 | 429 | +1893.37 | 1.06 | 42.89% |
| 3 | 2025-02-03 to 2026-10-01 | 428 | +521.41 | 1.01 | 44.86% |

## Gates

- PASS — minimum 30 closed trades
- PASS — positive locked return
- PASS — profit factor above 1
- FAIL — bootstrap return p05 positive
- FAIL — bootstrap pf p05 above 1
- FAIL — deflated sharpe 95pct
- PASS — recent half pf above 1
- PASS — two of three subperiods profitable
- FAIL — closed pnl total breach below 5pct
- FAIL — cost stress supplied
- FAIL — cost stress pf above 1

The prop-rule probabilities use closed trades only. Final promotion still requires MT5 equity-path/floating-drawdown evidence and a broker-specific cost-stress value.
