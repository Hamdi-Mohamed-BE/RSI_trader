# Calyx evidence audit — US100 ORB exploratory full-3y

**Verdict: WATCH ONLY**

This is an evidence-quality decision, not a profit guarantee.

## Observed and uncertainty metrics

| Metric | Result |
|---|---:|
| Closed trades | 255 |
| Return | +40.97% |
| Profit factor | 1.29 |
| Win rate | 52.94% |
| Win-rate 95% interval | 46.82% – 58.98% |
| Annualized Sharpe | 1.14 |
| Deflated Sharpe probability | 51.40% |
| Daily expected shortfall (95%) | 1.05% |
| Recent-half PF | 1.04 |
| Max win / loss streak | 4 / 7 |

## 10,000-path block bootstrap

| Metric | Result |
|---|---:|
| Probability profitable | 96.64% |
| Return P5 / median / P95 | +3.15% / +40.17% / +94.48% |
| PF P5 / median / P95 | 1.03 / 1.29 / 1.61 |
| Max DD median / P95 | 10.42% / 18.58% |
| Closed-P&L daily / total rule breach | 0.00% / 9.50% |

## Chronological stability

| Third | Dates | Trades | Net | PF | Win rate |
|---:|---|---:|---:|---:|---:|
| 1 | 2023-10-02 to 2024-10-09 | 85 | +2817.99 | 1.74 | 56.47% |
| 2 | 2024-10-11 to 2025-10-22 | 85 | +1330.04 | 1.28 | 51.76% |
| 3 | 2025-10-24 to 2026-09-30 | 85 | -51.06 | 0.99 | 50.59% |

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
