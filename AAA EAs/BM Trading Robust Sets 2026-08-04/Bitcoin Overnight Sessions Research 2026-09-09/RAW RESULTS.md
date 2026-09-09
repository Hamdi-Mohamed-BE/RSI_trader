# Bitcoin Overnight Sessions MAX(10) - raw MT5 results

This is a literal, unoptimized reproduction of the Vojtko-Dujava overnight rule on BTCUSD. It uses the paper's fully-invested exposure and deliberately adds no stop, target or Calyx filter.

| Window | Net P/L | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| paper-oos-proxy | $+4,168.33 | +41.68% | 1.33 | 50.00% | 16.15% | 112 | 1.44 | 1.81 |
| latest-1y | $-1,267.79 | -12.68% | 0.52 | 31.03% | 19.56% | 29 | -3.29 | -0.62 |
| recent-3y | $+626.38 | +6.26% | 1.06 | 45.54% | 19.57% | 112 | 0.30 | 0.25 |
| full-5y | $+3,472.75 | +34.73% | 1.18 | 48.21% | 19.71% | 168 | 0.87 | 1.08 |

## Raw verdict

HISTORICAL PASS / CURRENT FAIL. The five-year history is profitable, but the latest year loses 12.68% with PF 0.52, and the recent three-year PF is only 1.06. The raw rule is not suitable for the Calyx system, but its older genuine edge is strong enough to justify a controlled pipeline attempt if approved.

The paper has no stop-loss and uses fully invested exposure. A Calyx-compatible version must first introduce a defined stop so risk can be capped at the selected 1% per trade. It must also test the Friday/weekend, Monday and Tuesday legs separately because recent decay may be session-specific.

Five-year execution costs were $201.42 commission plus $1,236.67 swap. Maximum winning and losing streaks were both 6 trades; the average winner was $284.59 and average loser was -$222.73.

## Raw rules

- BTCUSD, long only, no stop and no profit target.
- At the 16:00 New York close, price must exceed all ten prior calendar-day 16:00 New York closes.
- Eligible entries: Friday, Monday and Tuesday on regular NYSE sessions.
- Exit at 10:00 New York: Friday entry on Monday; Monday/Tuesday entry the following morning.
- 100% notional allocation as published; this is not a live-ready Calyx risk configuration.

No website, installer, BAT, recommended system or active portfolio file was changed.
