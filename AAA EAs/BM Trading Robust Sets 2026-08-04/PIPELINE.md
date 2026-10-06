# Calyx EA pipeline — canonical definition

Amended **2026-10-06 (user): final out-of-sample (OOS) is always the last TWO calendar years**
ending at the frozen study end-exclusive date (normally through yesterday, UTC). All development and finalist
selection must finish before that two-year window. Never shorten it to 6/12 months because data or trades are scarce.
Shared date planner: `AAA EAs/Calyx Research Pipeline/data_split.py`.

Amended 2026-09-26 at the user's instruction: stage 5 (optimization) is a **full parameter search** over every dimension
we can think of — timeframe, entry model, exit model, stop type (static vs trailing variants), risk:reward 0.5–6R,
trading session (Asia / London / New York / London–NY overlap / all), direction, filters and trade management — and the
**best version must then go through Monte Carlo simulation** before promotion.

This file supersedes the short list in `CLAUDE_CODE_ONBOARDING.md` §9 where they differ. Thresholds live in
`AAA EAs/Calyx Research Pipeline/pipeline-policy.json`; the stage-5 search space lives in `OPTIMIZATION SEARCH SPACE.json`
(next to this file). Existing tools are reused: study runners (`run_*.py` pattern: isolated tester, report/input
checks, port-3000 wait, gzip evidence), `calyx_pipeline.py` (bootstrap, deflated Sharpe, cost stress), and the FTMO
simulators in `FTMO Portfolio Pass Simulation 2026-09-24/`.

Standing rules for every stage: isolated tester `_Backtests/MT5-DMC-20260811` only (never the live terminal or Ava),
one tester at a time, rules/gates written before results, every tried configuration counted, native MT5 / ledger
overlay / Monte Carlo reported as different evidence types, every results table shows trades, trades per month and per
trading day, return, PF, win rate, max equity DD and win/loss streaks.

---

## Stage 1 — Rules first
Extract explicit rules from the source (video, paper, user idea). Fill gaps with stated defaults marked "(ours)".
Choose a **control** (same trade without the signal: random entries, any candle, random symbols) and the **gate**.
Freeze in `run-config.json` before any test.

## Stage 2 — Research EA
Build in a dated research folder with the shared sizing helpers (1% risk, lots rounded up). Compile 0 errors /
0 warnings; smoke test one short window and read the trades. Improvements to live EAs are added as **default-off
switches** and must pass **parity** (switches off = production, trade for trade).

## Stage 3 — Raw native test (no tuning)
6m / 1y / 3y / 5y windows (website windows). Fast screen = Model 1 on 3y/5y; confirmation = Model 4 real ticks with
150 ms delay and broker costs on every period. The runner checks EA/symbol/dates/inputs in each report and journal flags.

## Stage 4 — Raw gate
Positive and PF ≥ 1.15 on 3y and 5y, ≥ 30 trades, better than the control. **FAIL → stop** (no optimizing a loser).
PASS or near-miss with a clear reason → report and ask the user whether to run stage 5.

---

## Stage 5 — Optimization (full parameter search) — needs user approval

Goal: find the best settings for the strategy, choosing a **stable plateau**, not the single highest backtest.

### 5.1 Data split (fixed before searching)
- **Final OOS / holdout: last TWO calendar years**, `[study_end - 2 calendar years, study_end)`. Freeze the
  exact end date before searching; use a calendar anniversary, not 730 trading/calendar days. The default end date
  is start of today UTC (through yesterday). Data freshness/coverage is checked against this requested window;
  a stale broker feed does not silently move the end date backwards. An explicitly requested historical study may
  use its stated historical end date.
- **Validation**: the 12 months immediately BEFORE OOS; use only this older period to rank finalists.
- **Development**: the available history BEFORE validation; all parameter searches/plateau checks occur here.
  Training/validation and OOS must be chronological and non-overlapping. A five-year history therefore splits into
  two development years, one validation year, two final OOS years. Use more older history if necessary.
- Example for a study ending **2026-10-06 exclusive**: OOS **2024-10-06 → 2026-10-06**; validation
  **2023-10-06 → 2024-10-06**; development ends **2023-10-06**.
- Evaluate the final frozen candidate **once** on the two-year OOS. If it fails, reject it; no re-tuning or choosing
  a different finalist using OOS results. Last-year/6m/3m tables are diagnostic subwindows of this OOS, not selection
  windows. Any additional unused earlier history is a separate stress test, not a replacement for the two-year OOS.
- If coverage or the older development/validation sample is insufficient, report **insufficient evidence**;
  obtain more data or stop. Do not relax sample gates or shrink OOS to manufacture a pass.
- Prior raw tests/reviews may already have exposed the last two years. Keep the same required dates but label the
  final check **retrospective OOS, previously inspected**, not genuinely untouched. Preserve dated historical
  reports/protocols; do not retroactively relabel their shorter holdouts as compliant two-year results. In-flight
  studies using old dates require a new frozen split/revision, not silently overwritten evidence.
- Record all three boundaries and selection provenance in `data-split.json` / `run-config.json`. Warm-up bars and
  rolling indicators may use causal past observations; fitted parameters/thresholds must not use future OOS data.

### 5.2 Search dimensions (see `OPTIMIZATION SEARCH SPACE.json` for exact values)
| Dimension | What is compared |
|---|---|
| Timeframe | M1, M3, M5, M15, M30, H1, H4, D1 (whichever the logic allows) |
| Entry model | market on signal close, next-bar open, limit retest (fixed/ATR offset), stop-entry breakout, confirmation candle |
| Stop type | static: fixed price/points, ATR multiple, % of price, signal-candle / swing extreme, range/structure level |
| Stop management | none, breakeven at X R, **trailing**: ATR trail, % trail, MA trail, swing/structure trail, chandelier, step/lock (e.g. dynamic 50-20) |
| Take profit / exit | fixed R **0.5, 0.75, 1, 1.25, 1.5, 2, 2.5, 3, 4, 5, 6**, no target + trail, next level, time exit, end of session/day, partial close (e.g. 50% at 1R + trail) |
| Session | Asia, London, New York, London–NY overlap, NY open only, all hours; plus day-of-week exclusions |
| Direction | long only, short only, both |
| Filters | trend (EMA/SMA slope, higher-timeframe bias), ADX strength, DI agreement, volatility regime (ATR percentile), news blackout, spread cap |
| Trade management | max trades/day, one position vs pyramiding, re-entry after stop, max holding time, flat at session end vs hold overnight/weekend |
| Symbols | the requested assets + transfer to related ones (e.g. XAU/XAG, USTEC/US500/US30, BTC/ETH) |
| Risk model | fixed 1%, reduced risk, adaptive portfolio controls (reported separately; risk never "optimizes" the edge) |

### 5.3 Search procedure
1. **Staged search** (default, matches `pipeline-policy.json` one-factor-at-a-time): timeframe → entry model → stop
   type → stop management (static vs trailing variants) → RR / exit → session → direction → filters → management.
   Keep the top 3 at each stage; carry them forward.
2. **Joint neighbourhood check** around the finalists (small grid over the 2–3 most sensitive parameters) to confirm a
   plateau: neighbours must stay profitable; a lone spike is rejected.
3. Rank on development PF and return/drawdown, with minimum trade counts; never on return alone.
4. **Count every configuration tried** (for the deflated Sharpe) and keep every result in `SEARCH RESULTS.json`.
5. Older pre-OOS validation picks one final version; the **last-two-year OOS** confirms it **once**.

### 5.4 Stage-5 outputs
Side-by-side tables per dimension (e.g. trailing vs static stop, 0.5R…6R, Asia vs London vs NY vs overlap), the
plateau chart, the frozen final SET, holdout result, and the list of rejected alternatives.

---

## Stage 6 — Monte Carlo on the best version — mandatory before promotion
Run on the frozen final version's **native Model 4 trades** (development + validation + holdout):
- **Block bootstrap** (10,000 paths, block length 5 — policy): distribution of return, PF, max DD; require return p05 > 0
  and PF p05 > 1 (policy thresholds).
- **Trade-order reshuffle**: distribution of max drawdown and longest losing streak.
- **Random trade removal** (skip 10–20% of trades): robustness to missed fills.
- **Cost stress**: measured extra spread/slippage per trade (never invented) — must stay profitable.
- **Prop-firm simulation** (FTMO rules): pass probability for phase 1/2, breach probability, days to pass, at the
  chosen risk — using the existing FTMO simulators; equity-path caveats stated.
- **Portfolio overlap**: correlation with and marginal effect on the current portfolio.
Tool: `calyx_pipeline.py --tested-configurations <count from 5.3>` plus the FTMO simulators.

## Stage 7 — Production build (needs approval)
Production EA + SET, parity (production = research final), hashes; installer item behind a new BAT option first;
`-ValidateOnly` dry run on no terminal.

## Stage 8 — Website & portfolio evidence (needs approval)
Evidence cache for 6m/1y/3y/5y, new website mode/graph, portfolio rebuild + consistency audit, tests. The owner
restarts/redeploys the site.

## Stage 9 — Go live (user)
The user runs the BAT on MT5. Claude never attaches EAs, replaces SETs, restarts MT5 or trades. Update `CLAUDE.md` /
handoff with date, artifacts and limitations; push to GitHub only when asked.
