# Noise Band optimisation (stage 5): REJECTED_AT_VALIDATION; keep the raw WIDE (2026-11-24)

The plan was frozen before the search (PLAN.md). Assets: USTEC + US500 together, one shared setting, 1 R each. DE30 was not optimised (it failed the raw gate).

## Split

| Window | Dates | Use |
|---|---|---|
| Development | 2019-07-16 → 2023-11-21 | the search |
| Validation | 2023-11-21 → 2024-11-21 | picks one finalist |
| OOS | 2024-11-21 → 2026-11-21 | final check, once (RETROSPECTIVE: these years were already seen in the raw study, and QuantLab chose k 1.4 on them) |

## Engine

- Numba replay on Exness M1 bars.
- Parity with the native Model 4 ledgers (PARITY.json): the same day and direction on 99.7-99.8% of trades, per-trade correlation 0.994-0.999.
- After a fill-cost calibration on WIDE (USTEC +0.44 pt, US500 +0.13 pt per trade), total R matched native within 3%. It was checked on PAPER: USTEC 39.0 vs 38.0 R, US500 -41.7 vs -44.3 R.

## Search

- 10 stages, top 3 carried forward: timeframe, band (QuantLab k √K ATR and the paper's sigma band), confirmation, stop, stop management, target / time exit, session, direction, filters, trades a day.
- 252 settings in the search + 42 plateau neighbours = 294 configurations (SEARCH_RESULTS.json).
- All three finalists come from one family: M15 checkpoints, k 2.0, 2 ATR stop, breakeven at +1 R, no trailing stop, 6 R target, flat 15:55 NY.
  - Finalist 2 adds: last check 11:00 NY and skip Monday.
  - Finalist 3 adds: skip Monday.
- The plateau check PASSED for all three (17 neighbours, 100% profitable, median PF 1.50-1.52).

## Decision (frozen rules)

**Validation:** all three finalists LOST.
- Finalist 1: −10.8 R, PF 0.80.
- Finalist 2: −2.9 R, PF 0.92.
- Finalist 3: −6.2 R, PF 0.85.
- The raw WIDE made +43.5 R (PF 1.35) in the same year.

**Walk-forward** (3 y train / 1 y test, 3 folds, 2,000 blind runs): chained test +5.9 R over 307 trades, t 0.28, p 0.84. FAIL: the search does not beat random picks.

→ **REJECTED_AT_VALIDATION. The raw WIDE stays.** There was no OOS selection and no stage 6 for a new version. The raw WIDE already had MC / controls in the raw study.

## All windows (engine replay, R = 1% risk units, USTEC + US500 together; trades per day = per month / 21.7)

**OOS columns of the finalists are DIAGNOSTIC ONLY.** They were computed after the decision.

| Version | Window | Trades | /month | /day | R | PF | Win % | Closed DD (R) |
|---|---|---|---|---|---|---|---|---|
| **Raw WIDE** (M30, k1.4, 2 ATR stop, 2 ATR trail from +1 R) | Dev | 1,282 | 24.6 | 1.13 | +71.4 | 1.12 | 51.0 | 29.3 |
| | Val | 291 | 24.2 | 1.12 | **+43.5** | 1.35 | 55.7 | 18.1 |
| | OOS | 605 | 25.2 | 1.16 | **+96.1** | 1.42 | 57.2 | 17.2 |
| | Last 12 m | 297 | 24.8 | 1.14 | +52.3 | 1.46 | 55.6 | 15.7 |
| | All | 2,178 | 24.7 | 1.14 | +211.0 | 1.22 | 53.4 | 43.4 |
| Finalist 1 (M15, k2.0, BE 1 R, 6 R target) | Dev | 510 | 9.8 | 0.45 | +133.2 | 1.60 | 32.4 | 19.6 |
| | Val | 109 | 9.1 | 0.42 | **−10.8** | 0.80 | 20.2 | 23.9 |
| | OOS (diag.) | 247 | 10.3 | 0.47 | +58.9 | 1.57 | 35.2 | 19.8 |
| | Last 12 m | 123 | 10.3 | 0.47 | +27.8 | 1.46 | 35.0 | 19.8 |
| | All | 866 | 9.8 | 0.45 | +181.3 | 1.48 | 31.6 | 23.9 |
| Finalist 2 (+ last check 11:00, skip Mon) | Dev / Val / OOS / All | 378 / 81 / 176 / 635 | 7.2 | 0.33 | +98.5 / **−2.9** / +34.0 / +129.6 | 1.60 / 0.92 / 1.43 / 1.47 | ~30 | 16.2 / 19.7 / 16.8 / 21.7 |
| Finalist 3 (+ skip Mon) | Dev / Val / OOS / All | 399 / 90 / 188 / 677 | 7.6 | 0.35 | +101.6 / **−6.2** / +37.6 / +133.0 | 1.60 / 0.85 / 1.45 / 1.46 | ~31 | 17.2 / 20.0 / 17.7 / 21.7 |

## Per asset, R (PF)

| Version | Asset | Dev | Val | OOS | All |
|---|---|---|---|---|---|
| Raw WIDE | USTEC | +41.8 (1.14) | +24.3 (1.37) | +43.0 (1.35) | +109.0 (1.22) |
| Raw WIDE | US500 | +29.7 (1.10) | +19.3 (1.33) | +53.1 (1.50) | +102.0 (1.23) |
| Finalist 1 | USTEC | +86.3 (1.71) | −7.7 (0.77) | +28.4 (1.48) | +107.1 (1.50) |
| Finalist 1 | US500 | +46.8 (1.46) | −3.2 (0.84) | +30.5 (1.69) | +74.2 (1.45) |

## Calendar years, R (both assets)

| Version | 2019* | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026* |
|---|---|---|---|---|---|---|---|---|
| Raw WIDE | −11.8 | +9.6 | +40.8 | +43.8 | −15.1 | +64.2 | +36.1 | +43.5 |
| Finalist 1 | −14.1 | +22.8 | +58.8 | +48.8 | +16.1 | −5.0 | +21.5 | +32.3 |

\* partial year

## Reading

1. **The search found a version with a much higher development PF** (1.60 vs 1.12).
   - It wins less often (32%) but bigger (6 R target, breakeven at +1 R).
   - It failed the next year it had not seen (validation), and the walk-forward could not beat random picks (p 0.84).
   - So the improvement is development fitting, not a proven better rule.
2. **The diagnostic OOS of finalist 1 is positive** (+58.9 R, PF 1.57) but earns less than the raw WIDE (+96.1 R, PF 1.42) in the same years.
   - Over all years it trades less (9.8 vs 24.7 / month) with a smaller drawdown (23.9 vs 43.4 R).
   - It was 2024 that broke it.
   - Choosing it now would mean picking on the OOS, which the pipeline forbids. It would need an explicit owner override, labelled exploratory.
3. **The raw WIDE stays the version to use.**
   - Every window is positive except the partial 2019 and 2023.
   - Its MC, random-entry, cost and best-day checks passed in the raw study.
   - The US500 clumped-losses flag remains.

## Files

- PLAN.md, engine.py, parity.py (+PARITY.json), calib.py, search.py (SEARCH_RESULTS.json, FINAL.json), diag.py (DIAG.json).
- In-sample replay, not native MT5 runs of the finalists.
- No EA was changed, nothing was installed or pushed.
