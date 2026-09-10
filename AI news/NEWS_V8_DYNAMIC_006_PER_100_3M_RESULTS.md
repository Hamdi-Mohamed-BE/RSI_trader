# Gold News V8 - Dynamic 0.06 Lot per $100, Three-Month Replay

> Before every event: lot = floor(balance / $100) x 0.06. Trading stops below $100. The frozen execution is T-5 seconds, $4 gold-price stop, no take profit, no trailing, and T+15-minute exit.

## Summary

| Measure | Result |
|---|---:|
| Starting balance | $100.00 |
| Ending balance | $71439.82 |
| Net P/L | $+71339.82 |
| Wins / losses | 5 / 3 |
| Win rate | 62.50% |
| Profit factor | 4.64 |
| Maximum realized drawdown | $19619.49 (61.72%) |
| Maximum tick-equity drawdown | $24983.11 (66.90%) |
| Minimum tick equity | $98.98 |

## Trades

| Date | Event | Call | Balance before | $100 units | Lot | Captured | Exit | P/L | Balance after |
|---|---|---|---:|---:|---:|---:|---|---:|---:|
| 2026-06-10 | CPI | POSITIVE | $100.00 | 1 | 0.06 | +22.930 USD | TIME_EXIT_T_PLUS_900s | $+137.58 | $237.58 |
| 2026-06-17 | FOMC | NEGATIVE | $237.58 | 2 | 0.12 | +94.534 USD | TIME_EXIT_T_PLUS_900s | $+1134.41 | $1371.99 |
| 2026-07-02 | NFP | POSITIVE | $1371.99 | 13 | 0.78 | +68.293 USD | TIME_EXIT_T_PLUS_900s | $+5326.85 | $6698.84 |
| 2026-07-14 | CPI | POSITIVE | $6698.84 | 66 | 3.96 | +63.360 USD | TIME_EXIT_T_PLUS_900s | $+25090.56 | $31789.40 |
| 2026-07-29 | FOMC | NEGATIVE | $31789.40 | 317 | 19.02 | -4.112 USD | STOP_LOSS | $-7821.02 | $23968.38 |
| 2026-08-07 | NFP | NEGATIVE | $23968.38 | 239 | 14.34 | -4.971 USD | STOP_LOSS | $-7128.41 | $16839.97 |
| 2026-08-12 | CPI | POSITIVE | $16839.97 | 168 | 10.08 | -4.633 USD | STOP_LOSS | $-4670.06 | $12169.91 |
| 2026-09-04 | NFP | NEGATIVE | $12169.91 | 121 | 7.26 | +81.639 USD | TIME_EXIT_T_PLUS_900s | $+59269.91 | $71439.82 |

## Important

- This is extreme compounding. A normal $4 stop is about $24 per $100 tranche before spread and slippage.
- Historical MT5 bid/ask ticks include observed spread and tick-gap slippage. Commission, latency, rejection, and future broker rules are unavailable.
- The execution configuration was selected using June 10-July 29, so the full three-month result is partly in-sample and not a clean prospective estimate.
