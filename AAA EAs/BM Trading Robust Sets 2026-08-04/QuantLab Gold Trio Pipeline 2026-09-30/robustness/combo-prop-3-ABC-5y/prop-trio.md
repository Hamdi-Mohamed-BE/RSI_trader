# Calyx evidence audit — PROP trio

**Verdict: WATCH ONLY**

This is an evidence-quality decision, not a profit guarantee.

## Observed and uncertainty metrics

| Metric | Result |
|---|---:|
| Closed trades | 708 |
| Return | +96.13% |
| Profit factor | 1.29 |
| Win rate | 73.45% |
| Win-rate 95% interval | 70.07% – 76.57% |
| Annualized Sharpe | 1.37 |
| Deflated Sharpe probability | 38.43% |
| Daily expected shortfall (95%) | 1.26% |
| Recent-half PF | 1.16 |
| Max win / loss streak | 28 / 6 |

## 10,000-path block bootstrap

| Metric | Result |
|---|---:|
| Probability profitable | 99.77% |
| Return P5 / median / P95 | +32.26% / +95.17% / +191.77% |
| PF P5 / median / P95 | 1.09 / 1.29 / 1.56 |
| Max DD median / P95 | 11.78% / 19.52% |
| Closed-P&L daily / total rule breach | 0.00% / 7.07% |

## Chronological stability

| Third | Dates | Trades | Net | PF | Win rate |
|---:|---|---:|---:|---:|---:|
| 1 | 2021-09-30 to 2023-05-18 | 236 | +4690.76 | 1.75 | 78.39% |
| 2 | 2023-05-19 to 2024-12-12 | 236 | +3942.54 | 1.39 | 73.73% |
| 3 | 2024-12-18 to 2026-09-28 | 236 | +979.87 | 1.06 | 68.22% |

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
- PASS — cost stress supplied
- PASS — cost stress pf above 1

The prop-rule probabilities use closed trades only. Final promotion still requires MT5 equity-path/floating-drawdown evidence and a broker-specific cost-stress value.
