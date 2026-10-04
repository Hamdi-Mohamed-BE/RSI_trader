# Calyx evidence audit — US100 ORB exploratory full-5y

**Verdict: WATCH ONLY**

This is an evidence-quality decision, not a profit guarantee.

## Observed and uncertainty metrics

| Metric | Result |
|---|---:|
| Closed trades | 408 |
| Return | +54.73% |
| Profit factor | 1.23 |
| Win rate | 49.26% |
| Win-rate 95% interval | 44.44% – 54.10% |
| Annualized Sharpe | 0.88 |
| Deflated Sharpe probability | 50.26% |
| Daily expected shortfall (95%) | 1.05% |
| Recent-half PF | 1.20 |
| Max win / loss streak | 6 / 7 |

## 10,000-path block bootstrap

| Metric | Result |
|---|---:|
| Probability profitable | 96.88% |
| Return P5 / median / P95 | +5.54% / +54.79% / +130.75% |
| PF P5 / median / P95 | 1.04 / 1.23 / 1.46 |
| Max DD median / P95 | 13.30% / 23.01% |
| Closed-P&L daily / total rule breach | 0.00% / 14.94% |

## Chronological stability

| Third | Dates | Trades | Net | PF | Win rate |
|---:|---|---:|---:|---:|---:|
| 1 | 2021-10-07 to 2023-06-28 | 136 | +1028.52 | 1.14 | 44.12% |
| 2 | 2023-06-30 to 2025-03-24 | 136 | +3932.31 | 1.54 | 52.21% |
| 3 | 2025-03-25 to 2026-09-30 | 136 | +512.17 | 1.06 | 51.47% |

## Gates

- PASS — minimum 30 closed trades
- PASS — positive locked return
- PASS — profit factor above 1
- PASS — bootstrap return p05 positive
- PASS — bootstrap pf p05 above 1
- FAIL — deflated sharpe 95pct
- PASS — recent half pf above 1
- PASS — two of three subperiods profitable
- FAIL — closed pnl total breach below 5pct
- FAIL — cost stress supplied
- FAIL — cost stress pf above 1

The prop-rule probabilities use closed trades only. Final promotion still requires MT5 equity-path/floating-drawdown evidence and a broker-specific cost-stress value.
