# User-selected positive-return setup

The synchronized BAT launches the eleven EAs the user selected from the corrected independent Exness one-year retest.

| Included EA | Symbol / chart | Return | Equity max DD | PF | Trades |
|---|---|---:|---:|---:|---:|
| LTA Volume Profile | XAUUSD M15 | +82.05% | 14.39% | 1.37 | 246 |
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

Test basis: Exness, 2025-08-07 through 2026-08-06, USD 10,000 initial balance per independent test, 1% planned risk per trade, MT5 Every Tick generated from Exness M1 history with random execution delay.

The installer accepts any positive balance and defaults to 1% planned risk. LTA remains fixed at 1.00%; percentage-risk inputs are adapted to 1%; Ninja Turtle's money-risk input is adapted to 1%; Go Long and Turnaround Tuesday receive broker-specific lots and hard stops targeting 1%.

This is no longer a strict +20% portfolio: seven included bots returned less than +20% because the user explicitly requested every positive bot in the table. Eleven simultaneous trades could stack planned exposure to roughly 11% before gaps, slippage and correlations.
