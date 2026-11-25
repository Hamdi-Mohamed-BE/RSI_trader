# Noise Band optimisation, stage 5 + 6 (frozen 2026-11-24, before any search result)

Owner 2026-11-24: "optimise the best results and run them on in and out of sample data and show results".
Raw study: `Noise Band Raw 2026-11-11/` (REPORT.md). Survivors of the raw gate: USTEC WIDE and US500 WIDE. The best mix was B: Nasdaq + S&P, with no DAX.
DE30 failed the raw gate, so it is NOT optimised (pipeline: no optimising a loser). It is shown only as a transfer diagnostic for the final setting.

## Data split (data_split.py, study end 2026-11-21 exclusive = tester data end)
- **Development:** 2019-07-16 -> 2023-11-21. All searches and plateau checks happen here.
- **Validation:** 2023-11-21 -> 2024-11-21. Ranks the finalists (top 3 from development) and picks ONE.
- **OOS:** 2024-11-21 -> 2026-11-21 (last two calendar years). The frozen pick is evaluated ONCE.
  - Label: RETROSPECTIVE, PREVIOUSLY INSPECTED. The raw study already showed these years, and QuantLab chose k 1.4 on them.
- **Walk-forward (stage 5.6):** robustness.rolling_folds, 3 y train / 1 y test, inside 2019-07-16 -> 2024-11-21 only; 2,000 blind runs; gate p <= 0.10 and chained total > 0.

## Engine (search tool) and parity
- Python / numba replay on the exported Exness M1 bars (`Noise Band Raw 2026-11-11/bars/`, bid OHLC + bar spread).
  - Checkpoint bars and ATR(14, SMA of true range = MT5 iATR) are built from M1 on the chosen timeframe.
  - Entry at the next bar open (ask for buys). The stop is checked before trail / target inside each M1 bar (conservative).
  - Commission per lot taken from the native ledgers.
- Parity before any search: the engine's WIDE and PAPER on USTEC and US500 must match the native Model 4 ledgers. Gates:
  - Same entry day + direction on >= 95% of native trades.
  - Total R within 15% (or 10 R) of native.
- Native MT5 confirms the final version (Model 4, EA updated only by default-off inputs; parity of the EA defaults = v1.10).

## Search (staged, top 3 carried per stage, every configuration counted in SEARCH_RESULTS.json)
Shared parameters for USTEC + US500 (one setting for both, 1 R each). Scored on the combined development ledger; per-asset results are reported.

| Stage | Dimension | Values |
|---|---|---|
| 1 | Checkpoint timeframe | M15, M30, H1 |
| 2 | Band (entry model) | QuantLab: k x sqrt(K) x ATR14, k 0.6 / 0.8 / 1.0 / 1.2 / 1.4 / 1.6 / 1.8 / 2.0 / 2.4. Paper: sigma band (14-day mean of \|close / open - 1\| at that time of day) x m, m 0.8 / 1.0 / 1.2 / 1.5 |
| 3 | Entry confirmation | next bar open (raw); 2 consecutive closes beyond the band |
| 4 | Initial stop | ATR x 0.75 / 1 / 1.5 / 2 / 2.5 / 3; band edge (paper) |
| 5 | Stop management | none; breakeven at 0.5 / 1 R; ATR trail 1 / 1.5 / 2 / 3 ATR from +0.5 / 1 / 1.5 / 2 R |
| 6 | Target / exit | none (flat at the close); 0.5 / 0.75 / 1 / 1.25 / 1.5 / 2 / 2.5 / 3 / 4 / 5 / 6 R; time exit after 2 h / 4 h |
| 7 | Session | first check at open + 30 / 60 min; last check 11:00 / 12:00 / 13:00 / 15:00 NY; flat 15:55 / 15:00 NY |
| 8 | Direction | both / long only / short only |
| 9 | Filters | none; daily trend (yesterday's close vs SMA20 of daily closes: trade only with it); volatility regime (ATR14 D1 above / below its 100-day median); skip Monday; skip Friday |
| 10 | Management | max 1 / 2 trades a day (re-entry after an exit at the next checkpoint) |

- **Score:** development PF and R / closed DD, with combined dev trades >= 300 and each asset >= 100.
  - Ranking = mean of the PF rank and the R/DD rank. Never return alone.
- **Plateau:** each finalist's one-step neighbours (every dimension, one value either side).
  - >= 70% must be profitable in development; neighbour median PF >= 1.05.
- **Validation pick:** the best finalist by validation R / DD among those with validation total > 0 and PF >= 1.10.
  - If none qualifies: REJECTED_AT_VALIDATION, and the raw WIDE stays.
- **OOS (once):** the pick must be positive with PF >= 1.10 to pass. It is compared side by side with the raw WIDE on every window.

## Stage 6 on the final (native Model 4 ledgers, 2019-07-16 -> 2026-11-21)
- Three-way MC (1,000 runs, seed 20261104), block bootstrap, and cost stress 1x / 2x / 3x.
- Random-entry control (200 copies).
- Best-day dependence.
- Buy & hold per window.
- Deflated Sharpe with the configuration count.
- FTMO sim only if it passes.

## Risk / sizing
1% of balance per trade per asset (raw convention). The mix weights (B) are reported as a replay, not optimised.
