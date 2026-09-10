# V7 Fixed 0.08-Lot News Replay - Three Months

> Market entry at T-30 seconds using MT5 bid/ask ticks. $12 initial gold-price stop, $46 target, and $12 trailing distance activated at +$24 (2R). Positions still open at T+60 are closed at the available quote.

## Summary

| Measure | Result |
|---|---:|
| Starting balance | $100.00 |
| Ending balance | $1033.54 |
| Net profit | $+933.54 |
| Return on start | +933.54% |
| Executed trades | 8 |
| Wins / losses | 5 / 3 |
| Execution win rate | 62.50% |
| Profit factor | 3.76 |
| Maximum realized drawdown | $337.77 (26.84%) |
| Largest tick-level equity drawdown | $385.18 |
| Worst tick-level drawdown percentage | 90.63% |

## Trades

| Date | Event | Direction | Entry | Exit | Exit reason | Trail | P/L | Balance |
|---|---|---|---:|---:|---|---|---:|---:|
| 2026-06-10 | CPI | POSITIVE | 4139.776 | 4161.711 | TRAILING_STOP | YES | $+175.48 | $275.48 |
| 2026-06-17 | FOMC | NEGATIVE | 4378.984 | 4349.874 | TRAILING_STOP | YES | $+232.88 | $508.36 |
| 2026-07-02 | NFP | POSITIVE | 4064.255 | 4110.739 | TAKE_PROFIT | YES | $+371.87 | $880.23 |
| 2026-07-14 | CPI | POSITIVE | 4030.446 | 4077.713 | TAKE_PROFIT | YES | $+378.14 | $1258.37 |
| 2026-07-29 | FOMC | NEGATIVE | 4043.931 | 4056.889 | STOP_LOSS | NO | $-103.66 | $1154.71 |
| 2026-08-07 | NFP | NEGATIVE | 4313.869 | 4329.924 | STOP_LOSS | NO | $-128.44 | $1026.27 |
| 2026-08-12 | CPI | POSITIVE | 4418.233 | 4405.024 | STOP_LOSS | NO | $-105.67 | $920.60 |
| 2026-09-04 | NFP | NEGATIVE | 4471.833 | 4457.715 | TRAILING_STOP | YES | $+112.94 | $1033.54 |

## Assumptions

- Fixed 0.08 lot on every event; no compounding of lot size.
- Gross stop risk at exact fill is $96.00; spread and gaps can change it.
- Bid/ask spread and tick gaps are included. Commission, swap, latency, and rejected fills are not available historically and are excluded.
- Margin uses the connected account's 1:2000 leverage and 0% stop-out level.
- This is a retrospective simulation; prediction accuracy and execution results are separate measurements.
