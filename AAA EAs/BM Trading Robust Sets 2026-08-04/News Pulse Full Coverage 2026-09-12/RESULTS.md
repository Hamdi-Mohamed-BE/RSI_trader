# News Pulse — full independent period coverage

News Pulse v2.16 trading rules and current production presets. XAU uses the approved T-15, live Ask/Bid, 4-unit offset, 4-unit stop, no-trailing profile while both pending sides remain armed. USD 10,000 restarted per run; 0.75% planned risk per pending side. Actual costs and fills may exceed planned risk.

| EA | Period | Net return | Net PF | Win rate | Max equity DD | Trades | Events / placed | Tick quality | Commission | Swap |
|---|---|---:|---:|---:|---:|---:|---:|---|---:|---:|
| News Pulse XAU | 6m | +71.19% | 7.6 | 57.14% | 3.88% | 21 | 17 / 16 | 100% real ticks | $-25.77 | $0.00 |
| News Pulse XAG | 6m | +41.51% | 5.74 | 57.14% | 4.77% | 21 | 17 / 16 | 100% real ticks | $-209.06 | $0.00 |
| News Pulse BTC | 6m | +26.51% | 7.81 | 73.91% | 2.13% | 23 | 17 / 17 | 100% real ticks | $-110.58 | $0.00 |
| News Pulse XAU | 1y | +122.35% | 7.82 | 60.53% | 3.96% | 38 | 31 / 30 | 67% real ticks | $-53.05 | $0.00 |
| News Pulse XAG | 1y | +84.78% | 4.97 | 55.26% | 4.75% | 38 | 31 / 30 | 67% real ticks | $-436.15 | $0.00 |
| News Pulse BTC | 1y | +92.56% | 7.87 | 70.45% | 3.34% | 44 | 31 / 31 | 67% real ticks | $-286.71 | $0.00 |
| News Pulse XAU | 3y | +196.98% | 6.26 | 62.86% | 3.87% | 105 | 94 / 93 | 22% real ticks | $-153.22 | $0.00 |
| News Pulse XAG | 3y | +122.62% | 3.82 | 54.08% | 4.71% | 98 | 94 / 93 | 22% real ticks | $-1,145.48 | $0.00 |
| News Pulse BTC | 3y | +886.34% | 9.71 | 74.40% | 3.33% | 125 | 94 / 94 | 22% real ticks | $-2,290.93 | $0.00 |
| News Pulse XAU | 5y | +270.07% | 6.1 | 67.31% | 3.88% | 156 | 158 / 156 | 13% real ticks | $-251.54 | $0.00 |
| News Pulse XAG | 5y | +149.14% | 3.43 | 53.95% | 4.67% | 152 | 158 / 156 | 13% real ticks | $-1,801.96 | $0.00 |
| News Pulse BTC | 5y | +2439.59% | 9.31 | 72.73% | 4.45% | 198 | 158 / 158 | 13% real ticks | $-6,536.01 | $0.00 |

## Coverage and method

- 6m: 2026-03-05 to 2026-09-05, end exclusive.
- 1y: 2025-09-05 to 2026-09-05, end exclusive.
- 3y: 2023-09-05 to 2026-09-05, end exclusive.
- 5y: 2021-09-05 to 2026-09-05, end exclusive.

All 158 scheduled releases across the five-year window are sourced to BLS or Federal Reserve receipts. Event coverage and tick coverage are distinct: Model 4 can generate older ticks when broker real ticks are unavailable. Scheduled events without trades remain in the audit, not fabricated as fills. The tester journal confirms fixed 1 ms execution delay, not a random-delay stress test.

The research harness uses a faster, equivalent historical-calendar lookup. All three six-month native controls matched every trade field and statistic against the untouched strategy lookup (LOOKUP PARITY.json). XAU now uses the approved T-15 / 4-unit / no-trailing production profile; XAG and BTC retain their prior presets. Both pending directions remain independently eligible to fill. The website deal importer pairs exits to the correct long/short side when both news orders fill.

Cards, detail statistics, period selector, equity curves, trade lists and reconstructed portfolio overlays now use these period-matched records. The adaptive portfolio remains a chronological overlay of separate tests, not a joint-margin native portfolio backtest.

Sources: OFFICIAL CALENDAR.json and bls-source-receipts.json. Native HTML reports are in Backtest Reports, per-run journals in Audit, and the previous website files are preserved in Previous Website Cache.
