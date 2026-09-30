# Calyx evidence audit — BEST trio

**Verdict: WATCH ONLY**

This is an evidence-quality decision, not a profit guarantee.

## Observed and uncertainty metrics

| Metric | Result |
|---|---:|
| Closed trades | 616 |
| Return | +114.35% |
| Profit factor | 1.44 |
| Win rate | 73.05% |
| Win-rate 95% interval | 69.41% – 76.40% |
| Annualized Sharpe | 1.62 |
| Deflated Sharpe probability | 62.95% |
| Daily expected shortfall (95%) | 1.23% |
| Recent-half PF | 1.27 |
| Max win / loss streak | 26 / 6 |

## 10,000-path block bootstrap

| Metric | Result |
|---|---:|
| Probability profitable | 99.94% |
| Return P5 / median / P95 | +47.61% / +113.22% / +212.15% |
| PF P5 / median / P95 | 1.20 / 1.44 / 1.75 |
| Max DD median / P95 | 9.76% / 16.23% |
| Closed-P&L daily / total rule breach | 0.00% / 2.99% |

## Chronological stability

| Third | Dates | Trades | Net | PF | Win rate |
|---:|---|---:|---:|---:|---:|
| 1 | 2021-09-30 to 2023-06-01 | 205 | +3448.27 | 1.62 | 74.15% |
| 2 | 2023-06-02 to 2024-12-18 | 206 | +4932.98 | 1.63 | 75.24% |
| 3 | 2024-12-19 to 2026-09-28 | 205 | +3053.89 | 1.24 | 69.76% |

## Gates

- PASS — minimum 30 closed trades
- PASS — positive locked return
- PASS — profit factor above 1
- PASS — bootstrap return p05 positive
- PASS — bootstrap pf p05 above 1
- FAIL — deflated sharpe 95pct
- PASS — recent half pf above 1
- PASS — two of three subperiods profitable
- PASS — closed pnl total breach below 5pct
- PASS — cost stress supplied
- PASS — cost stress pf above 1

The prop-rule probabilities use closed trades only. Final promotion still requires MT5 equity-path/floating-drawdown evidence and a broker-specific cost-stress value.
