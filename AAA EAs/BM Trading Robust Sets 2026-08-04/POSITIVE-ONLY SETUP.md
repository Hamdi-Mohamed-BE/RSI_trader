# User-selected positive-return setup

The synchronized BAT launches the twelve selected portfolio EAs plus News Pulse as a forced temporary test inclusion.

| Included EA | Symbol / chart | Return | Equity max DD | PF | Trades |
|---|---|---:|---:|---:|---:|
| LTA Volume Profile | XAUUSD M15 | +82.05% | 14.39% | 1.37 | 246 |
| ORB Volume Profile | XAUUSD M5 | +8.19% | 6.40% | 1.53 | 50 |
| ATR Candle Breakout | XAUUSD H1 | +30.20% | 8.77% | 1.40 | 117 |
| AAA Final Asia Breakout | XAUUSD H1 | +21.40% | 12.66% | 1.27 | 118 |
| AAA Final DmC | XAUUSD H1 | +20.90% | 9.82% | 1.15 | 233 |
| Go Long | US30 D1 | +17.24% | 8.29% | 1.20 | 312 |
| AAA Final EMA3 | XAUUSD H4 | +15.76% | 3.93% | 2.14 | 39 |
| AAA Final XAU Weakness | XAUUSD M15 | +9.19% | 17.89% | 1.05 | 277 |
| Ninja Turtle Scalper | EURUSD M5 | +8.48% | 8.54% | 1.13 | 353 |
| Nasdaq Overnight | USTEC M1 | +7.85% | 2.39% | 1.85 | 71 |
| Turnaround Tuesday | USTEC D1 | +3.29% | 6.11% | 1.20 | 30 |
| AAA Final US100 Weakness | USTEC M15 | +3.27% | 6.04% | 1.15 | 70 |
| AAA Final News Pulse — robust long-only 60-second preset | XAUUSD M1 | +62.51% | 1.46% | 41.00 | 19 |

Portfolio rows other than News Pulse use the prior Exness 2025-08-07 through 2026-08-06 independent tests. The updated News Pulse row uses Exness 2025-08-07 through 2026-08-08, USD 10,000 initial balance, 1% planned buy-side risk, and MT5 Every Tick generated from Exness M1 history. Its separate random-delay stress test returned +62.66%, PF 42.76 and 1.98% maximal equity drawdown. These are generated-tick backtests, not live fills or broker real-tick proof.

The installer accepts any positive balance and defaults to 1% planned risk. LTA remains fixed at 1.00%; percentage-risk inputs are adapted to 1%; Ninja Turtle's money-risk input is adapted to 1%; Go Long and Turnaround Tuesday receive broker-specific lots and hard stops targeting 1%.

This is no longer a strict +20% portfolio. ORB Volume Profile retains the validated baseline entry logic while displaying POC/VAH/VAL; its failed automatic profile filters are disabled. News Pulse is long-only and places no sell-stop, so its planned event risk is 1%. Thirteen simultaneous EAs can still stack much more account exposure before gaps, slippage and correlations.
