# EURUSD 8am swing low — full pipeline (EXPLORATORY OVERRIDE) — plan, frozen 2026-10-21 before any search result

**Why an override:** the raw study (`EURUSD 8am Swing Low Raw 2026-10-21`) FAILED the raw gate for both sessions.
PIPELINE.md stage 4 says "no optimizing a loser". The owner explicitly asked (2026-10-21) to "run full pipeline on both
session and find the best approach", so this runs as a labelled exploratory override, like the 2026-09-29 Nasdaq H1 and
2026-09-30 Gold Trio searches. Any result carries that label. Research only: isolated tester, nothing deployed.

## Data split (data_split.py rules, frozen)
- Study end **2026-10-17 exclusive** (same as the raw study).
- **OOS** 2024-10-17 → 2026-10-17. Retrospective: already seen in the raw test. Used ONCE for the frozen finalist per session.
- **Validation** 2023-10-17 → 2024-10-17. Also seen in the raw test. Finalist choice only.
- **Development** 2016-10-17 → 2023-10-17, 7 years. 2016-10-17 → 2021-10-17 has never been viewed. All searching and
  plateau checks happen here.

## Two tracks
London (08:00 London clock) and New York (08:00 New York clock), searched separately. The start is the raw main
version: H1 2-bar fractal low confirmed at the anchor, long, market entry, stop at pivot − 0.1 ATR (floor 0.5 ATR),
no target, 4 h time exit.

## Staged search (development, native MT5 Model 1 fast screen, 150 ms, $10k, 1%). Top 3 carried forward per stage
1. **Swing definition and timeframe:** TF M15 / M30 / H1 × fractal 1 / 2 / 3 × freshness window 1 / 2 / 4 / 6 bars × lower-low off/on.
2. **Entry:** market; limit 0.25 / 0.5 ATR below (2 h expiry); stop-entry above the last closed swing-TF bar (2 h expiry).
3. **Stop:** pivot − 0 / 0.1 / 0.25 / 0.5 ATR (floor 0.5 ATR); ATR 0.5 / 1 / 1.5 / 2 / 3 from entry.
4. **Stop management:** none; break-even at 0.5 / 1 / 1.5 R; ATR trail 1 / 2 ATR from 0.5 / 1 R.
5. **Exit:**
   - Time exit 1 / 2 / 3 / 4 / 6 / 8 h, or session end (16:30 London / 17:00 New York), no target.
   - Fixed target 0.5 / 0.75 / 1 / 1.25 / 1.5 / 2 / 2.5 / 3 / 4 / 5 / 6 R, each with an 8 h cap and with a session-end cap.
6. **Session anchor:** 07:00 / 07:30 / 08:00 / 08:30 / 09:00 / 09:30 local, on that track's clock.
7. **Direction:** long after a fresh low; short after a fresh high; both.
8. **Filters, one at a time:**
   - Trend: H1 close vs EMA200; EMA50 slope over 5 H1 bars; D1 close vs D1 EMA20.
   - ADX(14, H1) ≥ 20 / 25.
   - ATR(14, H1) regime: above / below its 100-bar median.
   - Skip Monday / Friday / both.

**Ranking (development):**
- Eligible: ≥ 60 trades, net > 0, PF ≥ 1.05.
- Rank by return ÷ balance drawdown; ties broken by PF.
- If fewer than 3 are eligible, the stage carries the best PF configurations with ≥ 60 trades, labelled "not profitable".

Every configuration is counted and kept (SEARCH RESULTS.json).

## Plateau, validation, OOS, Monte Carlo
- **Plateau:** a joint grid around each of the 3 final configurations, ±1 step on (freshness window, exit, anchor ±30 min),
  27 configs. It passes if ≥ 70% of neighbours have net > 0 AND median PF ≥ 1.05. Lone spikes are rejected.
- **Confirmation:** plateau survivors are re-run natively at **Model 4** on development and validation.
  Validation picks one per track: highest validation PF with ≥ 15 trades and net > 0. If none qualifies, the track is
  rejected at validation.
- **OOS once (Model 4):**
  - Pass requires net > 0, PF ≥ 1.15, ≥ 30 trades, recent-half PF > 1, and no flip without the best day or best trade.
  - A failure is final: no re-tuning, and no switching to another finalist.
- **Stage 6 (only for an OOS pass):**
  - Block bootstrap: 10,000 paths, block length 5; return p05 > 0 and PF p05 > 1.
  - Deflated Sharpe using the full tested-configuration count.
  - Trade-order reshuffle; 10–20% random trade removal; cost stress.
- **Parity gate before searching:** the engine must reproduce the raw study's native Model 4 5y ledgers for L8, NY8 and
  SHORT_NY8 (same entries, exits and cash).

Every table shows trades, trades/month and trades/day.
