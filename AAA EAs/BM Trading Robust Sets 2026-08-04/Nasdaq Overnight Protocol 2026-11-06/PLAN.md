# Nasdaq Overnight: Protocol clip ideas (frozen 2026-11-06, before any result)

Owner request: try to improve the Nasdaq Overnight bot, following a pasted clip ("OND" from "the Protocol", citing the New York Fed's Overnight Drift paper). The clip is data, not evidence. Its rules are incomplete, so the gaps below are my declared assumptions.

## Clip rules as tested
1. Red New York session: 16:00 cash close below the 09:30 open of the last completed session (Friday's for Monday morning).
2. RSI below 30 on a closed bar after midnight.
3. A later close above the last swing high: buy at market.
4. Stop 1 ATR below, target 1 ATR above.
5. At +0.5R the stop moves to -0.5R.
6. Target, stop, or close at 08:00.

Assumptions the clip does not give:
- Times are New York. Search window 00:00 to 08:00, one trade a night.
- Timeframe unknown, so M5 and M15 are both tested. RSI 14, ATR 14 on that timeframe.
- Swing = 2 bars each side, confirmed before the breakout bar. RSI stays armed once touched.
- The clip's "basic version" buys every midnight with the same exits.

## Current bot
Buys at 16:00 after a down close-to-close day, sells at 09:29, 2% emergency stop, no target. M1 chart, USTEC, Exness.

## Method
- Research copy of the production source. Lab inputs off must reproduce the production EX5 trade for trade, or the study stops.
- Native MT5, $10k, 1% risk, 150 ms, 2019-07-16 to 2026-11-01 (USTEC data starts 2019-07-16). Ticks before 2026 are generated.
- Every variant is one screening run in Model 1 (M1 OHLC), split by `data_split.research_split`: development to 2023-11-01, validation to 2024-11-01, OOS to 2026-11-01.
- OOS is previously viewed for the current bot and these years have been studied before (`US100 Overnight Optimization 2026-09-04`), so it is not untouched.
- No parameter search. These fixed variants only:

| Key | What changes |
|---|---|
| PROD | Current bot, lab off |
| LABPROD | Current bot through the lab code (check of the lab path) |
| BASIC | Clip basic: every midnight, no filter, clip exits (M15 ATR) |
| CLIP_M5, CLIP_M15 | Full clip rules |
| NORED_M5, NORED_M15 | Clip without the red session rule |
| NORSI_M5, NORSI_M15 | Clip without the RSI rule |
| MIRROR_M5, MIRROR_M15 | Control: short mirror (green session, RSI above 70, close below swing low) |
| RAND_M5, RAND_M15 | Control: clip trigger, random direction |
| X08 | Current bot, exit 08:00 |
| X04 | Current bot, exit 04:00 (after the European open) |
| E00 | Current bot, entry 00:00 |
| EU | Current signal, hold 01:30 to 04:00 only (the paper's window as the clip describes it) |
| O2C | Current bot, red = open to close |
| OVS40, OVS30 | Current bot, also needs M15 RSI below 40 / 30 at 16:00 |
| ATR1 | Current entry and exit time, clip stop, target and lock (M15 ATR) |
| ATR3 | Current entry and exit time, 3 M15 ATR stop, no target |
| LOCK | Current bot, 2% stop, lock at +0.5R to -0.5R |

## Decision rule
A variant counts as an improvement only if all hold:
1. PF at least 1.15 on the whole period.
2. Positive in development, validation and OOS.
3. Development return / closed drawdown (in R) above PROD's.
4. At least 2 trades a month.
5. Clip-family variants also beat their short and random controls on total R.
6. Passes the best-5-days check (still positive without them).

The top 3 by development return / closed drawdown go to native Model 4 and three-way Monte Carlo (seed 20261104), alongside PROD. Those gates must pass too. Each is compared with buy and hold on USTEC.

If nothing passes, keep the current bot. A wider search would be a separate step for the owner to approve. Nothing is installed or deployed by this study.
