# Exness XAU historical-DD8 optimization — 2026-08-06

## Selected setting

- EA: `LTA_Concepts_EA` version 1.10, with the built-in 2.5% absolute risk ceiling intact
- Symbol and timeframe: Exness `XAUUSD`, M15
- Preset: `Best Settings\XAUUSD M15 - EXNESS DD8 PASS - 0.68pct BE1R - DD7.94.set`
- Risk: 0.68% of current equity per trade for both momentum and contrarian entries
- Reward/risk: unchanged at 3.0R
- Move all open parts to breakeven at 1R: enabled
- Result: +$4,748.39 (+47.48%) from $10,000, ending at $14,748.39
- Maximum relative equity drawdown: 7.94% ($806.80)
- Profit factor: 1.47

## Test method

- Broker data: Exness MT5 `XAUUSD`
- Period: 2025-08-05 through 2026-08-04
- Model: Every tick generated from broker M1 data
- Execution: random execution delay
- Initial deposit: $10,000 USD
- Leverage: 1:2000
- History quality: 99%
- Data processed: 23,533 M15 bars and 98,282,826 generated ticks
- Optimization scope: position risk and the existing move-all-to-breakeven option only. Entry logic and 3.0R target were not curve-fitted.

## Boundary and protection tests

| Variant | Risk/trade | Net profit | Return | Max relative equity DD | PF | Status |
|---|---:|---:|---:|---:|---:|---|
| Plain | 0.50% | $3,169.30 | 31.69% | 7.03% | 1.38 | Pass |
| Plain | 0.56% | $4,579.27 | 45.79% | 7.90% | 1.47 | Pass |
| Plain | 0.57% | $4,567.22 | 45.67% | 7.96% | 1.46 | Pass |
| Plain | 0.58% | $4,755.26 | 47.55% | 8.35% | 1.46 | Fail |
| Move all to BE at 1R | 0.67% | $4,511.06 | 45.11% | 7.81% | 1.45 | Pass |
| Move all to BE at 1R | **0.68%** | **$4,748.39** | **47.48%** | **7.94%** | **1.47** | **Selected** |
| Move all to BE at 1R | 0.69% | $4,638.47 | 46.38% | 7.98% | 1.45 | Pass, lower profit |
| Move all to BE at 1R | 0.70% | $4,657.65 | 46.58% | 8.30% | 1.45 | Fail |

The 0.68% breakeven preset had the highest tested net profit while keeping historical relative equity drawdown below 8%. The 0.58% plain and 0.70% breakeven settings exceeded the limit. The 0.69% breakeven setting used more risk but earned less because broker volume rounding changed the compounded trade path.

## Full selected-run statistics

| Statistic | Result |
|---|---:|
| Initial balance | $10,000.00 |
| Final balance | $14,748.39 |
| Net profit | $4,748.39 |
| Gross profit | $14,940.28 |
| Gross loss | -$10,191.89 |
| Balance drawdown | 7.03% ($853.97) |
| Equity drawdown | 7.94% ($806.80) |
| Profit factor | 1.47 |
| Recovery factor | 5.03 |
| Sharpe ratio | 5.16 |
| Expected payoff/trade | $16.32 |
| Total trades | 291 |
| Winning trades | 66 (22.68%) |
| Losing trades | 225 (77.32%) |
| Average winning trade | $226.37 |
| Average losing trade | -$44.78 |
| Largest winning trade | $289.23 |
| Largest losing trade | -$97.52 |
| Longest losing sequence | 17 trades (-$628.70) |

## Important limitation

The 7.94% figure is the maximum drawdown observed in this historical test, not a hard live-account guarantee. The margin to 8% is only 0.06 percentage point. Slippage, gaps, spread changes, different data, and simultaneous positions can push live drawdown above 8%. The DD5 preset is the safer option. A separate account-level equity stop is needed if trading must stop at a strict account-loss threshold.
