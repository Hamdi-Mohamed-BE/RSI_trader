# Video ideas raw test on US100 (frozen 2026-11-09, before any result)

Owner request: build every idea from two Matteo Conti interviews (YouTube wm4A6qo0g3I and A0G14JYYVTk, captions read 2026-11-09) and one reel, raw rules only, on US100.

## Data and split
- Exness USTEC CFD, native MT5 Model 4 (every tick), 150 ms delay, $10k, 1% risk per trade sized to the stop. Lots round up to the lot step, as in the live EAs.
- USTEC history starts 2019-07-16. Ticks before 2026 are generated, not recorded.
- Owner's split: in-sample 2019-07-16 to 2024-01-01, out-of-sample 2024-01-01 to 2026-11-10 (end exclusive).
  - This differs from the standard pipeline split (two-year OOS plus a validation year). The owner chose it.
  - These OOS years have been seen in earlier Nasdaq studies, so they are not untouched data.
- One run per strategy over the whole period, with its ledger split by entry date. R = net / 1% of the balance before the trade.
- Buy and hold USTEC on the same windows (pipeline rule), with the native benchmark EA.

## Translation from NQ futures
- Point values are kept as index points: NQ $20/point, so $800 = 40 points and $1,500 = 75 points.
- Volume for the VWAP is MT5 tick volume, not exchange volume.
- Times are New York. Central Time = New York minus 1 hour.
- "15-session average ATR" = the mean daily true range of the last 15 completed broker D1 bars.

## Strategies (no optimisation)
**DRIFT: Drift VWAP Pullback** (video 1), M5 entries, 15-minute trend check
- VWAP on M15 bars from 09:30. No trades before 10:30.
- At each 15-minute close:
  - **Long trend:** M15 close above VWAP, VWAP above its value one bar earlier, and the close at least 0.1% above the close one hour (4 bars) earlier.
  - **Short trend:** the mirror.
- **Trigger:** the first M5 candle against the trend while the trend holds (red for long, green for short). Market entry at the next open.
  - Assumption: the trigger re-arms when the trend state changes or a trade closes.
- **Exits:** long stop 80 points, target 40 points; short stop 80 points, target 50 points.
- **Daily limits:** one position at a time, at most 4 trades a day, stop after 2 losing trades. No new trades after 15:30, flat at 15:55.

**VAULT: Vault Break** (video 2 #1), M30, long only
- **Daily setup:**
  - Session open = the M30 open at 01:00 (midnight Central Time).
  - Barrier = session open + 30% of the 15-session ATR.
  - VWAP from 01:00.
- **Entry:** an M30 close above both the barrier and the VWAP, on a bar closing 11:00–15:00. Buy at the next open.
  - Up to 3 trades a day, one at a time, re-entering on a new qualifying close.
- **Exits:** target 40 points, stop 75 points, flat at 15:30.

**VWAPADX: VWAP pullback with ADX gate** (video 2 #2), M1, long only
- **Opening range:** 09:30–10:00.
- **Arm:** an M1 close above the opening-range high.
- **Then:**
  1. price touches the VWAP (a low at or below it);
  2. an M1 close above the VWAP;
  3. ADX(14) above 20 and not higher than the previous bar. Wait for ADX if needed.
- **Entry:** buy at the next open.
- **Exits:** target = highest high of the last 5 closed bars, stop = lowest low of the last 20.
- **Assumptions:**
  - VWAP from 09:30.
  - Skip a signal whose target is not above the entry.
  - A new touch is needed after a trade.
  - One position at a time, no daily cap.
  - No new entries after 15:30, flat at 15:55 New York (the video says "3:55 Central", which is after the futures cash close).

**ONB: Overnight Bias ORB** (video 2 #3), M15, long and short
- **Overnight range:** 00:00–09:30.
- **Day bias** from the 09:30 open:
  - top third: long only;
  - bottom third: short only;
  - middle third: no trade.
- **Opening range:** the 09:30–09:45 bar.
- **Entry:** an M15 close beyond the opening range on the bias side, with ADX(14) M15 above 20. Enter at the next open.
- **Daily limit:** one trade a day. Signal bars close by 15:15.
- **Exits:** stop 30% of the 15-session ATR, target 3 times the stop, flat at 15:30.

**REEL: the reel version**
- Same as ONB without the ADX filter.
- Stop = 30% of the 15-session average daily range (high minus low).

## Controls (declared now)
- **DRIFT_RAND:** DRIFT's triggers with a random direction.
- **ONB_NOBIAS / REEL_NOBIAS:** the first opening-range break either way, ignoring the thirds.
- **ONB_RAND / REEL_RAND:** the same signals with a random direction.
- **Long-only VAULT and VWAPADX:** compared with buy and hold.

## Raw gate (report only; nothing is optimised or deployed)
A strategy passes only if all of these hold:
1. PF at least 1.15 over the whole period.
2. Positive in-sample and positive out-of-sample.
3. Still positive without its 5 best days.
4. Beats its controls on total R.
5. At least 1 trade a month.

Every table shows trades, trades per month and trades per weekday, plus the equity drawdown (relative) and the closed drawdown in R.

## Owner decisions (2026-11-10)
- DRIFT: dropped by the owner after the raw result (PF 0.99, -27.3%).
- VAULT: approved by the owner ("high win rate is good") although it fails the raw gate (PF 1.06 < 1.15, MC resample 14.4% / randomize 100% red). Owner approval, not a pipeline pass; nothing built or deployed yet.
- VWAPADX: dropped by the owner after the raw result (PF 0.64, -95.8%).
- ONB: passes the raw gate (PF 1.35, +117.5R, +205%, equity DD 10.7%, MC 0%/0%); approved by the owner. Nothing built or deployed yet.
- REEL: passes the raw gate but dropped by the owner (same trades as ONB: 782/782 ONB days shared, same side, daily correlation 0.95; 32 extra low-ADX trades lost -23R). ONB is the version kept.
