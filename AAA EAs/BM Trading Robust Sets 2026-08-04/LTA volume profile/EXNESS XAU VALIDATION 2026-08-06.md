# Exness XAU validation — 2026-08-06

## Test method

- Broker/account data: Exness Technologies Ltd, `Exness-MT5Trial16`, Zero demo account
- Symbol and timeframe: `XAUUSD`, M15
- Test window: 2025-08-05 through 2026-08-04
- Initial tester deposit: USD 10,000
- Leverage: 1:2000
- MT5 model: Every tick generated from Exness M1 history, random execution delay
- History quality: 99%
- Bars/ticks in the baseline report: 23,533 / 98,282,826
- Same entry logic and RR 3.0 in every row; only risk or the 1R break-even option changed

## Results

| Risk/control | Net profit | Return | Final balance | Relative equity DD | PF | Win rate | Trades | Approx. profit/month* |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1.00% | $9,214.62 | 92.15% | $19,214.62 | 14.82% | 1.41 | 32.79% | 244 | $767.89 |
| **1.25% — selected** | **$12,518.23** | **125.18%** | **$22,518.23** | **18.30%** | **1.40** | **32.65%** | **245** | **$1,043.19** |
| 1.25% + move all stops to break-even at 1R | $9,589.70 | 95.90% | $19,589.70 | 14.42% | 1.41 | 22.84% | 289 | $799.14 |
| 2.50% | $37,375.19 | 373.75% | $47,375.19 | 35.26% | 1.36 | 32.79% | 244 | $3,114.60 |
| 5.00% stress test | $127,968.76 | 1,279.69% | $137,968.76 | 60.90% | 1.28 | 32.79% | 244 | $10,664.06 |
| 8.00% stress test | $266,423.66 | 2,664.24% | $276,423.66 | 80.20% | 1.20 | 32.79% | 244 | $22,201.97 |

\*Simple net profit divided by 12. Actual monthly returns were uneven and compounding makes this figure non-predictive.

## Decision

The selected Exness setting is **1.25% risk per trade without the move-all-to-break-even option**. It is the only tested setting that combines the requested 15–20% historical drawdown band with approximately $1,000 per month on the $10,000 tester deposit.

The 5% and 8% settings are rejected. Their relative equity drawdowns were 60.90% and 80.20%, and their profit factors deteriorated as risk increased. They were tested only after temporarily increasing the code ceiling; the installed and packaged EA was restored to its 2.5% hard ceiling afterward.

This is a historical simulation, not a live drawdown guarantee. Gaps, slippage, spread changes, commissions, execution differences, simultaneous portfolio exposure, and future market behavior can exceed the report. A true account-level cap should use an external equity guard that blocks new entries before the limit and closes exposure at an emergency threshold; a trailing stop alone did not provide the best result here.

## Saved files

- Selected preset: `Best Settings\XAUUSD M15 - EXNESS PASS - 1.25pct - DD18.30.set`
- Native reports and graphs: `Backtest Reports\Exness\`
- Selected native report (final installed-build verification): `Backtest Reports\Exness\lta-exness-125-final.htm`
- Selected equity graph: `Backtest Reports\Exness\lta-exness-125-final.png`

The selected preset and safety-capped EA are also installed in the standard MT5 data folder. The portfolio BAT was not changed.
