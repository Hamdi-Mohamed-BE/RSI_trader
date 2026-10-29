# Small Account 90 Day Search 2026-10-23 — plan (written before any result)

**Owner request:** "run more deep simulation and find better approaches and what EAs to use to get there in 3 months
if possible (reach 10k in 3 months)". Start $100; target $10,000 within 90 calendar days.
Research only: Python replay of frozen native ledgers. No MT5 run, no live terminal, nothing installed.

Follows `Small Account Challenge 2026-10-23/` (2-year horizon). That study looked at all five years in aggregate, so
no period here is untouched (see Disclosures).

## Why this is hard (stated before the search)
100× in 90 days needs ln(100) = 4.6 of log growth.
- Per lane, full-Kelly growth per trade is about μ·k/2. Over the whole history the 19 FTMO17 lanes reach about
  0.0003–0.013 per trade.
- All lanes together give roughly 1.4 of log growth in 90 days at full Kelly, a median of about ×4.
- So reaching ×100 in 90 days needs overbetting plus luck. The search measures how often that luck came.

## Data and split
- **Lanes (20):**
  - The 19 FTMO17 lanes (`Portfolio Prop Comparison 2026-10-22/INPUTS-FTMO17.json`; 3 Way Gold as module lanes).
  - Nasdaq 5M **DI OFF** (`Best Prop Portfolio Retest 2026-10-20/INPUTS-DI_OFF.json`) as a 20th lane. It is mutually
    exclusive with Nasdaq 5M DI ON.
  - Net R per trade = (gross + commission + swap) / unit risk to the initial stop. End-censored trades are excluded.
- **Not included** (no stop-defined unit-risk stream exists, or the evidence is unverified):
  - US30/US100 hourly (no SL);
  - News Pulse straddles and Gold News V9;
  - BTC FVG / MonthEnd / VolumeConfirmed ORB (samples too small).
- **Split** (`SPLIT.json`, frozen with `Calyx Research Pipeline/data_split.py`):

  | Segment | Dates |
  |---|---|
  | Development | 2021-10-07 → 2023-10-06 |
  | Validation | 2023-10-06 → 2024-10-06 |
  | OOS | 2024-10-06 → 2026-10-06 |

  All search and ranking use development only. Validation chooses among the development top 20. OOS is run once on
  the chosen configuration, the development #1 and the fixed baselines.

## Simulation (identical across all configurations)
- **Account:**
  - Start $100.
  - Sizing on closed balance at entry: lots = f × balance ÷ (unit risk per lot), rounded DOWN to the lot step
    (`../Small Account Challenge 2026-10-23/SPECS.json`).
  - Below the minimum lot, use the minimum only if its risk is ≤ 3 × budget; otherwise skip.
  - Maximum lot from the specs.
  - One position per lane at a time, as in the source. Different lanes may overlap.
- **Booking:** P&L is booked at close. Balance is floored at 0.
- **Bust:** closed balance < $10.
- **Goal:** first close at or above $10,000 within 90 days. $1k and $5k are also recorded.
- **History starts:** every weekday (UTC midnight) whose 90-day window lies inside the segment. They overlap heavily:
  development holds only about 8 non-overlapping 90-day windows, validation 4 and OOS 8.
- **Monte Carlo:**
  - 2,000 paths per segment, seed 20261023.
  - Each path is 4 random 4-week blocks of that segment's real trades (Monday starts with the block inside the
    segment), shifted onto one timeline.
  - The same paths are used for every configuration (common random numbers).

## Search space (development)
- **Baskets:**
  1. Declared: NAS5M (DI ON), PR9 (9 lanes), FTMO17 (19 lanes), FTMO17 with DI OFF replacing DI ON, ORB5.
  2. Top-k: rank lanes by development Kelly growth per day (trades/day × μ × kelly / 2, with kelly = μ / E[R²], lanes
     with μ > 0 only), k ∈ {1, 2, 3, 4, 5, 6, 8, 10, 12, 15}.
  3. Greedy forward selection:
     - Each step adds the lane that most increases development MC P($10k ≤ 90 d).
     - Scored at the best of 16 policies: the 10 FIXED values plus DEADLINE k ∈ {2, 3, 4} × fmin 5% × fmax
       {30%, 50%}, no cap.
     - Stops when the gain is < 0.25 points or the basket has 12 lanes. Every step's basket enters the grid.
- **Sizing policies (46):**
  - FIXED f ∈ {3, 5, 7.5, 10, 12.5, 15, 20, 25, 30, 40}% of balance per trade.
  - KELLY: f_lane = c × kelly_lane (development), c ∈ {0.5, 0.75, 1, 1.5, 2, 3}, cap 40% per trade.
  - DEADLINE (goal-and-time aware): f = clip(k × ln(10,000 / balance) / days remaining, fmin, fmax),
    with k ∈ {1.5, 2, 3, 4, 6}, fmin ∈ {2%, 5%}, fmax ∈ {20%, 30%, 50%}. It bets more when behind schedule and less
    when ahead.
- **Open-risk cap (3):** none, 30% or 60% of balance in total stop risk across open trades. A new trade is cut to fit
  and skipped if it falls below the minimum lot.

## Selection and reporting rules
- **Development ranking:** MC P($10k ≤ 90 d); ties broken by lower bust, then higher P($5k ≤ 90 d).
- **Validation:** the development top 20 (distinct configurations) plus baselines are run on validation history and
  MC. **Chosen** = the highest validation MC P($10k ≤ 90 d); ties broken by development rank.
- **OOS:** run once for the chosen configuration, development #1 and the baselines (PR9 F05, FTMO17 F03, FTMO17 F10,
  FTMO17 F20). No changes after OOS.
- **Monte Carlo on the chosen configuration (mandatory):**
  - All-period 5,000 paths.
  - Stress: every trade −0.05 R of extra cost and winners −10%.
  - Horizons of 90, 180 and 365 days.
  - Reloads: re-deposit $100 after a bust, K ∈ {0, 1, 2, 4, 9}; report the money deposited per success.
- **Labels for P($10k ≤ 90 d):** ≥ 50% likely; 20–50% possible; 5–20% long shot; < 5% not realistic. The label uses
  the lower of OOS history and OOS MC.
- **Every results table** shows trades, trades/month and trades/day.

## Addendum 1 (owner request, added before any run)
"Try RSI+VWAP EA only too with higher risk per trade."
- **New declared basket:** RSI_VWAP = `xau-rsi-vwap` alone.
- **FIXED risk extended for every basket:** 50%, 75% and 100% per trade (FIXED now has 13 values; 49 policies in
  total).
- **RSI_VWAP comparison row:** its best development configuration is carried to validation and OOS as a reported
  comparison. It is not a selection candidate unless it is already in the development top 20.

## Disclosures
- **In-sample EAs.** The EAs and their settings were chosen by earlier studies that saw most or all of this history.
  OOS here is a chronological holdout only for the basket and sizing choice, not for the EA signals.
- **Previously viewed.** `Small Account Challenge 2026-10-23` already showed whole-period and 2024–2026 results. The OOS
  is therefore previously viewed in aggregate and not pristine.
- **Generated ticks** before 2026; gaps can exceed stops (they are in the ledgers only as recorded).
- **No intratrade equity.** Stop-out and floating losses are not modelled; the open-risk cap is the only control.
- **Fills at size.** Large late-path lot sizes assume fills the broker may not give.
- Not a forecast, not advice; any attempt belongs on demo first.
