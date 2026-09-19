# Promotion verification — 2026-09-19

- User choice: full-year fitted NFP/CPI/FOMC combinations for XAG, BTC and EURUSD. XAU v2.16 unchanged.
- Dedicated production v2.17 compiled with zero errors and warnings.
- All three production/native one-year parity checks reproduced the selected research final balances, trade counts, win rates and equity drawdowns.
- Twelve independent native MT5 website runs completed (three assets × 6m/1y/3y/5y), fresh $10,000 balances, ending 2026-09-05. Native reports and costs reconcile with published ledgers.
- Seven maintained normal-MT5 BAT launchers route to the shared installer. Roster: 33 EAs; five news exemptions, including restored EURUSD. Unique News Pulse magic numbers retained. Ava and archived historical packages were not changed.
- Installer `-ValidateOnly -UseRecommendedSelections -UseAdaptiveProfile`: passed without changing a terminal, chart, account or profile.
- Website test suite: **82 passed**, one existing FastAPI/Starlette deprecation warning.
- Local HTTP smoke checks: all 16 News Pulse product-period APIs, four portfolio-period APIs, catalogue period values/links and manifest counts passed.
- Catalogue now honors the selected evidence period and preserves it in detail links. Manifest now contains the current 33/32 roster/evidence counts and matching news run statistics.
- The portfolio consistency audit was regenerated. Its nominal exposure diagnostic now assigns 0.75% to each triggered news side, rather than incorrectly assigning a full 1.50% event budget to each leg.
- Local website restarted on 127.0.0.1:8080. The normal MT5 process remained running unchanged; no portfolio installer execution, live attachment, manual order or Git push occurred.

## Important limits

These are hindsight-optimized results, not forward expectations. Multi-asset real-tick coverage is 100% (6m), 67% (1y), 22% (3y), and 13% (5y). The original research comparison ended 2026-09-19; website periods retain the established 2026-09-05 endpoint.

Four concurrent News Pulse straddles plan 6% combined risk before rounding, costs and gaps, and Gold News V9 adds exposure. Small stop distances can cause losses far beyond nominal risk. The portfolio is an overlay of independently sized ledgers with closed-balance drawdown, not a shared-margin/floating-equity account simulation.

Reapply a maintained BAT only when ready to change the attached trading profile. Existing website cache backups remain in `Previous Website Cache`.
