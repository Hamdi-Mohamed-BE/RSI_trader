# BM Trading EA robustness results

Generated on 2026-08-04 using the connected MEXAtlantic-Demo symbol specifications and a USD 10,000 test deposit.

## Final selections

| EA | Final status | Symbol / chart | Unseen validation period | Net profit | Profit factor | Recovery factor | Equity DD | Trades | Quality |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| Range Breakout | Original retained | USDJPY / M5 | 2024-01-01 to 2026-08-01 | $6,163.50 | 1.19 | 1.60 | 20.73% | 658 | 100% |
| Go Long | Original retained | US30 / D1 | 2021-01-01 to 2026-08-01 | $2,054.26 | 1.12 | 2.81 | 6.79% | 1,439 | 99% |
| Turnaround Tuesday | Original retained | UT100 / D1 | 2023-01-01 to 2026-08-01 | $73.50 | 1.86 | 2.53 | 0.29% | 96 | 99% |
| Ninja Turtle Scalper | Research only - no profitable set | EURUSD / M5 | 2025-01-01 to 2026-08-01 | -$768.65 | 0.94 | -0.40 | 18.74% | 539 | 54% real ticks |
| The Fisherman | Optimized | EURUSD / H1 | 2023-01-01 to 2026-08-01 | $210.20 | 1.41 | 0.84 | 2.39% | 87 | 100% |
| ATR Candle Breakout | Optimized | XAUUSD / H1 | 2023-01-01 to 2026-08-01 | $8,153.19 | 1.24 | 2.74 | 18.26% | 487 | 99% |

## What changed

- Range Breakout, Go Long and Turnaround Tuesday: the extra optimized candidates were weaker on unseen data, so their earlier presets were retained.
- The Fisherman: retracement 0.2%, TP 0.5%, SL 1.25%, daily MA period 50, RSI filter enabled. Its comparable original preset lost $293.78 over the same unseen period.
- ATR Candle Breakout: ATR period 250, multiplier 2.5, close proximity 25%, minimum body ratio 20%, SL 0.5%, TP 2%, fixed $100 risk. It improved net profit from $7,736.78 to $8,153.19 and recovery factor from 2.58 to 2.74 over the same unseen period.
- Ninja Turtle: all 243 searched combinations across M5, M15 and H1 Donchian timeframes lost money in training. The included original file is kept only for research and is clearly named as such.

## Method

The strategy inputs were optimized on older data, ranked by recovery factor with drawdown and trade-count limits, and then retested on a later unseen period. Final candidates were also compared against the original preset over identical dates. Position size was not optimized.

The `_Optimization Evidence` folder contains the MT5 optimization XML files and the selected validation reports.

## Important

These are historical simulations, not a promise of future profit and not a recommendation to trade live. Broker symbols, spreads, commissions, server time, slippage and future market conditions can materially change the results. Use a demo account first and confirm the symbol name and chart timeframe shown above.
