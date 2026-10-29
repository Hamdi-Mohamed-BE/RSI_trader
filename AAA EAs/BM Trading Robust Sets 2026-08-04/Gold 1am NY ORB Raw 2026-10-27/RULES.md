# Gold 1am New York ORB — raw rules (frozen 2026-10-27, before any test)

**Source:** a social-media clip pasted by the user (2026-10-27), treated as data. It is a Pine prompt for MGC1! (COMEX micro
gold futures), 5m chart, New York time.

Research only. Isolated tester, nothing deployed.

## Rules stated in the clip
- **Opening range:** the 01:00–01:15 NY high / low.
- **Entry:**
  - Signal: a 5m close beyond the range.
  - Fill: at market at the next bar open.
  - Window: entries only 01:15–03:40.
- **Stop:** the opposite side of the range.
- **Target:** 0.5R.
- **Trade limits:**
  - Max 2 trades a day, one per direction.
  - The second trade comes only after the first hits SL / TP.
  - Reverse on an opposite breakout.
- **Exit:** force close at 06:00.
- **Size in the clip:** floor($350 ÷ stop distance) at $10/pt, max 20 contracts, i.e. a fixed $350 risk per trade.
- **"Regime layer":** 6 toggleable filters (trend strength, breakout extension, volatility, volume, candle quality, VWAP),
  combined as All / N-of-M / weighted score.
  - Their definitions and lengths are **not given**, so they are **not tested**. The raw test is the core rules.

## Our defaults (fill the gaps; fixed before testing)
- **Instrument:** Exness-MT5Trial16 `XAUUSD` CFD, the spot-gold proxy for MGC (same underlying; CFD spread / swap, not
  futures).
- **Timeframe and clock:** M5. The server clock is UTC. NY time uses US DST (second Sunday of March → first Sunday of
  November).
- **Opening range:** high / low of the three M5 bars opening 01:00, 01:05 and 01:10 NY.
  - The NY day is skipped if any of those bars is missing, or if the range is under 10 points ($0.10).
- **Signal:** a closed M5 bar opening 01:15–03:35 NY (closing by 03:40) closes above the range high (long) or below
  the range low (short).
  - Entry at the first tick of the next bar.
- **Stop and target:**
  - SL = the opposite range edge.
  - TP = entry ± 0.5 × |entry − SL|.
  - A trade is skipped if the broker stop level forbids it.
- **Trades per day:** at most 2 per NY day, at most one long and one short.
  - A second trade is allowed only when no position is open (the first closed at SL / TP).
- **Reverse:** a breakout opposite to an OPEN position closes it at market and opens the other direction, if that
  direction is unused. In practice this is rare, because the stop sits at the opposite range edge.
- **Force close:** any open position closes at the first tick ≥ 06:00 NY.
- **Risk:** **1% of equity per trade**, the Calyx standard, instead of the clip's fixed $350.
  - Lots are rounded **up** to the lot step, with the broker minimum if needed.
  - The clip's 20-contract cap (= 2.0 lots XAUUSD) is applied.
- **Test setup:** native MT5 Model 4, 150 ms, $10,000, 1:2000, broker spread / commission / swap.

## Windows (end 2026-10-27 exclusive)
- 6m, 1y, 3y, 5y.
- **Ticks:** real XAUUSD ticks from 2026-01-01; earlier windows use generated ticks.

## Versions
| Id | What |
|---|---|
| **ORB05** | the clip's core rules (main) |
| RND1–3 | control: same signals and times, **random direction** (seeds 1–3), same stop distance and 0.5R |
| S_1R / S_2R | declared target sensitivities (1R, 2R); not used to pick a winner |
| S_NOREV | sensitivity: no reverse |

## Raw gate (PIPELINE.md stage 4)
- ORB05 positive on 3y and 5y with **PF ≥ 1.15**;
- **≥ 30 trades**;
- **beats the random-direction mean** on PF and mean R;
- best-day check passes;
- no execution failures.

FAIL → no optimisation.

## Addendum 1 (2026-10-27, after the raw FAIL; owner: "what if we add volatility filter?") — EXPLORATORY, declared before testing
- **Status:** a labelled exploratory add-on to a rejected strategy. It cannot turn the raw FAIL into a pass.
- **Filters,** each tested alone with the clip's rules unchanged. ATR(14) is D1, of yesterday.
  - `W_GE10` / `W_GE15`: trade only if the 01:00–01:15 range width ≥ 0.10 / 0.15 × D1 ATR (skip tiny, noisy ranges).
  - `W_LE10`: trade only if the range width ≤ 0.10 × D1 ATR (tight ranges only).
  - `HV` / `LV`: trade only if D1 ATR is above / below its own 50-day median (high- / low-volatility regime).
- **Targets:** each filter runs at the clip's 0.5R and at 2R (the best raw sensitivity) → 10 runs on 5y.
- **Split** (data_split.py on the 5y window, from each 5y ledger by close time):
  - development 2021-10-27 → 2023-10-27 for the choice;
  - validation 2023-10-27 → 2024-10-27;
  - OOS 2024-10-27 → 2026-10-27.
  - Validation and OOS were already viewed in the raw run: retrospective, not pristine.
- **Pick:** the single best by development PF with ≥ 100 dev trades. It passes only if validation AND OOS are net > 0
  with PF ≥ 1.15. No further tuning.
- **Parity:** with the filter OFF, the EA must reproduce the raw ORB05 5y ledger exactly.
