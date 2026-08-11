# AAA Final IVB FRVP EA

## Status: rejected for the active portfolio and disabled

This EA builds a tick-volume profile from the first 30 minutes after the New York cash open, waits for an accepted opening-range breakout, then enters a qualifying pullback to VAH.

Best researched US30 M1 settings:

- New York open: 09:30, opening range: 30 minutes.
- Fixed-range profile: 24 bins and 70% value area.
- Breakout relative tick volume: at least 1.10 times the preceding 20-minute mean.
- Acceptance: one close outside the opening range.
- Retest: VAH within six M1 bars, with 2% opening-range tolerance.
- Stop: beyond the signal candle plus 5% of the opening range.
- Target: 3R; no break-even, trailing stop, or timeout.
- Hard exit: 16:00 New York.
- Risk: 1% of current equity, maximum one trade per day.

The independent 2025-2026 Exness holdout was positive (+6.15%, PF 1.34), but the complete 2022-2026 Exness replay made only +5.65% with PF 1.11 and 11.71% maximum equity drawdown. This misses the system's 20% annual-return gate. `InpEnableTrading` is false in the EA defaults, and this EA is not in the active installer.

The `.set` file is retained only to reproduce the rejected test.
