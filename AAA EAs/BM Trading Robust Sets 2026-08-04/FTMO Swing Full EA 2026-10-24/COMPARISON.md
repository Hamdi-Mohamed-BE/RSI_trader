# Full EA portfolio vs the other five portfolios — FTMO 2-step (2026-10-24)

## Sources
- **Full EA** (Recommended Adaptive): `FTMO Swing Full EA 2026-10-24/` (this folder). NO_NEWS headline; optimistic and
  pessimistic breach bracket.
- **Other five:** `Portfolio Prop Comparison 2026-10-22/TABLES.md`.
- **Dollar basis:** everything is at $100k. Full EA income is its $10k result × 10 (fractional lots scale exactly).
- **Not identical engines:**
  - The other five check breaches on sampled intratrade equity, which is stricter. Full EA has no intratrade marks, so
    its "optimistic" column checks closed balance only and flatters it.
  - The five use the guard or unguarded models of the earlier study. Full EA uses its own adaptive tapers.
  - Read the comparison as indicative, not as equal-engine.
- All in-sample (EAs chosen on this history; ticks before 2026 generated). Pass rates are scenario frequencies, not
  forecasts.

## Challenge — pass both phases within 180 days of purchase (Monte Carlo / history)

| Portfolio | EAs | Risk | Pass both ≤ 180 d | Funded ≤ 90 d | Challenge breach | Stuck (guard) | Median days to funded | Trades / month |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **FTMO guarded · Current 14 + ORB** | 17 | 0.50% | 62% / 67% | 15% / 20% | 0% | 13% | 117 / 120 | 61 |
| | | 0.75%* | 69% / 74% | 28% / 37% | 0% | 36% | 101 / 91 | 48 |
| | | 1.00%* | 58% / 62% | 29% / 38% | 0% | 51% | 89 / 81 | 33 |
| **Current 14 + ORB 0.5R (no guard)** | 17 | 0.50% | 76% / 66% | 29% / 35% | 4% | – | 105 / 84 | 85 |
| | | 0.75% | 81% / 71% | 48% / 50% | 13% | – | 81 / 66 | 85 |
| | | 1.00% | 64% / 60% | 51% / 52% | 35% | – | 60 / 53 | 85 |
| **Prop ready** (Nasdaq DI ON) | 9 | 0.50% | 53% / 57% | 9% / 9% | 0% | 8% | 130 / 115 | 39 |
| | | 0.75%* | 70% / 71% | 31% / 37% | 0% | 26% | 96 / 88 | 38 |
| | | 1.00%* | 62% / 67% | 42% / 46% | 0% | 45% | 74 / 71 | 35 |
| **Best Prop** (Nasdaq DI OFF) | 9 | 0.50% | 49% / 57% | 11% / 11% | 0% | 12% | 129 / 117 | 43 |
| | | 0.75% | 63% / 66% | 30% / 36% | 0% | 35% | 94 / 85 | 42 |
| | | 1.00% | 54% / 59% | 40% / 44% | 0% | 54% | 67 / 68 | 38 |
| **ORB-only** (no guard) | 5 | 0.5 / 0.75 / 1% | 0 / 0 / 2% | 0% | 0% | – | – | 10 |
| **Full EA · Recommended Adaptive** (NO_NEWS, optimistic) | 32 | 0.50% | 64% / 53% | 38% / – | 5% (phase 1) | – | 107 / 94 | ~350 |
| | | 0.75% | 55% / 42% | 38% / – | 23% | – | 75 / 76 | ~355 |
| | | 1.00% | 38% / 29% | 29% / – | 40% | – | 56 / 48 | ~355 |
| **Full EA** (NO_NEWS, pessimistic) | 32 | 0.5 / 0.75 / 1% | 8 / 1 / 1% | – | 80 / 97 / 98% | – | – | ~360 |

\* The FTMO and Prop ready installers cap risk at 0.5%; their 0.75% and 1% rows are hypothetical guards.
Full EA trades/month = about 11.7 trades per calendar day × 30.4.

## Funded $100k — income and lifetime (Monte Carlo 36 months; history in brackets)

| Portfolio | Risk | Avg monthly income while trading | Median days until the account ends | How it ends | Total income until end (median / mean) | 12-month history: income / month and still trading |
|---|---:|---:|---:|---|---:|---|
| **FTMO guarded 17** | 0.50% | $2,634 | 1,061 | 50% freeze, 0% breach | $76.8k / $68.9k | $2,928, 79% still trading |
| | 0.75%* | $3,613 | 358 | 89% freeze | $41.1k / $53.2k | $3,806, 55% |
| | 1.00%* | $3,725 | 170 | 100% freeze | $18.5k / $27.9k | $3,067, 14% |
| **Current 14 + ORB (no guard)** | 0.50% | $3,618 | > 1,092 | 45% breach | $110.1k / $99.1k | $3,481, 72% |
| | 0.75% | $5,736 | 358 | 89% breach | $64.6k / $85.1k | $5,591, 16% |
| | 1.00% | $7,319 | 86 | 100% breach | $16.9k / $28.5k | $7,147, 0% |
| **Prop ready 9** | 0.50% | $2,257 | 847 | 59% freeze | $58.2k / $54.1k | $2,474, 60% |
| | 0.75%* | $3,701 | 232 | 97% freeze | $25.3k / $37.9k | $4,110, 36% |
| | 1.00%* | $4,841 | 105 | 100% freeze | $14.7k / $23.6k | $5,201, 27% |
| **Best Prop 9** | 0.50% | $2,192 | 529 | 77% freeze | $36.8k / $42.2k | $2,237, 62% |
| | 0.75% | $3,625 | 148 | 99% freeze | $15.8k / $25.8k | $4,134, 28% |
| | 1.00% | $5,109 | 79 | 100% freeze | $11.0k / $18.7k | $4,893, 7% |
| **ORB-only** | 0.5 / 0.75 / 1% | $310 / $469 / $642 | > 1,092 | 0 / 5 / 18% breach | $11–22k | $353–701, 100% |
| **Full EA** (NO_NEWS, optimistic) | 0.50% | $4,035 (median $3,952) | 829 (history 283) | 60% breach in 3 y; 26% in 1 y (history 59%) | $95.6k / $100.5k | $1,378, 41% |
| | 0.75% | $5,448 (median $3,906) | 107 (history 101) | 100% breach | $15.8k / $28.0k | $1,760, 9% |
| | 1.00% | $5,911 (median $1,058) | 33 (history 36) | 100% breach | $2.0k / $12.8k | $2,179, 3% |
| **Full EA** (pessimistic) | 0.5 / 0.75 / 1% | $1,916 / $90 / $0 | 16 / 3 / 1 | 100% breach | ~$0 | – |

## Recommendation — FTMO guarded · Current 14 + ORB at 0.5% (the packaged installer)
- **Consistent across both tests.** It passes both phases in 62% of MC paths and 67% of real history starts, with
  0% challenge breaches.
- **Longest-lived funded account:**
  - The median MC account lasts 1,061 days and pays about $2,634 a month per $100k ($76.8k median total).
  - In real history, 79% of accounts are still trading after 12 months, at about $2,928 a month.
- **Deployable as tested:** the guard keeps every trade inside the 5% daily and 10% total limits (the account freezes
  rather than breaches). The installer cap is 0.5% already, so the tested setting is the shipped setting.
- **Runner-up for more income, if breach risk is acceptable:** Current 14 + ORB 0.5R unguarded at 0.5%.
  - 76% pass (66% history), $3,618 a month.
  - But 4% challenge breach and 45% funded breach within 3 years. It is unguarded.
- **Why not the Full EA portfolio:**
  - **Weaker in real history:** its MC numbers look strong, but replaying the actual history order gives 53% pass and a
    median funded life of 283 days, with 59% breached in year 1. Income is about $1,378 a month.
  - **Closed-balance-only check:** its headline uses that check, which flatters it against the others. With open trades
    at their stops it almost never passes.
  - **No hard limit on open risk:** it runs 32–36 EAs with a median of 6 trades open, including no-stop hourly bots and
    news straddles. Nothing stops their open risk from exceeding FTMO's 5% daily limit.
  - **News results not credible:** its news EAs show implausible +7R averages.
- **Avoid 0.75% and 1% funded risk on every portfolio:** accounts end in months, by freeze or breach.
