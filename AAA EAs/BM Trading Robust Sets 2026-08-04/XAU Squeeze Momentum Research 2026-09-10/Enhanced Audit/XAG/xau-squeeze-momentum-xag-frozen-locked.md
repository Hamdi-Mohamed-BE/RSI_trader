# Calyx evidence audit — XAU Squeeze Momentum — XAG frozen locked

**Verdict: REJECT**

This is an evidence-quality decision, not a profit guarantee.

## Observed and uncertainty metrics

| Metric | Result |
|---|---:|
| Closed trades | 0 |
| Return | +0.00% |
| Profit factor | 0.00 |
| Win rate | 0.00% |
| Win-rate 95% interval | 0.00% – 0.00% |
| Annualized Sharpe | 0.00 |
| Deflated Sharpe probability | 0.00% |
| Daily expected shortfall (95%) | 0.00% |
| Recent-half PF | 0.00 |
| Max win / loss streak | 0 / 0 |

## 10,000-path block bootstrap

| Metric | Result |
|---|---:|
| Probability profitable | 0.00% |
| Return P5 / median / P95 | +0.00% / +0.00% / +0.00% |
| PF P5 / median / P95 | 0.00 / 0.00 / 0.00 |
| Max DD median / P95 | 0.00% / 0.00% |
| Closed-P&L daily / total rule breach | 0.00% / 0.00% |

## Chronological stability

| Third | Dates | Trades | Net | PF | Win rate |
|---:|---|---:|---:|---:|---:|

## Gates

- FAIL — minimum 30 closed trades
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
