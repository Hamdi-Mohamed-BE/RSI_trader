# Nasdaq 5M, all versions + candle-colour entry: plan (frozen 2026-11-05, before any result)

**Owner request:** backtest all Nasdaq 5M versions side by side, out of sample and Monte Carlo, against a new version: same everything, but instead of close vs EMA, follow the 09:30 New York
5-minute candle: closes green go long, closes red go short. Then suggest the best for FTMO with the expected monthly return on $100k.

**Versions (no tuning of any value):** initial stop ATR(14) x 6 (deployed) or 0.60% of price (old) x DI14 filter ON or OFF x entry EMA12 (production) or CANDLE colour. Eight in total.
Everything else as deployed: no target, ATR x 6 trail from +1R, overnight holding, 09:30 New York signal, one trade a day. A doji (close = open) is no trade.

**Tests:**
1. Native Model 4, 150 ms, $10k, 1%: data_split windows 2019-01 -> 2023-11 development, -> 2024-11 validation, -> 2026-11 OOS, and all (USTEC data starts 2019-07-16; ticks generated before 2026).
2. Stage 6 Monte Carlo on each: three-way (reshuffle, resample, randomize; 1,000 runs) + day-block bootstrap (10,000 paths); on all trades and on OOS trades.
3. Buy and hold USTEC on the same windows.
4. FTMO on the frozen engines, $100k, 2021-10 -> 2026-10 streams with intratrade marks, 0.5 / 0.75 / 1%, guard and no guard: 2-step, 1-Step, funded income.

**Raw gate for the candle rule (PIPELINE stage 4):** positive and PF >= 1.15 on 3y and 5y, >= 30 trades, better than the control. Control = the same candle rule with long and short swapped (the opposite direction).

**Choosing the FTMO suggestion, in this order, decided now:**
1. Must pass the three-way gates over all years (resample <= 5%, randomize <= 10% red) and be positive in development, validation and OOS.
2. Among those: highest FTMO 1-Step pass rate at <= 10% breach. Report the 2-step and funded income for it.
3. If no version passes step 1, say so and name the least bad, labelled as failing.

**Parity:** research EX5 with InpDirectionRule 0 must match the production ledger trade for trade.
**Caveat decided now:** eight versions from one history is a selection; the stop and DI choices were made on this data, and only the candle rule is new. Nothing here is untouched.

## Addendum 1 (owner 2026-11-05, before any result was seen)
Added the old fixed version from `Selected Portfolio Settings 2026-09-01` (OPTIMIZED 2P5R): stop 4 x ATR, fixed 2.5R target, no trailing, closed at session end 15:55 New York, DI ON and OFF, with both entry rules; and the old DYNAMIC 50-20 preset with the EMA entry. Thirteen versions in total. Same tests and same choice rule.
