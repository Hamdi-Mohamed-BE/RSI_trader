# EMA3 Pivot Reversal Backtest

- Broker symbol: **XAUUSD..**
- Period: **2026-06-02T11:38:36.122222+00:00 to 2026-08-01T11:38:36.122222+00:00**
- Timeframe: **H4**
- Pivot distance: **6 left / 6 right**
- Same-direction legs: **up to 1**
- Execution: **next H4 open after 6-right-bar confirmation**
- Test size: **0.10 lot**, starting balance **$1,000.00**

| Metric | Result |
|---|---:|
| Trades | 23 |
| Wins / losses | 10 / 13 |
| Win rate | 43.48% |
| Profit factor | 1.00 |
| Net profit | $33.10 |
| Ending balance | $1,033.10 |
| Return | 3.31% |
| Max realized DD | 403.26% |
| Max equity DD | 394.97% |

EMA and Bollinger values are plotted by the original indicator but do not
participate in its Buy/Sell label logic. The backtest therefore follows
the confirmed pivot labels exactly and does not add unrequested filters.
