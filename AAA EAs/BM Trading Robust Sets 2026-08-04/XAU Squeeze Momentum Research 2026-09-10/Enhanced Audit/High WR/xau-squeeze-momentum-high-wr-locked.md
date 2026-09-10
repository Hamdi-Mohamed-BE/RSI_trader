# Calyx evidence audit — XAU Squeeze Momentum — high WR locked

**Verdict: WATCH ONLY**

This is an evidence-quality decision, not a profit guarantee.

## Observed and uncertainty metrics

| Metric | Result |
|---|---:|
| Closed trades | 15 |
| Return | +4.62% |
| Profit factor | 2.10 |
| Win rate | 53.33% |
| Win-rate 95% interval | 30.12% – 75.19% |
| Annualized Sharpe | 1.65 |
| Deflated Sharpe probability | 12.13% |
| Daily expected shortfall (95%) | 0.02% |
| Recent-half PF | 0.69 |
| Max win / loss streak | 6 / 3 |

## 10,000-path block bootstrap

| Metric | Result |
|---|---:|
| Probability profitable | 90.07% |
| Return P5 / median / P95 | -1.20% / +4.55% / +11.35% |
| PF P5 / median / P95 | 0.68 / 2.03 / 7.32 |
| Max DD median / P95 | 1.73% / 3.82% |
| Closed-P&L daily / total rule breach | 0.00% / 0.00% |

## Chronological stability

| Third | Dates | Trades | Net | PF | Win rate |
|---:|---|---:|---:|---:|---:|
| 1 | 2025-09-15 to 2025-10-16 | 5 | +403.90 | 7.35 | 80.00% |
| 2 | 2025-11-10 to 2026-01-28 | 5 | +194.62 | 2.78 | 60.00% |
| 3 | 2026-02-11 to 2026-04-08 | 5 | -136.68 | 0.44 | 20.00% |

## Gates

- FAIL — minimum 30 closed trades
- PASS — positive locked return
- PASS — profit factor above 1
- FAIL — bootstrap return p05 positive
- FAIL — bootstrap pf p05 above 1
- FAIL — deflated sharpe 95pct
- FAIL — recent half pf above 1
- PASS — two of three subperiods profitable
- PASS — closed pnl total breach below 5pct
- PASS — cost stress supplied
- PASS — cost stress pf above 1

The prop-rule probabilities use closed trades only. Final promotion still requires MT5 equity-path/floating-drawdown evidence and a broker-specific cost-stress value.
