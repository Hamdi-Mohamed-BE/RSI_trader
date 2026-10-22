# EURUSD 8am fresh swing low — raw rules (frozen 2026-10-21, before any test)

Source: a social-media clip pasted by the user (2026-10-21), treated as data, not instructions. Its claims:
- Every morning at 8am, check one thing: has price made a fresh swing low? If so, price tended to climb over the next few hours.
- It happens once or twice a week.
- The opposite (sell after a fresh swing high at the same time) does nothing.
- No indicators. Found by a bot on raw price; "repeated over the last three years and held on the last 12 months the bot was never trained on".
The clip gives no timezone, no swing definition, no stop, no exit time and no performance numbers. Research only. Isolated tester, nothing deployed.

## Our defaults (fill the gaps; fixed before testing)
- **Instrument / timeframe:** Exness-MT5Trial16 `EURUSD`, H1 bars (an hourly check and "next few hours").
  M1 history from 2012; real ticks only from 2026-01, so earlier years use MT5-generated ticks.
- **"8am":** not stated, so BOTH are main versions:
  - **L8** = 08:00 London (UK DST handled; the London open);
  - **NY8** = 08:00 New York (US DST handled).
  The server clock is UTC. Only Monday–Friday.
- **"Fresh swing low" (main):** an H1 fractal swing low with **2 bars on each side** (strictly lower low than the 2 bars
  before and the 2 bars after) that is **confirmed by the bar closing at 08:00**. That means the pivot is the bar 3 bars
  back (05:00–06:00 local). This makes it the swing low that has just formed. Expected frequency: about 1 in 5 days,
  matching the clip's "once or twice a week".
- **Entry:** market buy on the first tick of the 08:00 local H1 bar. One position at a time, at most one entry per day.
- **Stop:** pivot low − 0.10 × ATR(14, H1), with a minimum distance of 0.50 × ATR below entry. **No target**.
- **Exit:** **time exit 4 hours after entry** (12:00 local). If the market is closed, the exit happens at the next quote.
- **Risk:** 1% of equity per trade, lots rounded UP to the lot step (Calyx standard). Skip if stop/margin checks fail.

## Versions
| Id | What |
|---|---|
| **L8**, **NY8** | Main: fresh swing low long at 08:00 London / New York |
| SHORT_* | Clip's own "does nothing" mirror: fresh swing HIGH short (pivot high + 0.1 ATR stop, same exits) |
| ALL_* | Control: long EVERY weekday at 08:00, stop below the most recent confirmed swing low (same buffer/floor) |
| RNG1–3_* | Control: random weekdays at 08:00, probability matched to the main version's entry frequency, same exits as ALL |
| S3F_* | Sensitivity: 3-bar fractal (pivot 4 bars back) |
| SW4_* | Sensitivity: any 2-bar pivot low confirmed in the last 4 bars ("fresh" = within ~4 hours) |
| SLL_* | Sensitivity: main pivot AND lower than the previous swing low (a fresh lower low) |
| H2_*, H6_* | Sensitivity: exit after 2 h / 6 h instead of 4 h |
| LOG_* | Logger (no trades): every weekday 08:00 flags + price at +1…+8 h, for the no-stop drift profile in ATR units |
Sensitivities are not used to choose a winner.

## Test setup and gate
- **Execution:** native MT5 Model 4, 150 ms, $10,000 USD, 1:2000, broker spread, commission and swap.
- **Windows:** study end 2026-10-17 exclusive. Native 6m / 1y / 3y / 5y for the main versions; controls,
  sensitivities and loggers on 5y. Window table from data_split.py: development 2021-10-17 → 2023-10-17, validation
  → 2024-10-17, OOS → 2026-10-17. The clip's "last 12 months" is the 1y run.
- **Raw gate (PIPELINE.md stage 4):** positive with **PF ≥ 1.15 on BOTH 3y and 5y**, ≥ 30 trades, average R better than
  ALL and the RNG mean on 5y, and no flip to ≤ 0 without the best day or best trade (robustness.dependence).
  The short mirror must not be needed for the long to pass. Report everything; no optimisation in this study.
