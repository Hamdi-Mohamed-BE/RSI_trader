# EMA3 Pivot Reversal Backtest

- Broker symbol: **XAUUSD..**
- Period: **2025-07-29T07:13:12.811293+00:00 to 2026-07-29T07:13:12.811293+00:00**
- Timeframe: **H4**
- Pivot distance: **6 left / 6 right**
- Same-direction legs: **up to 1**
- Execution: **next H4 open after 6-right-bar confirmation**
- Test size: **0.10 lot**, starting balance **$1,000.00**

| Metric | Result |
|---|---:|
| Trades | 125 |
| Wins / losses | 58 / 67 |
| Win rate | 46.40% |
| Profit factor | 1.05 |
| Net profit | $1,751.80 |
| Ending balance | $2,751.80 |
| Return | 175.18% |
| Max realized DD | 132.77% |
| Max equity DD | 137.41% |

EMA and Bollinger values are plotted by the original indicator but do not
participate in its Buy/Sell label logic. The backtest therefore follows
the confirmed pivot labels exactly and does not add unrequested filters.
