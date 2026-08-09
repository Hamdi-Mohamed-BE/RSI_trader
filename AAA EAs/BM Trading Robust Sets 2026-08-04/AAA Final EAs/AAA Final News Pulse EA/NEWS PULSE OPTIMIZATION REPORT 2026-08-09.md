# News Pulse robust optimization — 9 August 2026

## Decision

No parameter set can guarantee a 100% win rate. The retained configuration is the 60-second exit because it had the strongest full-year drawdown-adjusted result and remained profitable under the random execution-delay stress test.

Retained inputs:

- XAUUSD M1; NFP, CPI and FOMC only
- 1% planned equity risk per filled side; no OCO cancellation
- Place orders 30 seconds before the broker-calendar release time
- Buy/sell entry offset: $6
- Stop: $6
- Start trailing at 1.5R; trail distance: $15
- Close all EA exposure 60 seconds after the event

## Exact generated-tick comparison

Test basis: Exness XAUUSD, 7 August 2025 through 8 August 2026, USD 10,000 initial balance, MT5 Every Tick generated from broker M1 history, 99% history quality.

| Configuration | Return | Equity max DD | PF | Win rate | Wins / losses | Trades |
|---|---:|---:|---:|---:|---:|---:|
| Previous baseline: $12 entry / $10 stop / 120s | +21.30% | 4.75% | 4.70 | 56.52% | 13 / 10 | 23 |
| $6 entry / $6 stop / 180s | +82.55% | 4.39% | 7.68 | 68.57% | 24 / 11 | 35 |
| $6 entry / $6 stop / 120s | +81.12% | 4.34% | 8.10 | 70.59% | 24 / 10 | 34 |
| $6 entry / $6 stop / 90s | +80.48% | 3.76% | 9.23 | 68.75% | 22 / 10 | 32 |
| **Retained: $6 entry / $6 stop / 60s** | **+76.92%** | **2.37%** | **10.29** | **65.62%** | **21 / 11** | **32** |
| $6 entry / $6 stop / 30s | 0.00% | 0.00% | 0.00 | 0.00% | 0 / 0 | 0 |

The 30-second version did not find an edge: its event window ended before any simulated trades qualified.

## Wider-stop control

Entry, trailing and the 60-second exit were held constant so only stop size changed.

| Stop | Return | Equity max DD | PF | Win rate | Trades |
|---:|---:|---:|---:|---:|---:|
| $6 | +76.92% | 2.37% | 10.29 | 65.62% | 32 |
| $10 | +39.42% | 2.02% | 7.66 | 65.62% | 32 |
| $14 | +25.26% | 1.97% | 6.25 | 65.62% | 32 |

Widening the stop did not save a single extra losing trade. With risk fixed at 1%, it reduced position size and cut returns.

## Forward and execution stress

The last three months, 9 May through 8 August 2026, were checked separately:

| Candidate | Return | Equity max DD | PF | Win rate | Trades |
|---|---:|---:|---:|---:|---:|
| Retained 60s | +40.90% | 2.42% | 22.45 | 77.78% | 9 |
| Alternative 90s | +41.79% | 1.90% | 26.96 | 77.78% | 9 |

The retained 60-second configuration was also retested over the full year with MT5 random execution delay: +83.46% return, 2.62% equity max DD, PF 11.28, 62.50% win rate, 32 trades.

## Important limits

- The search space contained 13,500 possible combinations. MT5's genetic optimization evaluated 177 passes, then the strongest parameter families were retested with the exact generated-tick model.
- These are generated ticks reconstructed from M1 bars, not broker real-tick history. News trading is unusually sensitive to tick order, spread expansion, stop-order gaps and slippage.
- Only 32 closed trades occurred. The nine-trade forward sample is supportive but too small to prove the edge statistically.
- Risk is 1% per filled side. Because both pending orders intentionally remain active, two fills can create up to 2% planned event risk. Gaps can lose more: the largest simulated loss in the retained test was $167.59 on the $10,000 account (1.68%).
- The saved BAT preset is updated for the next installation. This report does not restart or modify the EA already attached to a live chart.

## Native reports

The reports are saved in `_Backtests/MT5-Isolated-20260805/reports`, including:

- `news-pulse-exact-a60.htm`
- `news-pulse-exact-a60-oos.htm`
- `news-pulse-exact-a60-random-delay.htm`
- `news-pulse-exact-a60-stop10.htm`
- `news-pulse-exact-a60-stop14.htm`
- `news-pulse-exact-a90.htm`
