# Exness XAU historical-DD5 optimization — 2026-08-06

## Selected setting

- EA: `LTA_Concepts_EA` version 1.10, with the built-in 2.5% absolute risk ceiling intact
- Symbol and timeframe: Exness `XAUUSD`, M15
- Preset: `Best Settings\XAUUSD M15 - EXNESS DD5 PASS - 0.34pct - DD4.78.set`
- Risk: 0.34% of current equity per trade for both momentum and contrarian entries
- Reward/risk: unchanged at 3.0R
- Move-all-to-breakeven at 1R: disabled
- Result: +$2,215.64 (+22.16%) from $10,000, ending at $12,215.64
- Maximum relative equity drawdown: 4.78% ($540.32)
- Profit factor: 1.42

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
| Plain | 0.30% | $1,284.44 | 12.84% | 4.41% | 1.27 | Pass |
| Plain | **0.34%** | **$2,215.64** | **22.16%** | **4.78%** | **1.42** | **Selected** |
| Plain | 0.35% | $2,106.55 | 21.07% | 5.14% | 1.40 | Fail |
| Plain | 0.36% | $2,311.37 | 23.11% | 5.22% | 1.42 | Fail |
| Move all to BE at 1R | 0.38% | $1,994.40 | 19.94% | 4.37% | 1.42 | Pass, lower profit |
| Move all to BE at 1R | 0.40% | $1,922.24 | 19.22% | 4.73% | 1.38 | Pass, lower profit |
| Move all to BE at 1R | 0.42% | $1,923.77 | 19.24% | 5.41% | 1.37 | Fail |

The 0.34% plain preset had the highest tested net profit while keeping historical relative equity drawdown below 5%. The 0.35% setting already exceeded the limit, and the breakeven variants reduced profit.

## Full selected-run statistics

| Statistic | Result |
|---|---:|
| Initial balance | $10,000.00 |
| Final balance | $12,215.64 |
| Net profit | $2,215.64 |
| Gross profit | $7,535.19 |
| Gross loss | -$5,319.55 |
| Balance drawdown | 4.42% ($498.15) |
| Equity drawdown | 4.78% ($540.32) |
| Profit factor | 1.42 |
| Recovery factor | 4.10 |
| Sharpe ratio | 4.72 |
| Expected payoff/trade | $8.90 |
| Total trades | 249 |
| Winning trades | 79 (31.73%) |
| Losing trades | 170 (68.27%) |
| Average winning trade | $95.38 |
| Average losing trade | -$31.03 |
| Largest winning trade | $122.32 |
| Largest losing trade | -$41.68 |
| Longest losing sequence | 17 trades (-$486.71) |

## Important limitation

The 4.78% figure is the maximum drawdown observed in this historical test, not a hard live-account guarantee. Slippage, gaps, spread changes, different data, and simultaneous positions can push live drawdown above 5%. The 0.30% preset produced 4.41% historical drawdown and offers slightly more buffer, but with materially lower tested profit. A separate account-level equity stop is needed if trading must stop at a strict 5% account loss.
