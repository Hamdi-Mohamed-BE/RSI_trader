# EMA3 Pivot Reversal Backtest

- Broker symbol: **XAUUSD..**
- Period: **2025-07-29T05:41:21.349342+00:00 to 2026-07-29T05:41:21.349342+00:00**
- Timeframe: **H4**
- Pivot distance: **6 left / 6 right**
- Same-direction legs: **up to 2**
- Execution: **next H4 open after 6-right-bar confirmation**
- Test size: **0.10 lot**, starting balance **$1,000.00**

| Metric | Result |
|---|---:|
| Trades | 153 |
| Wins / losses | 71 / 82 |
| Win rate | 46.41% |
| Profit factor | 0.99 |
| Net profit | $-598.40 |
| Ending balance | $401.60 |
| Return | -59.84% |
| Max realized DD | 155.12% |
| Max equity DD | 227.33% |

EMA and Bollinger values are plotted by the original indicator but do not
participate in its Buy/Sell label logic. The backtest therefore follows
the confirmed pivot labels exactly and does not add unrequested filters.
