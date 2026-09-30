# XAU Slow Trend: weekly entry limits (exploratory)

Frozen before weekly variant results, 29 September 2026. Research only; no changes to active MT5, installed EA, website or portfolio. Recent historical prices have already been examined in earlier research: no period here is a pristine holdout. This is a bounded follow-up, not a new full-pipeline qualification.

## Four variants, two retained controls

- calendar: original strategy, at most one successful entry in a Monday 00:00 to next Monday 00:00 broker-time week.
- rolling7: original strategy, at least 604800 seconds between entries.
- adx-calendar: calendar rule plus the previously selected ADX14 >=20, directional DI alignment and rising ADX on the last closed H4 candle.
- adx-rolling7: rolling7 rule plus the same ADX/DI filter.
- Controls: previous baseline and adx20-di-rising, with weekly limit disabled. Both controls must match their existing one-year trade ledgers exactly before new tests begin: Model1 for baseline, Model4 for ADX (the available prior reference).

These are maximum entry frequencies, not mandatory weekly orders. Existing positions may carry across weeks; there is still only one position. The original 24-hour entry cooldown, 1% equity sizing (including original lot-rounding-up behavior), ATR stop, 6R target and all exits remain unchanged. No weekday selection, target optimization or compensating risk increase. New filter defaults off. Full stateful native reruns, never post-hoc deletion of ledger rows. Manual interventions are not simulated.

Calendar weeks use broker time (Exness GMT+0). A weekly reset does not waive the original 24-hour cooldown. Both rules count entries, not exits: after a sufficiently old trade is manually closed, immediate re-entry can still occur. A permanent manual-close override is a separate feature.

## Validation and selection

1. Calendar arithmetic self-tests (Sunday/Monday, year boundary, leap year, rolling interval) and exact off-switch parity for both controls.
2. All four candidates: development 2021-09-27 to 2024-09-27, Model1 (1-minute OHLC screen); validation 2024-09-27 to 2025-09-27, Model1.
3. Select using those two older windows only. Require development >=20 trades, positive return and PF>=1.15; validation >=10 trades, positive return and PF>=1.10. Rank validation return/equity drawdown. If none qualify, retain highest validation return/drawdown as explicitly failed exploratory candidate.
4. All four candidates: recent six months, 2026-03-27 to 2026-09-27, Model4 (real ticks where available). Selected candidate also gets one-year Model4 2025-09-27 to 2026-09-27. Do not reselect after viewing recent results.
5. All runs use isolated Exness-MT5Trial16 tester, XAUUSD H4, USD10000, 150ms execution delay, existing broker costs, existing original risk sizing. Each window starts flat and is independently liquidated at tester end. Prior control metrics remain sourced from the previous study, with source paths explicit.
6. Audit native ledger reconciliation, no overlaps, original 24-hour spacing, maximum one calendar entry/week or minimum seven-day spacing as appropriate. Report all candidates including losses, trade counts, native equity drawdown and costs. This does not validate manually managed live performance.

Promotion requires subsequent genuinely unseen forward evidence and broader pipeline/risk validation. Fewer trades or a smoother curve alone do not establish an edge. No additional parameter search during this study.
