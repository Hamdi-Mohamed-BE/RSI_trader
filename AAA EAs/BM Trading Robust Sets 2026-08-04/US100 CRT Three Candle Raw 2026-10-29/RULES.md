# US100 CRT three-candle setup: raw rules (frozen 2026-10-29, before any test)

**Source:** a pasted interview transcript (the "Nitro Trades" CRT / candle range theory setup), treated as data. The claims in it are *not* evidence: a 70–80% win rate at 1.5R, about $350–400k made, and "the best strategy in the game". Research only, in the isolated tester; nothing is deployed.

## Rules stated in the clip
- **Timeframes:** the setup runs on **H1, M30 or M15**; take whichever timeframe forms the setup **first**. Execution is watched on M1.
- **C1:** any candle; mark its high and low.
- **C2 (bullish):** trades **below C1's low** and its body **closes back inside** C1's range. The bearish setup is the mirror image: C2 goes above C1's high and closes back inside.
- **C3:** the entry candle.
  - **Long** when C3 breaks **C2's high**; **short** when C3 breaks C2's low.
  - If C3 does not break, the setup is over. A 4th candle is not taken.
- **Target:** the opposite extreme of C1 (C1's high for a long).
- **Stop:** placed so that reward : risk = **1.5** ("drag the stop until it's 1.5"). It is not a price level.
- **Hold:** never close early; only TP or SL ends the trade ("walk away").
- **Two entry styles:**
  - **DIRECT:** enter on the first break.
  - **REBREAK:** wait for the break, a pullback, then a second break of the same level, all inside C3 on M1. Fewer trades; claimed to have the higher win rate.
- **Session:** New York 09:30–12:00 ET, **first setup of the day**, usually 1 trade a day (2 at most). Asia 20:00–22:00 ET is mentioned as an alternative.
- **Bias:** read from H1 "key levels". Longs only after an extreme H1 low is **swept and rejected**; shorts only after an extreme high is swept and rejected. A level that is broken and held ("one or two full-bodied closes beyond it") is gone.
- **Discretionary, so NOT testable:**
  - skipping "chop" (big alternating candles or wicks);
  - skipping days without red-folder news;
  - choosing between direct and rebreak by "how aggressive the candles are";
  - occasionally using 1.3R.

## Our mechanical defaults (fill the gaps; fixed before testing)
### Market and test setup
- **Instrument:** Exness-MT5Trial16 `USTEC` (US100 / Nasdaq-100 CFD), a proxy for NQ / MNQ futures. It has CFD spread and swap, not futures costs.
- **Chart:** M1. HTF candles are the broker's own M15 / M30 / H1 bars; the server clock is UTC, so they align with ET hours.
- **NY clock:** US DST (second Sunday of March to the first Sunday of November).

### Setup and entry
- **Setup check:** when an HTF bar closes, C2 = that bar and C1 = the bar before it.
  - **Bullish:** C2.low < C1.low, C1.low < C2.close < C1.high, and C2.high < C1.high (there must be room for the target).
  - **Bearish:** the mirror image.
  - A C2 that sweeps both sides is skipped.
- **Entry level and window:**
  - **L** = C2.high (long) or C2.low (short).
  - The trigger window is **C3**, the HTF bar that opens when C2 closes.
- **Stop and target:**
  - **TP** = C1.high (long) / C1.low (short).
  - **SL** = L − (TP − L) / 1.5 (long), mirrored for shorts.
  - SL and TP are fixed from the levels when the setup arms. The real fill is at the ask/bid at the trigger, so realised RR is slightly below 1.5.
- **DIRECT trigger:** a market buy at the first tick in C3 with ask ≥ L (sell: bid ≤ L).
- **REBREAK trigger:** inside C3,
  1. first ask ≥ L;
  2. then an M1 bar closes below L (the pullback);
  3. then the next tick with ask ≥ L enters.
  Mirror for shorts. If the sequence does not complete inside C3, there is no trade.
- **Session (main):** the trigger time must be **09:30–12:00 ET**. Setups whose C3 is outside the window are not armed.
  - **One trade per NY day:** the first setup that actually triggers.
  - A setup that never triggers does not use up the day.
- **Multi-timeframe "first" version (ALL):** M15, M30 and H1 are armed at the same time. The first trigger trades, and the rest are cancelled for the day.

### Bias (B versions)
H1 confirmed fractal swings (2 bars on each side). On each H1 close, against the latest swing low (SLo) and swing high (SHi):
- low < SLo and close > SLo → **bull** (sweep and reject);
- high > SHi and close < SHi → **bear**;
- close < SLo → **bear** (broken and held);
- close > SHi → **bull**.

Trades must agree with the bias. There are no trades until the first bias event.

### Exit and risk
- **Exit:** only TP or SL, including overnight and weekends.
- **One open position at a time:** a trigger is skipped (and counted) while the EA still holds a position, for example from a previous day.
- **Risk:** **1% of equity**, lots rounded **up** to the lot step (Calyx standard), broker minimum if needed. Skipped if the broker stop level forbids it or margin is missing.
- **Test setup:** native MT5, 150 ms delay, $10,000, 1:2000, broker spread / commission / swap. End 2026-10-27 (exclusive). Real USTEC ticks start 2026-01; earlier ticks are generated.

## Data split (shared `data_split.py`)
| Part | Dates |
|---|---|
| Development | 2021-10-27 → 2023-10-27 |
| Validation | 2023-10-27 → 2024-10-27 |
| **OOS** | 2024-10-27 → 2026-10-27, the last two calendar years |

The rules are frozen before any result, so all three parts are *raw* (nothing is fitted). The OOS is the part that would be held back if the strategy later went to optimisation. Each 5y ledger is split by trade entry date. Every table shows trades, trades / month and trades / day.

## Versions
- **Grid:** TF {M15, M30, H1, ALL} × entry {DIRECT, REBREAK} × bias {none, B}. 16 versions, NY session, 1 trade/day, 5y, Model 1 (fast screen).
- **MAIN** = `ALL_R_B`, the clip's "best" version: first of the three TFs, rebreak, H1 bias.
- **SIMPLE** = `ALL_D_N`, the clip's "easy" version: first setup, direct break, no bias.
- **Model 4 confirmation:**
  - MAIN on 6m / 1y / 3y / 5y;
  - SIMPLE on 5y.
- **Controls (Model 1, 5y):** RND1–3 = MAIN with a **random direction** at each trigger (seeds 1–3), the same entry moment and the same TP / SL distances.
- **Sensitivities on MAIN (declared, not used to pick a winner):**
  - MON: skip Mondays;
  - ASIA: 20:00–22:00 ET instead of New York;
  - TWO: 2 trades a day;
  - R13: 1.3R.

## Raw gate (PIPELINE.md stage 4)
- Positive, with PF ≥ 1.15, on 3y and 5y.
- At least 30 trades.
- Better than the random-direction control.
- Still positive without the best day and without the best trade.

**FAIL → stop.** No optimisation of a loser without an explicit owner override.

## Addendum 1 (2026-10-29, after the Model 1 grid and before any Model 4 5y result)
**The Model 1 screen is invalid for this strategy.**

**Evidence:** `native/*/journal`, CRT_ENTRY entry vs L.
- Model 1 has 4 OHLC ticks per minute, so it fills the breakout a median **+3.3 to +4.0 points beyond L** (p90 +12 to +15, max +71).
- Realised RR at the fill drops from the planned 1.50 to **0.91–1.06**.
- Model 4 (smoke, real ticks) fills a median **+0.06** points from L (max +0.4), with RR 1.50 at the fill.

**Consequences:**
- The 16 Model 1 runs and the Model 1 controls / sensitivities are kept only as a **labelled invalid diagnostic**. They are not used for any decision.
- **All gate evidence is Model 4:**
  - MAIN on 6m / 1y / 3y / 5y;
  - SIMPLE on 5y;
  - RND1–3 on MAIN at 5y;
  - per-timeframe MAIN variants M15_R_B / M30_R_B / H1_R_B at 5y.
  - These are the same declared versions; nothing new is added.
