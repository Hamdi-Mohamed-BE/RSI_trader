# Calyx evidence audit — DMC H4 Fresh Ladder XAU frozen 3Y

**Verdict: REJECT**

This is an evidence-quality decision, not a profit guarantee.

## Observed and uncertainty metrics

| Metric | Result |
|---|---:|
| Closed trades | 1711 |
| Return | -76.23% |
| Profit factor | 0.84 |
| Win rate | 40.39% |
| Win-rate 95% interval | 38.08% – 42.73% |
| Annualized Sharpe | -1.27 |
| Deflated Sharpe probability | 0.09% |
| Daily expected shortfall (95%) | 2.77% |
| Recent-half PF | 0.89 |
| Max win / loss streak | 9 / 11 |

## 10,000-path block bootstrap

| Metric | Result |
|---|---:|
| Probability profitable | 0.73% |
| Return P5 / median / P95 | -90.85% / -76.39% / -37.46% |
| PF P5 / median / P95 | 0.75 / 0.84 / 0.92 |
| Max DD median / P95 | 80.60% / 91.88% |
| Closed-P&L daily / total rule breach | 0.00% / 99.89% |

## Chronological stability

| Third | Dates | Trades | Net | PF | Win rate |
|---:|---|---:|---:|---:|---:|
| 1 | 2023-09-01 to 2024-08-29 | 570 | -5252.16 | 0.77 | 39.82% |
| 2 | 2024-08-29 to 2025-08-28 | 571 | -1627.91 | 0.88 | 42.56% |
| 3 | 2025-08-28 to 2026-08-31 | 570 | -743.43 | 0.93 | 38.77% |

## Gates

- PASS — minimum 30 closed trades
- FAIL — positive locked return
- FAIL — profit factor above 1
- FAIL — bootstrap return p05 positive
- FAIL — bootstrap pf p05 above 1
- FAIL — deflated sharpe 95pct
- FAIL — recent half pf above 1
- FAIL — two of three subperiods profitable
- FAIL — closed pnl total breach below 5pct
- FAIL — cost stress supplied
- FAIL — cost stress pf above 1

The prop-rule probabilities use closed trades only. Final promotion still requires MT5 equity-path/floating-drawdown evidence and a broker-specific cost-stress value.
