# Negative RR Study 2026-10-21 — plan (written before any result)

Owner question: set every EA in the Calyx Current14 ORB05 profile (17 EAs) to a take-profit BELOW 1R — 0.75R, 0.6R or
0.5R — leaving EAs that already use < 1R unchanged. Does it make the prop challenge pass faster / more often, and what
is the expected monthly income once funded?

## EAs (Current14 ORB05 package inputs; `Portfolio Long History All ORB05 2026-10-14` current14-orb05 cases)
Unchanged (already < 1R): five ORBs (0.5R), XAU RSI VWAP (0.5R), XAU Trend Progression (0.6R).
Changed — target input only, every other input (entry, stop, trailing, break-even, partials, time exits) unchanged:
| EA | Current exit | Override for level x |
|---|---|---|
| DMC Current XAU | 3.0R | InpRewardRisk = x |
| DMC Fresh Reaction US100 | 2.0R + trailing | InpRewardRisk = x |
| EMA3 Gold | 1.7R | InpRewardRisk = x |
| Gold Overnight Value Area | no target, 16:00 exit | InpTargetR = x (tester-only copy removes the raw guard on InpTargetR, as the 2026-10-08 RR05 study did) |
| Nasdaq 5M Candle Momentum | no target, ATR x6 trail from 1R | InpUseFixedTarget = true, InpRewardRisk = x |
| Nasdaq Overnight | no target, calendar exit; R = 2% emergency stop | InpRewardRisk = x |
| US100 Month End Flow | 2.5R, 6 h max hold (EA rejects < 0.5R) | InpRewardRisk = x |
| USDJPY London Open | 1.0R, BE at 0.75R | InpTargetR = x |
| XAU Squeeze Momentum | 1.5R + ATR trail | InpTargetR = x |
| 3-Way Gold | A no TP / B 2.5R / C 2.5R | tester-only accessor override of the module TP for ALL three modules (the RR05 patch covered A/B only) |
Levels: 0.75R, 0.60R, 0.50R. Baseline = the existing hash-verified 5-year native runs (reused, not re-run).

## Evidence
A. Native MT5 Model 4 (every tick based on real ticks where available), 150 ms delay, $10k, 1% risk, 2021-10-06 ->
   2026-10-06 exclusive, isolated tester `_Backtests/MT5-DMC-20260811` only, same ReadOnlyAudit export as the baselines.
   30 runs (10 EAs x 3 levels) + 3 Nasdaq DI OFF runs (prop package default). Gates: two baseline cases re-run through this
   runner must reproduce the stored baseline trades exactly; every run must reconcile native cash with exported deals.
   Report per EA: dev 2021-10-06 -> 2023-10-06 / validation -> 2024-10-06 / OOS -> 2026-10-06 (`data_split.py`) and 5y:
   trades, trades/month, trades/day, win rate, PF, average R per trade, return, closed DD (+ native equity DD for 5y).
B. Prop: Best Prop 9 package model (unchanged guard) with its three changed EAs (Nasdaq 5M DI OFF, USDJPY, Month End Flow)
   all set to the same level; RSI VWAP and the five ORBs unchanged. Same engines as `FTMO First Payout Study 2026-10-20`:
   challenge (both phases <= 180 d) by start window + Monte Carlo; end-to-end first payout; funded $100k income until it
   ends at 1.00% and 0.50% funded risk. Baseline re-run through the same driver must reproduce the stored results.
Every level is reported; none is selected here. Choosing a level is an owner decision on in-sample evidence.

## Caveats fixed in advance
Older ticks are generated (real ticks from 2026-01-01). The 17-EA profile has no FTMO guard and was never modelled as a
prop portfolio; part B uses the guarded Best Prop 9 roster only. Lower targets raise win rate by construction; the test is
whether net expectancy, PF and the prop/funded outcomes improve. Nothing is installed, no SET/BAT/live change, no push.

## Addendum (2026-10-21, after the parity gate, before any RR variant ran)
Parity re-run of two stored baselines: USDJPY identical (462 trades, cash identical). Nasdaq 5M: signal path identical
on all 921 trades (entry/exit times, side, prices, exit reasons, gross per lot) but total swap -$2,337.61 vs -$2,422.91
stored, so 325 compounded lot sizes differ and net is $21,554.65 vs $21,376.40. The isolated tester's symbol swap
specification has changed since the 2026-10-08 baselines. Therefore every changed EA (and Nasdaq DI OFF) gets a FRESH
baseline run in the current tester state (level `base`), and every RR level is compared with that fresh baseline.
Part B builds a `base-fresh` stream from those runs; the stored-source `base` stream is kept only as the parity link to
the earlier FTMO studies. Unchanged EAs (RSI VWAP, five ORBs) use the same stored runs in every stream.

## Correction (2026-10-21, found in the 0.75R results, before any analysis or prop run)
USDJPY London Open's current exit is NOT 1.0R: InpTargetMode=0 is PIPELINE_TIME_EXIT (exit at 16:00 London, break-even
at 0.75R); InpTargetR is only read when InpTargetMode=1 (PIPELINE_FIXED_R). The first USDJPY level runs therefore
reproduced the baseline trade-for-trade (no effect). Corrected override: InpTargetMode=1 and InpTargetR=x. The invalid
runs are kept (renamed *.INVALID-time-exit-mode) and re-run with the corrected override. All other overrides changed
results versus their fresh baselines (checked). USDJPY therefore changes from "time exit" to "fixed target".
