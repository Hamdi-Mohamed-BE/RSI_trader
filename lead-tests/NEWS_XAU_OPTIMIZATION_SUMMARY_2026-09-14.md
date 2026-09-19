# News Pulse XAU parameter optimization — 2026-09-14

Research only. No production EA, BAT, website data, or active portfolio setting was changed.

## Recommendation for review

- Entry anchor: live Ask/Bid (not the forming M1 high/low)
- Placement lead: 15 seconds before the official event
- Pending offset: USD 4.00
- Stop distance: USD 4.00
- Take profit: disabled
- Trailing stop: disabled
- Forced event exit: 60 seconds after release
- Opposite pending order: remain armed until the existing expiry/cleanup logic
- Risk: 0.75% per pending side; maximum planned two-sided exposure 1.50%

The 15-second lead is recommended over the 5-second headline winner because it retained most of the ideal-fill performance and was materially more resilient in delayed-execution testing.

## Current vs recommended

| Window / execution | Profile | Return | Net win rate | Net PF | Max equity DD | Trades | Commission | Swap |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1Y, 1 ms | Current | 36.10% | 61.76% | 4.74 | 3.60% | 34 | -$27.57 | $0.00 |
| 1Y, 1 ms | Recommended | 122.35% | 60.53% | 7.82 | 3.96% | 38 | -$53.05 | $0.00 |
| 1Y, fixed 1000 ms | Current | 48.32% | 64.71% | 5.97 | 3.15% | 34 | -$27.88 | $0.00 |
| 1Y, fixed 1000 ms | Recommended | 130.13% | 64.86% | 9.84 | 3.74% | 37 | -$51.85 | $0.00 |
| 5Y, 1 ms | Current | 53.07% | 56.39% | 2.77 | 3.62% | 133 | -$107.62 | $0.00 |
| 5Y, 1 ms | Recommended | 270.07% | 67.31% | 6.10 | 3.88% | 156 | -$251.54 | $0.00 |

Data quality: 67% real ticks for the 1Y reports and only 13% real ticks for the 5Y reports. The 5Y result is robustness evidence, not proof of executable historical performance.

## TP sweep on the recommended 15-second geometry

All rows use live quote anchoring, USD 4 offset, USD 4 stop, no trailing, and a 60-second forced exit. All produced 38 trades.

| TP | Return | Native PF | Max equity DD |
|---:|---:|---:|---:|
| 0.5R | 11.85% | 3.13 | 1.84% |
| 1.0R | 19.02% | 3.58 | 2.79% |
| 1.5R | 29.80% | 4.00 | 4.66% |
| 2.0R | 30.41% | 3.22 | 4.03% |
| 2.5R | 32.90% | 3.16 | 3.69% |
| 3.0R | 37.58% | 3.45 | 3.42% |
| 3.5R | 44.33% | 3.82 | 3.94% |
| 4.0R | 47.01% | 3.97 | 3.87% |
| 4.5R | 50.21% | 4.15 | 3.86% |
| 5.0R | 56.09% | 4.46 | 3.91% |
| 5.5R | 63.54% | 4.85 | 3.96% |
| 6.0R | 69.40% | 5.16 | 3.87% |
| 6.5R | 79.88% | 5.66 | 3.99% |
| 7.0R | 86.28% | 5.99 | 3.96% |
| 7.5R | 89.34% | 6.15 | 3.88% |
| 8.0R | 96.25% | 6.52 | 3.95% |
| No TP | 122.35% | 7.70 native / 7.82 net | 3.96% |

## Other decisions

- Forming M1 high/low anchor was weaker than live quote anchoring in the broad lead/offset sweep.
- Best trailing variant tested was start at 3R, trail by USD 12, but no trailing was stronger.
- Cancelling the opposite pending order after the first fill reduced 1Y return from 122.35% to 89.26%, while lowering drawdown from 3.96% to 2.68%.
- The pure headline winner was the same geometry with a 5-second lead: 133.43% return, native PF 11.41, 2.88% DD, 37 trades. It is not the recommendation because its operational buffer is too small for news execution.

## Cost and execution interpretation

- Model 4 uses the broker's recorded bid/ask ticks where available, so historical spread and stop-fill gaps are embedded.
- Commission is the exact amount recorded in the MT5 deals and is included in net profit.
- Swap was zero because positions were held for seconds, not overnight.
- A fixed 1000 ms delay test was added. MT5 random-delay tests were also run as an intentionally harsh diagnostic, but they can delay the pending-order request past the event and therefore change the strategy rather than merely add slippage.
