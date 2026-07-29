# Asian Breakout — two-month MT5 research

Test window: 2026-05-29 to 2026-07-29  
Feed: HFMarketsGlobal-Live20 M1 bid OHLC and recorded spread  
Starting balance: $1,000 per symbol  
Risk: 3% of current balance per trade, compounded  
Drawdown: includes worst M1 adverse excursion while trades were open  

## Independently optimized result per symbol

| Symbol | Trades | Win rate | PF | Max DD | Ending | Return | Entry | Stop | RR | Buffer | Max box/ADR |
|---|---:|---:|---:|---:|---:|---:|---|---|---:|---:|---:|
| XAUUSDb | 18 | 77.8% | 4.29 | 5.3% | $1,462.22 | 46.2% | M15 close | Midpoint | 3.0 | 3% | 50% |
| XAGUSD | 13 | 46.2% | 1.76 | 8.9% | $1,076.11 | 7.6% | OCO | Opposite edge | 2.5 | 3% | 35% |
| #BTCUSDr | 27 | 85.2% | 4.03 | 5.3% | $1,267.72 | 26.8% | M15 close | Midpoint | 0.5 | 5% | 70% |
| #ETHUSDr | 12 | 58.3% | 1.97 | 5.9% | $1,132.33 | 13.2% | M15 close | Midpoint | 3.0 | 0% | 35% |
| EURJPYb | 13 | 53.8% | 3.50 | 9.2% | $1,522.71 | 52.3% | OCO | Midpoint | 3.0 | 0% | 35% |
| AUDCADb | 12 | 75.0% | 5.55 | 5.7% | $1,325.21 | 32.5% | Close + retest | Midpoint | 2.5 | 0% | 100% |
| AUDCHFb | 17 | 76.5% | 3.54 | 7.6% | $1,276.53 | 27.7% | M15 close | Midpoint | 1.5 | 3% | 100% |
| GBPJPYb | 26 | 84.6% | 4.86 | 5.1% | $1,271.54 | 27.2% | M15 close | Opposite edge | 0.5 | 0% | 50% |

These are in-sample winners selected from 720 combinations per symbol. The
sample is too short to treat the very high profit factors as expected future
performance.

## RR comparison

This compares the highest-ranked cross-symbol configuration available at each
target. PF and win rate aggregate the eight independent symbol replays; worst
DD is the worst single-symbol drawdown.

| RR | Entry | Stop | Buffer | Trades | Win rate | PF | Net R | Worst DD |
|---:|---|---|---:|---:|---:|---:|---:|---:|
| 0.5 | OCO | Opposite edge | 10% | 88 | 71.6% | 1.75 | 12.22R | 9.6% |
| 1.0 | M15 close | Midpoint | 3% | 81 | 61.7% | 1.62 | 17.74R | 12.4% |
| 1.5 | OCO | Midpoint | 0% | 96 | 51.0% | 1.53 | 23.72R | 17.8% |
| 2.0 | OCO | Midpoint | 0% | 299 | 45.2% | 1.23 | 33.36R | 34.4% |
| 2.5 | OCO | Midpoint | 0% | 299 | 44.1% | 1.22 | 32.08R | 37.3% |
| 3.0 | OCO | Midpoint | 0% | 299 | 43.8% | 1.23 | 33.45R | 37.3% |

## Executable default

The absolute aggregate winner used zero buffer. The bot instead defaults to
the next practical candidate:

- Mechanical OCO at 08:00 UTC
- 3% of Asian-box height outside each boundary
- Midpoint stop
- 1.5R target
- Only trade when the box is no more than 35% of prior 14-day ADR
- Cancel unfilled entries at 13:00 UTC
- Force close at 17:00 UTC

Across all symbols this practical configuration produced 93 trades, a 50.5%
win rate, 1.46 PF, and 19.80R before compounding. Seven of eight symbols had
positive net R, but several individual results were nearly flat. It is a
research default, not a validated live edge.

## Methodology cautions

- Optimization and reporting use the same two-month sample.
- M1 OHLC cannot reveal tick order; if stop and target occur in one M1 bar,
  the stop is assumed first.
- Commissions, swaps, slippage, rejected orders, gaps, and latency are not
  fully modeled.
- There is no economic-calendar filter yet.
- The live OCO runner cancels the sibling after detecting a fill, but an
  extremely fast two-sided spike can fill both legs before cancellation.
