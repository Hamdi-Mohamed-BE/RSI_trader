# Calyx evidence audit — DMC H4 Fresh Ladder US100 transfer 3Y

**Verdict: REJECT**

This is an evidence-quality decision, not a profit guarantee.

## Observed and uncertainty metrics

| Metric | Result |
|---|---:|
| Closed trades | 1524 |
| Return | -99.16% |
| Profit factor | 0.49 |
| Win rate | 30.91% |
| Win-rate 95% interval | 28.64% – 33.27% |
| Annualized Sharpe | -4.50 |
| Deflated Sharpe probability | 0.00% |
| Daily expected shortfall (95%) | 3.14% |
| Recent-half PF | 0.65 |
| Max win / loss streak | 5 / 21 |

## 10,000-path block bootstrap

| Metric | Result |
|---|---:|
| Probability profitable | 0.00% |
| Return P5 / median / P95 | -99.66% / -99.16% / -97.85% |
| PF P5 / median / P95 | 0.41 / 0.49 / 0.58 |
| Max DD median / P95 | 99.20% / 99.68% |
| Closed-P&L daily / total rule breach | 86.28% / 100.00% |

## Chronological stability

| Third | Dates | Trades | Net | PF | Win rate |
|---:|---|---:|---:|---:|---:|
| 1 | 2023-09-01 to 2024-08-07 | 508 | -8554.89 | 0.45 | 32.28% |
| 2 | 2024-08-07 to 2025-07-02 | 508 | -1042.52 | 0.64 | 33.46% |
| 3 | 2025-07-03 to 2026-08-31 | 508 | -318.99 | 0.60 | 26.97% |

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
