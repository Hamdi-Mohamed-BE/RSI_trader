# Best 1-Step Search 2026-11-11 — REPORT

Owner: Nasdaq 5M, Overnight Bias ORB, Gold Band Wave and EMA3 are must-haves; best FTMO 1-Step portfolio; aim 60%+ pass within 2 months.
Method in PLAN.md (frozen engines, FTMO 1-Step $100k, weekday starts, 180-day horizon, streams 2021-10-07 -> 2026-10-06, 13-EA pool). Addendum A
(declared before any validation result): dev-infeasible winners excluded. In-sample / selection-biased; OOS 2024-10 -> 2026-10 previously viewed.

## Answer: 60% within 60 days is NOT reached by any portfolio with the four must-haves (MC best guarded 36%, best no guard 46-52% with 7-41% breaches).

Rule pick (forced, GUARD 0.75%, 11 EAs incl. Vault Break + ORB VP, without USDJPY / XAU Squeeze) vs Core 9 + P4 (GUARD 0.5%, 11 EAs) — pass within 30 / 60 / 90 / 180 days, breach:

| Portfolio | Period | ≤30 d | ≤60 d | ≤90 d | ≤180 d | Breach | Median days | Trades/month | Trades/day |
|---|---|---|---|---|---|---|---|---|---|
| **Core 9 + P4, guard 0.5% (BUILT)** | dev 2021-23 | 3% | 18% | 35% | 65% | 0% | 87 | 64.5 | 3.07 |
| | val 2023-24 | 17% | 59% | 91% | 100% | 0% | 50 | | |
| | OOS 2024-26 | 14% | 54% | 82% | 86% | 0% | 54 | | |
| | MC 2,000 | 9% | 35% | 57% | 78% | 0% | 65 | | |
| Rule pick, guard 0.75% | dev | 12% | 26% | 30% | 33% | 0% | 41 | 80.1 | 3.81 |
| | val | 15% | 52% | 68% | 70% | 0% | 47 | | |
| | OOS | 25% | 52% | 59% | 63% | 0% | 35 | | |
| | MC | 17% | 36% | 47% | 53% | 0% | 45 | | |
| Core 9 + P4, NO guard 0.5% | dev | 8% | 28% | 46% | 70% | 28.2% | 71 | 64.5 | 3.07 |
| | val | 18% | 60% | 90% | 93% | 7.3% | 48 | | |
| | OOS | 26% | 64% | 83% | 91% | 9.1% | 42 | | |
| | MC | 13% | 46% | 68% | 90% | 7.4% | 60 | | |
| Core 9, guard 0.5% (ref) | MC | 4% | 27% | 49% | 82% | 0% | 79 | 50.7 | 2.41 |
| P4, guard 0.5% (ref) | MC | 3% | 15% | 29% | 58% | 0% | 88 | 38.7 | 1.84 |
| All 13, guard 0.5% (ref) | MC | 9% | 39% | 60% | 78% | 0% | 60 | 89.9 | 4.28 |
| All 13, NO guard 0.5% (ref) | MC | 17% | 52% | 70% | 82% | 17.4% | – | 89.9 | 4.28 |

No forced NO GUARD pick exists: the only dev-feasible no-guard winner (0.5%) breached 6.1% in validation (> 5%).

Why Core 9 + P4 is built instead of the rule pick: it is better on validation (59% vs 52% ≤60 d), OOS (54% vs 52%) and MC (35% vs 36% ≤60 d, but 78% vs 53% ≤180 d);
the rule pick is better only in development, where its members were chosen. It also excludes Vault Break (failed its own MC and validation year). This choice
is post hoc (made after seeing the reference rows) and is disclosed as such.

Trades/month from the 2021-10 -> 2026-10 streams (60 months, 21 trading days/month).
Nasdaq 5M = deployed REPLACE, DI OFF; the guard has no native tester run (it refuses the tester).
