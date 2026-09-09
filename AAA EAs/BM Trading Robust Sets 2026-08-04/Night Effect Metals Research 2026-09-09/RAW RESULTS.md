# Precious-metals Night Effect - raw CFD results

Research date: 2026-09-09

## Source and replication boundary

Ma, Bouri, Xu and Zhou's 2025 *Global Finance Journal* paper reports that the first half-hour return of the Shanghai gold and silver night session predicts selected later half-hours. The public publisher preview confirms the signal and market-timing construction. The exact target intervals below come from the authors' accessible earlier full working paper because the final published tables are paywalled.

This is therefore the closest publicly auditable raw momentum replication, mapped from Beijing time to the same UTC clock on Exness XAUUSD and XAGUSD CFDs. It is not a claim that a continuous OTC CFD is economically identical to an SHFE futures contract.

## Raw rules

- Signal: direction of 21:00-21:30 Beijing, converted directly to 13:00-13:30 UTC.
- XAUUSD: trade in the signal direction during 09:00-09:30 Beijing on the next trading day, converted to 01:00-01:30 UTC.
- XAGUSD: trade in the signal direction during the paper's significant night interval 10 and day intervals 1, 5, 6 and 8: 17:30-18:00 UTC on the signal date, then 01:00-01:30, 03:00-03:30, 05:30-06:00 and 06:30-07:00 UTC on the next trading day.
- No trend, volatility, direction, day, news, spread or regime filter.
- No take-profit, trailing stop, breakeven or parameter optimization.
- Positions close at the end of each paper half-hour window.
- Dynamic 1% equity risk at a 2x H1 ATR emergency stop. A trade is skipped if the broker minimum lot would exceed 1%.
- Native MT5 Every Tick with broker spread, commission, swap and random execution delay.

## Results

| Period | Asset | Return | PF | Win rate | Max DD | Sharpe | Recovery | Trades | Quality |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 5 years | XAUUSD | -18.52% | 0.84 | 47.34% | 19.86% | -5.00 | -0.93 | 1,259 | 98% |
| 5 years | XAGUSD | -94.29% | 0.15 | 27.65% | 94.29% | -5.00 | -1.00 | 1,765 | 98% |
| 3 years | XAUUSD | -6.75% | 0.91 | 47.53% | 8.90% | -3.70 | -0.76 | 749 | 98% |
| 3 years | XAGUSD | -88.66% | 0.24 | 29.87% | 88.72% | -5.00 | -1.00 | 1,778 | 98% |
| 1 year | XAUUSD | -0.83% | 0.97 | 48.15% | 5.49% | -1.30 | -0.15 | 243 | 99% |
| 1 year | XAGUSD | -11.40% | 0.86 | 50.94% | 13.71% | -5.00 | -0.83 | 958 | 99% |

## Cost check

| Period | Asset | Net P/L | Commission | P/L before commission |
|---|---|---:|---:|---:|
| 5 years | XAUUSD | -$1,852.08 | -$496.94 | -$1,355.14 |
| 5 years | XAGUSD | -$9,429.02 | -$2,246.72 | -$7,182.30 |
| 3 years | XAUUSD | -$675.27 | -$243.92 | -$431.35 |
| 3 years | XAGUSD | -$8,866.21 | -$2,744.36 | -$6,121.85 |
| 1 year | XAUUSD | -$83.34 | -$32.91 | -$50.43 |
| 1 year | XAGUSD | -$1,139.90 | -$861.20 | -$278.70 |

Commission makes the high-turnover silver transfer worse, but it is not the reason the transfer fails: every asset-period row is already negative before commission.

## Decision

Reject both CFD transfers. XAUUSD approaches break-even in the latest year but fails every period and never reaches PF 1.0. XAGUSD is decisively unsuitable because five half-hour entries per signal create excessive turnover and the underlying pre-commission price result is also negative. No pipeline optimization, EA-store, installer, recommended portfolio or website change is justified.

Research files are retained only for audit and future reference.
