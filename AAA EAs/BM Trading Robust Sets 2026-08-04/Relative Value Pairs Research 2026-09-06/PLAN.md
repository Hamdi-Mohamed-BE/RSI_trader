# Step 2 — Relative-value pairs research

Research only. No live orders, no production installers, no website promotion.

## Locked scope before reading results

- Pairs: BTCUSD/ETHUSD and XAUUSD/XAGUSD; broker symbols must exist and be synchronized.
- Context: 2023-09-01 through 2026-09-01; warm-up from 2023-06-01 where available.
- Training: 2023-09-01 through 2024-09-01. Selection validation: 2024-09-01 through 2025-09-01. Final test: 2025-09-01 through 2026-09-01. Final test is not used to select settings.
- Risk: 1% of equity combined across the two legs, rounded down to broker lot steps. This is planned risk, not a guaranteed loss cap during gaps or leg-execution failures.
- M5, M15, M30, H1 and H4 decisions. Both symbols' bars must have matching timestamps; never forward-fill a missing quote into an entry.
- Sessions: all day, Asia 00:00–08:00 UTC, London 08:00–17:00 local, New York 08:00–17:00 local, London/New York overlap, and London-or-New-York. Local sessions use historical DST.
- Spread models: log price ratio (equal dollar notionals) and rolling log-price OLS hedge ratio. Use only prior completed bars to fit; freeze the hedge ratio for an open trade.
- Entries: standardized divergence 1.5, 2.0, 2.5 or 3.0; 32, 64 and 128-bar estimation windows; both directions plus each spread direction separately.
- Stops: fixed residual standard-deviation distance, spread ATR distance, and recent adverse spread swing. Cash basket risk and per-leg emergency stops required in native validation.
- Exits: fixed 0.5R, 1R, 1.5R, 2R, 3R, 4R, 6R; entry-time mean target (adaptive entry RR); rolling-mean target (genuinely changes while holding); time-only exit.
- Management: none, breakeven at +0.5R or +1R, M15 completed-close +0.5R to +0.2R basket floor, trailing from +1R with 0.5R or 1R distance, and spread-volatility trailing.
- Holding limits: 6, 24 or 72 hours. Financing cannot be ignored for overnight positions.
- Broad screen cross-tests timeframe × session × stop × exit. Signal and management refinements follow, preserving all results and showing that this is staged optimization, not an infinite exhaustive search.
- Training ranks require meaningful trade counts and penalize drawdown. Lock candidates using selection-validation stability, then open the final year once. No forced winner if none survives.
- Native MT5 multi-symbol execution checks for baseline and locked candidates, generated Every Tick with random delay; attempt real ticks where available. Report both leg and completed basket counts, including broken/partial baskets.
- Cost stress, rolling/yearly breakdowns, parameter sensitivity, 5,000 block-bootstrap Monte Carlo paths, graphs and auditable trade ledgers. Simulation frequencies are conditional, not future probabilities.

## Evidence distinctions

Python synchronized-bar screening is an approximation and must not be presented as an MT5 tick backtest. No synthetic forward-filled prices, guaranteed future gains, or claims that correlation establishes cointegration. Historical swap schedules and commissions may not be fully available; assumptions and native/Python differences must be explicit.

## Sources

- https://www.nber.org/papers/w7032 — original relative-value pairs research (equities, not evidence these two pairs work).
- https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.coint.html — Engle–Granger test; null is no cointegration.
- https://www.mql5.com/en/docs/runtime/testing — native multi-symbol tester synchronization and execution limitations.
- https://www.metatrader5.com/en/terminal/help/start_advanced/start — tester configuration and execution modes.
