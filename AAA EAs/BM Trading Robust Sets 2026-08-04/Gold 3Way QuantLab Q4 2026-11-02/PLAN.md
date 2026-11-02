# 3 Way Gold vs QuantLab "XAUUSD 3x Speed Q4 Turn": plan (frozen 2026-11-02, before any result)

**Owner request:** "try the same with gold 3 way" (as for Nasdaq 5M). The target profile is QuantLab's public page:
- XAUUSD H1, three rules: "Speed Switch (H4) — momentum that adapts", "Q4 breakout (H1) — the year-end move", "Turn of the month (H1)";
- one account, one risk budget, 0.75% per trade;
- +210.1% since 2019, win 44.8%, PF 1.26, DD −14.09%, 1,309 trades (3.2 / week), worst day −2.98%, longest dry spell 48.2 weeks;
- 74% of trades held overnight, 33% over a weekend.

Their rule details are behind a subscription, so only the structure is used.

**Our 3 Way Gold:**
- A: H4 momentum (matches "Speed Switch (H4)").
- B: M15 Donchian breakout all year (QuantLab: **H1, Q4 only**).
- C: turn of month.

The only structural gap is B's season and timeframe.

## Variants (inputs only, research copy; production EA untouched)
| Id | Breakout module |
|---|---|
| G0 | production: all year, M15 |
| G1 | Q4 only (Oct–Dec), M15 |
| G2 | Q4 only, H1 (bar lengths scaled ×15/60, so the time span is the same) |
| G3 | all year, H1 |
| G4 | breakout OFF |

A and C are unchanged in every variant. Risk is 0.75% per module trade.

**Parity first:** the research copy with default inputs (G0) must reproduce the production EX5's trades over the last year exactly.

## Data and split (native MT5 Model 4, XAUUSD Exness CFD, $10k, 150 ms; entries from 2019-06-01 after warm-up)
| Part | Dates |
|---|---|
| Development | 2019-06-01 → 2023-11-01 |
| Validation | 2023-11-01 → 2024-11-01 |
| OOS | 2024-11-01 → 2026-11-01 (last two years) |

**Nothing here is untouched.** 3 Way Gold's settings were optimised on 2021-09 → 2026-09, and its untouched holdout (2019–2021) lost. 2019-06 → 2021-09 is the only part not used to fit A / B / C.

## Choice
- **Pick:** the variant with the best development return ÷ closed DD, with PF ≥ 1.15 and ≥ 200 trades.
- **Validation:** must be positive.
- **OOS:** reported once.
- **Monte Carlo:** 4-week block bootstrap, 2,000 × 1 year, on the pick and on G0.
