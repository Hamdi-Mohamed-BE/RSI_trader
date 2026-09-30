# US100 transfer — rules frozen before testing

User request: try the same raw strategy on US100 and US500. This asset uses broker symbol USTEC. Exact gold EA source and binary, same risk, 3R, dates, entries, exits, session, costs/delay and predeclared gate. Broker contract sizes and tick sizes are read dynamically. This is index CFD tick-volume data, not centralised futures volume. The 09:30 NY opening convention coincides with the US cash equity open. No optimization, production, BAT or website changes.

The following is the original frozen gold specification retained as provenance; gold-specific context does not change the above symbol:

# Gold NY30 Value Area + VWAP — raw test
Rules frozen 2026-09-27 before compilation or performance results. Source: the user's Arabic reel transcript. This is an independent mechanical interpretation on gold, not Deep-M IVB replication.

## What the source actually establishes
First 30 minutes of New York opening; fixed-range volume profile; M1 execution; false breakout back inside value area with VWAP-band acceptance; VWAP touch to break-even in the reversal example; later band reclaim and retest for continuation; a 3R target. Stop locations, exact acceptance, profile settings, VWAP anchor, entry time limit and trade cap are not completely specified.

## Explicit defaults (ours)
- 09:30–10:00 America/New_York, DST aware. This transfers the Nasdaq cash-open convention to gold; it is not the COMEX gold open.
- Require all 30 opening M1 bars. Freeze profile at 10:00. 64 bins, M1 typical price assigned to one bin weighted by tick count, contiguous 70% VA around POC. POC ties lower bin; adjacent-volume ties expand upward. This reuses the existing raw profile convention, NOT exact traded volume at each price.
- VWAP starts 09:30, HLC3 weighted by M1 tick volume. Bands are +/-1 volume-weighted standard deviation of HLC3, not 1% and not guaranteed identical to the video's indicator. Only completed bars enter calculations.
- Reversal and continuation use the precise state machines in run-config.json. One-bar separation prevents a breakout and retest being assumed to occur in the right order in one candle.
- Stops beyond the relevant extreme by one tick; minimum entry-stop distance three current spreads (skip, never widen). 3R target from requested entry; actual fill slippage can change realized initial RR.
- Reversal break-even is at actual fill and therefore gross, not net of commissions/swaps. Latest completed-M1 VWAP must be favorable to entry; broker stop/freeze-distance restrictions apply. Continuation has no BE.
- Entry deadline 15:30; request flat 15:55; closed-market holdings exit only when executable and must remain in the results. No overnight/weekend profit or risk erased.
- One open position, maximum one attempt per engine/day, maximum two entries combined. No forced reversal of an existing position. Bull/bear rules mirrored. Control maximum one entry per direction.
- $10,000 research start, target 1% current equity, lots rounded UP per existing pipeline. Minimum lot and round-up can exceed intended risk; log actual initial cash risk. Broker spread, swaps and commissions are retained, fixed 150ms execution-delay simulation is not a measured live slippage forecast.
- Isolated Exness tester only. Research EA refuses to run outside the strategy tester. No live account API, BAT, website or production configuration change.

## Four predeclared versions
1. Reversal only.
2. Continuation only.
3. Both, sharing position and session limits (not the arithmetic sum of standalone results).
4. Plain M1 close opening-range breakout, same 3R and structural candle stop, no profile/VWAP filters: a benchmark, not proof of a causal effect.

## Evaluation
Use 6m/1y/3y/5y ending 2026-09-27 exclusive. Smoke first; Model 1 long-window screen; Model 4 requested-mode runs on all windows with journal coverage disclosed. Do not relabel generated ticks as real.
Long-window raw gate: positive, PF >=1.15, >=30 trades, PF and return/equity-DD better than control on both 3y/5y. Winner only among qualifying variants, robust across the long windows. No tuning from these results. Complete native report validation, trade reconstruction, signal and profile no-lookahead audit, initial-risk and exit checks.
A coverage problem leaves verification incomplete even if the headline metrics pass. This is not a funded-account simulation and overlapping windows are not independent validation.

## Research sources checked
- https://helpdesk.deepcharts.com/portal/en/kb/articles/deep-m-ivb — product's official description, not its unpublished equations or independent proof.
- https://www.tradingview.com/support/solutions/43000502018-volume-weighted-average-price-vwap/ — VWAP concepts; our precise band formula is stated above.
- https://www.tradingview.com/support/solutions/43000502040-volume-profile-indicators-basic-concepts/ — VA/POC concepts and distinction between tick and traded volume.

