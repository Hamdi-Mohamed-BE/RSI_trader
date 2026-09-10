# Calyx evidence audit — XAGUSD — baseline

**Verdict: WATCH ONLY**

This is an evidence-quality decision, not a profit guarantee.

## Observed and uncertainty metrics

| Metric | Result |
|---|---:|
| Closed trades | 8 |
| Return | +66.39% |
| Profit factor | 46.76 |
| Win rate | 75.00% |
| Win-rate 95% interval | 40.93% – 92.85% |
| Annualized Sharpe | 6.13 |
| Deflated Sharpe probability | 95.53% |
| Daily expected shortfall (95%) | -0.00% |
| Recent-half PF | 13.34 |
| Max win / loss streak | 4 / 1 |

## 10,000-path block bootstrap

| Metric | Result |
|---|---:|
| Probability profitable | 99.91% |
| Return P5 / median / P95 | +27.27% / +65.88% / +121.07% |
| PF P5 / median / P95 | 17.81 / 46.76 / 982.28 |
| Max DD median / P95 | 0.00% / 0.00% |
| Closed-P&L daily / total rule breach | 0.00% / 0.00% |

## Chronological stability

| Third | Dates | Trades | Net | PF | Win rate |
|---:|---|---:|---:|---:|---:|
| 1 | 2026-06-17 to 2026-07-14 | 3 | +3917.32 | inf | 100.00% |
| 2 | 2026-07-29 to 2026-08-07 | 2 | +795.09 | 6.83 | 50.00% |
| 3 | 2026-08-07 to 2026-08-12 | 3 | +1926.49 | 222.18 | 66.67% |

## Gates

- FAIL — minimum 30 closed trades
- PASS — positive locked return
- PASS — profit factor above 1
- PASS — bootstrap return p05 positive
- PASS — bootstrap pf p05 above 1
- PASS — deflated sharpe 95pct
- PASS — recent half pf above 1
- PASS — two of three subperiods profitable
- PASS — closed pnl total breach below 5pct
- FAIL — cost stress supplied
- FAIL — cost stress pf above 1

The prop-rule probabilities use closed trades only. Final promotion still requires MT5 equity-path/floating-drawdown evidence and a broker-specific cost-stress value.
