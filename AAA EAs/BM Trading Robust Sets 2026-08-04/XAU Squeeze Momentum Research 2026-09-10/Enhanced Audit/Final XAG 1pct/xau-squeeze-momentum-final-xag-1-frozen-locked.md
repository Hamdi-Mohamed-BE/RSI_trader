# Calyx evidence audit — XAU Squeeze Momentum — final XAG 1% frozen locked

**Verdict: WATCH ONLY**

This is an evidence-quality decision, not a profit guarantee.

## Observed and uncertainty metrics

| Metric | Result |
|---|---:|
| Closed trades | 11 |
| Return | +3.02% |
| Profit factor | 2.13 |
| Win rate | 54.55% |
| Win-rate 95% interval | 28.01% – 78.73% |
| Annualized Sharpe | 1.12 |
| Deflated Sharpe probability | 7.76% |
| Daily expected shortfall (95%) | 0.01% |
| Recent-half PF | 1.32 |
| Max win / loss streak | 3 / 2 |

## 10,000-path block bootstrap

| Metric | Result |
|---|---:|
| Probability profitable | 88.52% |
| Return P5 / median / P95 | -1.13% / +2.88% / +7.58% |
| PF P5 / median / P95 | 1.33 / 2.13 / 3.73 |
| Max DD median / P95 | 1.23% / 2.87% |
| Closed-P&L daily / total rule breach | 0.00% / 0.00% |

## Chronological stability

| Third | Dates | Trades | Net | PF | Win rate |
|---:|---|---:|---:|---:|---:|
| 1 | 2025-09-12 to 2025-10-09 | 4 | +257.55 | 13.36 | 75.00% |
| 2 | 2025-10-17 to 2025-11-27 | 3 | -6.52 | 0.93 | 33.33% |
| 3 | 2025-12-09 to 2026-07-29 | 4 | +50.91 | 1.33 | 50.00% |

## Gates

- FAIL — minimum 30 closed trades
- PASS — positive locked return
- PASS — profit factor above 1
- FAIL — bootstrap return p05 positive
- PASS — bootstrap pf p05 above 1
- FAIL — deflated sharpe 95pct
- PASS — recent half pf above 1
- PASS — two of three subperiods profitable
- PASS — closed pnl total breach below 5pct
- FAIL — cost stress supplied
- FAIL — cost stress pf above 1

The prop-rule probabilities use closed trades only. Final promotion still requires MT5 equity-path/floating-drawdown evidence and a broker-specific cost-stress value.
