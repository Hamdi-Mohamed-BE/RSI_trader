# In-play ORB — raw test report (2026-09-25)

Source: the user's pasted transcript of Lance's "opening range break" video. Design choices and why (`run-config.json`):
the repo's 7 deployed ORB EAs and ~12 ORB studies are single-instrument; the video's core claim is that ORB works on
IN-PLAY stocks, which the 12 stock CFDs in the isolated tester finally allow testing (cross-sectional selection by opening
relative volume). **Result: FAIL on all 5 variants in the screen; nothing advanced to the real-tick stage.**
Research only; nothing deployed. Full tables: `RESULTS.md` / `native/report-screen.log`.

## Rules (EA/In Play ORB Research EA.mq5, multi-symbol, 0 errors / 0 warnings)

OR 09:30–10:00 NY (M5 wick high/low). In-play = opening relative volume (OR tick volume / 14-session average) ≥ 1.5,
top 2 of 12 stocks (top 1 of US500/USTEC/US30 for the macro case). Entry: first M5 close beyond the OR, 10:00–14:00 NY,
one trade per symbol per day; stop at the other side of the OR; skip OR > 2 ATR(D1); exit end of day (earlier of 15:40
NY / 19:40 UTC) or 2R. Variants: both directions, continuation (with the gap), exhaustion (against the gap), 2R, indices.
Controls: the same trades on randomly chosen symbols (same number per day). Screen: Model 1, 3y and 5y to 2026-09-25,
$10,000, 1% risk per trade. Mechanics verified on the first run (picks, RV/gap, EOD exits, stops; clean journal).

## Screen results (trades, per month, per trading day)

| Variant | 3y | 5y | Random-symbol control 5y |
|---|---|---|---|
| Stocks, both directions | 454 (12.6/mo, 0.58/day) −28.3% PF 0.77 win 44% | 724 (12.1/mo, 0.56/day) −35.8% PF 0.82 | −67.6% PF 0.86 (2,241 trades) |
| Stocks, continuation | 264 (7.3/mo, 0.34/day) −18.3% PF 0.76 | 409 (6.8/mo, 0.31/day) −27.4% PF 0.77 | −35.0% PF 0.88 |
| Stocks, exhaustion | 189 (5.2/mo, 0.24/day) −12.3% PF 0.77 | 313 (5.2/mo, 0.24/day) −8.6% PF 0.91 | −48.0% PF 0.83 |
| Stocks, both, 2R | 454 (12.6/mo) −27.6% PF 0.78 | 724 (12.1/mo) −37.2% PF 0.81 | −62.7% PF 0.87 |
| Indices, macro days | 159 (4.4/mo, 0.20/day) −20.1% PF 0.69 | 191 (3.2/mo, 0.15/day) −20.9% PF 0.73 | −7.6% PF 0.98 |

(The controls trade 2–3× more often because random picks do not require RV ≥ 1.5, so compare PF rather than return.)

## Findings

1. **Every variant loses** (PF 0.69–0.91); win rates 42–46%.
2. **The in-play selection does not help:** per-trade quality (PF) of in-play picks is equal to or worse than random picks
   in 4 of 5 variants; for indices, high-volume "macro" days are clearly worse than random days (PF 0.73 vs 0.98).
3. Limits of this test: CFD tick volume is only a proxy for exchange volume; no news/earnings feed, so catalysts are
   approximated by the gap; the universe is 12 mega-caps, not the thousands of small caps Lance scans, where "in-play"
   names are far more extreme. The result says the idea does not transfer to these Exness CFDs, not that it never works.
4. Consistent with the repo's earlier ORB work: `Paper 5M ORB US100` found the relative-volume filter hurt on US100 as well.

## Decision

Fails the pre-registered gate; no optimization. The deployed index ORB EAs are unaffected.
