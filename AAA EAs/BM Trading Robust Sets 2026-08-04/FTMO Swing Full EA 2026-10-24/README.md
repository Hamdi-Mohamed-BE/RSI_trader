# FTMO Swing — Full EA portfolio · Recommended Adaptive (2026-10-24)

Research only: Python/numba replay of frozen ledgers. In-sample. Nothing installed and no account touched.
Method: `PLAN.md` (+ Addendum 1). Full tables: `RESULTS.md`. Raw numbers: `RESULTS.json`.

## What was simulated
- **Stream:** the website's Full EA stream (`Portfolio Long History All ORB05 2026-10-14`, `full-eas`).
  - 36 of 37 members (Gold News V9 has no ledger).
  - 22,117 positions, 2021-10 → 2026-10.
  - About 10–12 trades per calendar day, a median of 6 open at once and up to 15.
- **Sizing:** exactly the website's Recommended Adaptive replay.
  - Parity: to the cent on 3 one-year windows (`PARITY.json`).
  - Tapers at 4% / 7% drawdown and after 3 / 5 losses; Nasdaq ×0.25.
  - News at 0.75 × risk per order.
- **FTMO Swing 2-step:**
  - Phase 1 +10%, phase 2 +5%; 5% daily loss (Prague midnight) and 10% max loss.
  - Funded: 80% of the profit withdrawn every 14 days.
- **Two breach models, because the ledger has no floating equity:**
  - Optimistic: closed balance only.
  - Pessimistic: every open trade at its full stop at once.
  - Reality is in between, probably much nearer the optimistic one, since all open trades rarely stop out together.
- **Two variants:**
  - **NO_NEWS (headline):** the four News Pulse EAs removed.
  - **ALL36:** everything.
  - The News Pulse BTC / EURUSD ledgers average about +7R per trade, with single trades up to +86R / +110R. Those are
    tester news-spike fills on generated ticks with fitted presets, so ALL36 is not credible for sizing.

## Headline — NO_NEWS, optimistic model (MC / history)

| Risk | Phase 1 pass | Phase 2 pass (given phase 1) | Funded | Median days to funded | Funded breach ≤ 1 y / 3 y | Median days funded alive MC / hist | Monthly income 10k / 20k / 50k / 100k (median) | Trades / day |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.50% | 92% / 72% | 95% / 91% | 86% / 66% | 107 / 94 | 26% / 60% | 829 / 283 | $395 / $790 / $1,976 / $3,952 | 10–12 |
| 0.75% | 76% / 66% | 83% / 77% | 63% / 50% | 75 / 76 | 89% / 100% | 107 / 101 | $391 / $781 / $1,953 / $3,906 | 10–12 |
| 1.00% | 60% / 54% | 68% / 59% | 41% / 32% | 56 / 48 | 100% / 100% | 33 / 36 | $106 / $212 / $529 / $1,058 | 9–12 |

Pessimistic model (every open trade at its stop):
- Funded only 8% / 1% / 1% at 0.5% / 0.75% / 1%.
- The funded account breaches within about 1–16 days.

The gap between the two models is the concurrency risk. At 0.5% risk, 9 open trades already put 4.5% at stop against
a 5% daily limit.

## Reading it
- **0.5% is the only setting that survives funded for long.** The median MC path is alive 829 days, paying about $395
  per month per $10k.
  - The history starts are much worse: a median of 283 days alive.
  - 60% of funded MC paths breach within 3 years.
- **0.75% and 1% pass faster but breach the funded account fast.** At 0.75%, 89% breach within a year. At 1%, every
  path breaches within a year (median 33 days).
- **The 14-day withdrawal resets the balance to the start.** The account never builds a cushion, so the funded account
  is harder to keep than the challenge was to pass.
- **20k is not an FTMO size** (FTMO offers 10k / 25k / 50k / 100k / 200k). Values are a linear ×2.
- **Not modelled:**
  - Leverage 1:30 margin limits.
  - The real Calyx lot rounding (up to the minimum lot); fractional lots are used.
  - Spread and slippage beyond the ledgers.
  - The challenge fee.
- **In-sample:** EA settings were chosen on this history, and ticks before 2026 are generated.
- **Rules:** check FTMO's current Swing rules before buying.
