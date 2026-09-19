# Calyx evidence audit — XAU D14 selected 5y

**Verdict: WATCH ONLY**

This is an evidence-quality decision, not a profit guarantee.

## Observed and uncertainty metrics

| Metric | Result |
|---|---:|
| Closed trades | 115 |
| Return | +21.21% |
| Profit factor | 1.41 |
| Win rate | 59.13% |
| Win-rate 95% interval | 49.99% – 67.68% |
| Annualized Sharpe | 0.84 |
| Deflated Sharpe probability | 24.28% |
| Daily expected shortfall (95%) | 0.03% |
| Recent-half PF | 1.31 |
| Max win / loss streak | 8 / 8 |

## 10,000-path block bootstrap

| Metric | Result |
|---|---:|
| Probability profitable | 96.12% |
| Return P5 / median / P95 | +1.34% / +21.24% / +45.09% |
| PF P5 / median / P95 | 1.00 / 1.42 / 2.01 |
| Max DD median / P95 | 6.29% / 11.77% |
| Closed-P&L daily / total rule breach | 0.00% / 2.27% |

## Chronological stability

| Third | Dates | Trades | Net | PF | Win rate |
|---:|---|---:|---:|---:|---:|
| 1 | 2021-10-13 to 2023-07-11 | 38 | +500.95 | 1.30 | 57.89% |
| 2 | 2023-09-07 to 2025-03-14 | 39 | +603.12 | 1.35 | 58.97% |
| 3 | 2025-03-17 to 2026-08-24 | 38 | +1017.11 | 1.59 | 60.53% |

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
