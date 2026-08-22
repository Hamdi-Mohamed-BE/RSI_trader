# Nasdaq 5-Minute Open / EMA / ATR EA — Exness MT5 Validation

## Decision

The strategy produced a positive result, but the advertised **+406% return with about 19% drawdown was not reproduced**. The selected robust variant returned **+155.35%** over the available 7.09-year Exness history, with **27.10% maximum equity drawdown**.

This EA has **not** been added to the main installation BAT or active portfolio.

## Implemented rule

- Symbol/chart: Exness `USTEC`, M5
- Determine New York time automatically with US daylight-saving rules.
- At 09:35 New York time, evaluate the completed 09:30–09:35 candle.
- Close above EMA(12): buy. Close below EMA(12): sell.
- One entry per New York trading day.
- ATR(14) initial stop and Chandelier-style trailing stop.
- Close any remaining position at 15:55 New York time.
- Risk 1% of current equity per entry.
- Both long and short entries enabled.

The source description did not reveal its proprietary volatility formula. ATR was therefore used as the explicit, testable interpretation. A training screen compared multiple ATR stop/trailing distances. The chosen setting was then frozen before the locked validation period.

## Selected settings

| Input | Value |
|---|---:|
| EMA period | 12 |
| ATR period | 14 |
| Initial stop | 4.0 ATR |
| Trailing distance | 5.0 ATR |
| Trail activation | Immediate |
| End-of-day close | 15:55 New York |
| Risk | 1.0% of equity |
| Directions | Long and short |

## Native MT5 results

| Segment | Dates | Model | Return | PF | Win rate | Max equity DD | Trades | Final balance |
|---|---|---|---:|---:|---:|---:|---:|---:|
| Training/selection | 2019-07-16 to 2024-12-31 | 1-minute OHLC | +62.73% | 1.07 | 35.73% | 26.23% | 1,405 | $16,273.45 |
| Locked validation | 2025-01-01 to 2026-08-19 | Every tick | +70.18% | 1.26 | 37.80% | 10.47% | 418 | $17,018.49 |
| Full available history | 2019-07-16 to 2026-08-19 | Every tick | +155.35% | 1.12 | 36.07% | 27.10% | 1,824 | $25,535.37 |

The full-history MT5 test used 212,065,290 generated ticks, reported 98% history quality, and started with $10,000. Its approximate CAGR was 14.13%.

### Full-history trade statistics

- Net profit: $15,535.37
- Gross profit: $144,503.50
- Gross loss: -$128,968.13
- Wins/losses: 658 / 1,166
- Long trades: 916; 39.85% won
- Short trades: 908; 32.27% won
- Largest win/loss: $1,360.28 / -$343.24
- Average win/loss: $219.61 / -$108.30
- Balance maximum drawdown: $3,977.01 (26.21%)
- Equity maximum drawdown: $4,122.53 (27.10%)
- Recovery factor: 3.77
- Sharpe ratio reported by MT5: 2.03
- Commission: -$2,690.36
- Swap: -$314.76
- Broker spread is included in simulated fills.

## Real-tick limitation

An additional “every tick based on real ticks” cross-check was attempted. Exness disconnected while the isolated tester tried to download the required tick archive, and MT5 stopped with `no history data`. The resulting zero-trade report is invalid and is not used in any result above. The valid final report is the synchronized MT5 **Every tick** test, not an offline/Python price simulation.

## Files

- EA source/binary: `EA/Nasdaq 5M Open EMA ATR EA.mq5` and `.ex5`
- Best settings: `Sets/BEST - USTEC M5 - 1pct - EMA12 ATR4 Trail5.set`
- Full MT5 report and charts: `Backtest Reports/Final Full History/`
- Locked validation reports: `Backtest Reports/Locked Validation/`
