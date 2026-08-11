# AAA Final US100 Asia London Continuation EA

Research implementation of the proposed Asia/London-to-New-York continuation idea.

## Exact signal implemented

- Sessions use `America/New_York` time and automatically observe New York daylight saving time.
- Asia: previous New York calendar day 18:00 through 03:00.
- London: 03:00 through 09:30.
- Both sessions must close in the same direction relative to their own opens.
- The matching extreme of the first New York 15-minute range must be within 20.00 index points of the Asia-session extreme:
  - bullish: `abs(New York OR high - Asia high) <= 20.00`
  - bearish: `abs(New York OR low - Asia low) <= 20.00`
- On a broker whose trade tick is 0.01, 20.00 index points equals 2,000 broker ticks. The EA deliberately names this in **index points**, not ambiguous pips.
- Entry: break of the first New York 15-minute range after 09:45, allowed through 10:30.
- Stop: the larger of 1.25 times that opening range or 20.00 index points.
- Target: 2R.
- Trailing: disabled. The parameter search did not improve validation robustness with break-even or M15 trailing.
- Hard exit: 16:00 New York.
- One attempted setup per New York trading day.
- Position sizing: 1% of current account equity at the initial stop.

## Safety and use

The source-code default has `InpEnableTrading=false`. Load the Exness test preset deliberately to enable it. The EA was **not** added to the portfolio installer because this research has a small sample and the user did not request deployment.

Use `USTEC` on Exness with the Exness preset. Use `UT100` on MEXAtlantic with the cross-broker preset; its only difference is the historical tester server-clock conversion.

This strategy is promising research, not a guarantee. Exness produced only 86 trades across roughly seven years, and MEXAtlantic produced only 34 trades across roughly four and a half years. A losing calendar year occurred on the MEX replay.

Full evidence and data hashes are under `Research`.
