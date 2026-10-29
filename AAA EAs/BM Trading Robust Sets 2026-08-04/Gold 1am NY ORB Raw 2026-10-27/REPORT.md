# Gold 1am New York ORB raw study 2026-10-27 — REJECTED at the raw gate

**Owner request:** "try this on gold". The clip is a Pine prompt for MGC1! (micro gold futures):
- 01:00–01:15 NY range;
- 5m close beyond it 01:15–03:40;
- stop at the opposite edge;
- 0.5R target;
- 2 trades a day, reverse on an opposite breakout;
- force close 06:00.

**Rules:** frozen in `RULES.md`. The clip's 6 "regime filters" are undefined and were not tested.

**Runs:** 16 native Model-4 runs on Exness XAUUSD M5, 150 ms, $10,000, 1% risk (lots rounded up, 2-lot cap), end
2026-10-27. Full tables are in `RESULTS.md`, the chart in `balance.png`.

## Result
| Window | Trades | / month | / day | Return | PF | Win % | Equity DD | Mean R |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 6m | 192 | 31.9 | 1.47 | +3.4% | 1.05 | 68% | 11.5% | +0.02 |
| 1y | 363 | 30.3 | 1.39 | +11.6% | 1.09 | 69% | 13.7% | +0.03 |
| 3y | 1,121 | 31.1 | 1.43 | −10.7% | 0.97 | 67% | 26.3% | −0.01 |
| **5y** | **1,940** | 32.3 | 1.49 | **−72.9%** | **0.76** | 64% | **78.6%** | −0.06 |

- **By year:** 2022 −56.7% and 2023 −38.0%; only 2025 (+5%) and 2026 (+6%) were positive.
- **Win rate vs payoff:** about 68% of trades win, but at 0.5R a win pays half a loss, so the win rate needs to be about
  67% just to break even. Spread and swap push it below that.
- **Long vs short:** both lose over 5y (longs −$4,307, shorts −$2,978).
- **Random-direction control:** PF 0.65 over 5y, mean R −0.106. The breakout direction does beat random, but not by
  enough to make money.
- **Sensitivities (declared, not used to pick):**
  - 1R target: 3y +53.5%, PF 1.09, but 5y −54%.
  - 2R target: 3y +125%, PF 1.14, but 5y −27.5%.
  - Both are positive only in 2024–26 and below the PF 1.15 gate.
  - No-reverse is identical to the main version: the reverse never triggered, because the stop sits at the range edge.
- **Raw gate: FAIL.** 3y and 5y lose, PF is below 1.15, and the version is negative without its 5 best days.
  **No optimisation.**

## Disclosures
- **Instrument:** XAUUSD CFD stands in for MGC futures. The underlying is the same, but costs differ (spread and swap
  vs futures commission).
- **Risk sizing:** 1% of equity instead of the clip's fixed $350.
- **Ticks:** real from 2026-01-01; earlier ticks are generated.
- **Control mismatch:** random-direction controls trade more often (≈2,570 vs 1,940 over 5y), because random
  positions face opposite "breakouts" and reverse. The comparison uses PF and mean R.
- **Exit-column label:** the "24h" exit column counts the 06:00 NY force closes.

Nothing installed, deployed or pushed.

## Addendum 1 — volatility filter (EXPLORATORY, owner: "what if we add volatility filter?")
- **Setup:** 5 filters declared before testing (RULES.md Addendum 1) × 0.5R / 2R = 10 native 5y runs. Data: `VOLFILTER.json`.
- **Parity:** with the filter OFF, v1.10 reproduces raw ORB05 exactly (0 mismatches over 1,940 trades).
- **Split:** each 5y ledger is split by close time into development 2021-10 → 2023-10 (choice), validation 2023-10 →
  2024-10 and OOS 2024-10 → 2026-10. Validation and OOS were viewed in the raw run.

| Version (5y trades) | 5y return | 5y PF | Dev trades (/month) | Dev PF | Val PF | OOS PF |
|---|---:|---:|---:|---:|---:|---:|
| No filter 0.5R (1,940) | −72.9% | 0.76 | 819 (34.2) | 0.64 | 0.86 | 1.03 |
| Range ≥ 0.10 ATR, 0.5R (461) | −6.1% | 0.96 | 139 (5.8) | 0.76 | 0.87 | 1.13 |
| Range ≥ 0.10 ATR, 2R (461) | +6.7% | 1.03 | 139 (5.8) | 0.81 | 1.16 | 1.12 |
| Range ≥ 0.15 ATR, 0.5R (113) | +12.1% | 1.37 | 24 (1.0) | 1.44 | 0.83 | 1.47 |
| Range ≥ 0.15 ATR, 2R (113) | +27.1% | 1.53 | 24 (1.0) | 1.02 | 1.53 | 1.71 |
| Range ≤ 0.10 ATR, 0.5R (1,479) | −71.2% | 0.73 | 680 (28.4) | 0.62 | 0.86 | 0.99 |
| Range ≤ 0.10 ATR, 2R (1,479) | −34.8% | 0.93 | 680 (28.4) | 0.78 | 1.01 | 1.21 |
| High-vol regime, 0.5R (894) | −39.2% | 0.83 | 344 (14.3) | 0.70 | 0.67 | 1.14 |
| High-vol regime, 2R (894) | +37.5% | 1.07 | 344 (14.3) | 0.88 | 0.97 | 1.33 |
| Low-vol regime, 0.5R (1,046) | −56.0% | 0.77 | 475 (19.8) | 0.61 | 1.10 | 0.93 |
| Low-vol regime, 2R (1,046) | −49.9% | 0.87 | 475 (19.8) | 0.72 | 1.11 | 1.03 |

- **Declared pick:** best development PF with ≥ 100 development trades is the high-vol regime at 2R (dev PF 0.88,
  i.e. losing). Validation PF 0.97 → **FAIL**. Every eligible filter lost in development.
- **Wide-range filter (range ≥ 0.15 × daily ATR):** looks best over 5y (2R: +27.1%, PF 1.53, equity DD 6.5%), but:
  - it has only 113 trades in 5 years (1.9 / month) and only 24 in development, so it was not eligible under the rule
    fixed before the test;
  - 78 of its 113 trades fall in 2024–26;
  - at 0.5R it lost in validation (PF 0.83);
  - it was chosen after looking at results.

  It is a lead to test later on new data, not a qualified strategy.

**Verdict unchanged:** REJECTED. No optimisation of the base strategy.
