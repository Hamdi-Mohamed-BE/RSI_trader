# FTSE 100 three-setup bot — raw rules (frozen 2026-10-27, before any test)

**Source:** a social-media clip pasted by the user (2026-10-27), treated as data. It is the same "UK 100 bot" as the
2026-10-19 clip (`FTSE Monday Dip Raw 2026-10-19/`). It now names the three setups:
- **Claims:** "since 2017, +313%". Setup 1 has 44% winners and every winner pays twice its risk. Setup 2 has 54%
  winners and the best PF. Setup 3 has about 3× setup 2's trades and made 38% of the profit (setup 2: 25%). Live only
  since September.
- **2026-10-19 clip (same bot), still used here:** 0.75% risk, 2R target, 24 h exit, Monday-dip stop 2.5 ATR, other
  stop 2 ATR.

Research only. Isolated tester, nothing deployed.

## Rules stated in the clips
| Setup | Direction | Rule |
|---|---|---|
| **S1 Panic drop** | long | Close below the lower band of a 2-standard-deviation band around the 40-hour average, and RSI < 35 |
| **S2 Monday dip** | long | Monday; price below its 20-hour average; RSI < 40 |
| **S3 Trend pullback** | long | 100-hour average pointing up; price "well under" its 40-hour average; RSI < 40 |
| | short | 100-hour average pointing down; price "well above" its 40-hour average; RSI > 60 (mirror) |

All setups use a 2R target and a 24-hour time exit. Stops: S2 2.5 ATR; S1 and S3 2 ATR.

## Our defaults (fill the gaps; fixed before testing)
- **Instrument and timeframe:** Exness-MT5Trial16 `UK100` (FTSE 100 CFD), H1.
  - Signals are evaluated on each **closed** H1 bar.
  - Entry is at market on the next bar's first tick.
  - The server clock is UTC; London BST/GMT is handled.
- **Indicators:** RSI(14), ATR(14), SMA(20), SMA(40), SMA(100) of close. The band is Bollinger(40, 2.0) on close.
  **(ours: standard periods; the clip gives none for RSI/ATR)**
- **S1:** close < lower Bollinger(40, 2) and RSI < 35. **(clip)**
- **S2:** London-calendar Monday, close < SMA(20), RSI < 40, at most one entry per Monday. **(clip + ours)**
- **S3:**
  - **"Pointing up":** SMA(100) of the last closed bar > SMA(100) 5 bars earlier; "down" is the reverse. **(ours)**
  - **"Well under / above":** close ≤ SMA(40) − 1.5 ATR, or close ≥ SMA(40) + 1.5 ATR. **(ours; same 1.5 ATR used for
    "far below the 40-hour average" in the 2026-10-19 study)**
- **Positions:** at most one open position per setup, so S1, S2 and S3 can be open together. S3 holds one position at a
  time in either direction. A setup can re-enter after its trade closes.
- **Exits:**
  - SL = entry ∓ k·ATR, TP = entry ± 2·k·ATR.
  - Time exit at the first tradable tick ≥ 24 h after entry, so weekend gaps are included.
- **Hours and risk:**
  - All broker hours.
  - **0.75% of equity per trade.** Lots are rounded **up** to the step (broker minimum if needed), as in all Calyx EAs.
- **Test setup:** native MT5 Model 4, 150 ms, $10,000 USD, 1:2000, broker spread / commission / swap.

## Windows (end 2026-10-27 exclusive)
- 6m, 1y, 3y and 5y.
- **MAX** from 2019-08-01: the tester's UK100 history starts mid-2019, so the clip's "since 2017" cannot be reproduced.
- **Tick data:** real UK100 ticks begin 2026-01-02. Earlier windows use MT5-generated ticks from M1 bars.
- **Previously viewed:** 2020–2023 was viewed in the 2026-10-19 study (with different S1/S2 definitions).

## Versions
| Id | What |
|---|---|
| **S1**, **S2**, **S3** | each setup alone (main) |
| **ALL** | the three setups together: the clip's bot (main) |
| C2TF | control for "Monday matters": S2 on Tuesday–Friday, one per day (5y) |
| RNG1–3 | random-long control with 2 ATR / 2R / 24 h exits, frequency-matched to S1 (5y, 3 seeds) |
| RNGD1–3 | random-direction control with S3 exits, frequency-matched to S3 (5y, 3 seeds) |

## Raw gate (PIPELINE.md stage 4)
Each of S1, S2, S3 and ALL must meet all of these:
- 3y and 5y positive with **PF ≥ 1.15**;
- **≥ 30 trades**;
- **beats its control** on PF and mean R: S1 vs RNG, S2 vs C2TF, S3 and ALL vs RNG / RNGD;
- best-day check passes;
- no execution failures.

FAIL → no optimisation. PASS → report and ask before stage 5.
