# Calyx evidence audit — XAU Squeeze Momentum — final safe 1% locked

**Verdict: WATCH ONLY**

This is an evidence-quality decision, not a profit guarantee.

## Observed and uncertainty metrics

| Metric | Result |
|---|---:|
| Closed trades | 13 |
| Return | +5.24% |
| Profit factor | 2.90 |
| Win rate | 61.54% |
| Win-rate 95% interval | 35.52% – 82.29% |
| Annualized Sharpe | 2.31 |
| Deflated Sharpe probability | 24.73% |
| Daily expected shortfall (95%) | 0.02% |
| Recent-half PF | 1.11 |
| Max win / loss streak | 6 / 2 |

## 10,000-path block bootstrap

| Metric | Result |
|---|---:|
| Probability profitable | 95.95% |
| Return P5 / median / P95 | +0.25% / +5.14% / +10.85% |
| PF P5 / median / P95 | 1.03 / 2.90 / 12.31 |
| Max DD median / P95 | 1.15% / 2.53% |
| Closed-P&L daily / total rule breach | 0.00% / 0.00% |

## Chronological stability

| Third | Dates | Trades | Net | PF | Win rate |
|---:|---|---:|---:|---:|---:|
| 1 | 2025-09-15 to 2025-10-08 | 4 | +249.58 | 6.23 | 75.00% |
| 2 | 2025-10-16 to 2025-12-10 | 5 | +162.74 | 2.74 | 60.00% |
| 3 | 2026-01-28 to 2026-03-01 | 4 | +111.39 | 1.83 | 50.00% |

## Gates

- FAIL — minimum 30 closed trades
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
