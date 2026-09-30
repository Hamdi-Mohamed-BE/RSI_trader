# Nasdaq trend-pullback — exploratory override, 2026-09-29

Authorization: user explicitly requests exploratory optimization despite the failed raw gate. This exception permits research, not promotion or live trading. The raw result remains rejected: 5y PF1.130, 3y PF1.075, 3y worse than the direction-randomized control, and intraday carryover warnings. This is the H1 market-style hypothesis, NOT the already deployed Nasdaq5M strategy. Gold remains unchanged; BTC/GBPUSD wait for review.

## Frozen evidence and decisions

- Unchanged original mode0 source is included as RawCore.mqh. Search defaults must reproduce the original 103 latest-year positions, including modeled carryovers and cash, before searching.
- Development: 2021-09-27 to 2024-03-27 exclusive, native Model1. Only this interval may choose parameters.
- Validation: 2024-03-27 to 2025-09-27 exclusive, Model4. Test at most three development/plateau finalists; rank only passing candidates.
- Recent confirmation: 2025-09-27 to 2026-09-27 exclusive, Model4, one selected candidate only. Already seen baseline data, NOT an untouched holdout.
- Older strategy-unused temporal transfer: 2019-09-27 to 2021-09-27 exclusive, selected candidate once, if full broker history exists. Not globally pristine across this repository or forward validation.
- 180-day warmup, no trades before start. Recorded real ticks begin 2026-01-01; earlier history is generated. No pure five-year real-tick claim.
- Research terminal only: isolated MT5-DMC-20260811 portable, empty chart profile, live Experts/DLL disabled, local agents, serial tester. Exness-MT5Trial16 USTEC CFD, USD10000, leverage1:2000, 150ms simulated delay, broker-model spread/commission/swap/fees. No normal MT5 API or Ava, no deployment/installer/website edits or push.
- 1% equity nominal risk rounded UP; maximum two slots share that budget. Two-slot selection requires >=2 daily attempts AND observed overlapping positions, preventing inactive-slot half-risk optimization. Actual initial and realized risk can exceed the target.

## Search (staged top-three beam, not exhaustive Cartesian/global optimum)

Preserve every attempted case, including repeats, no-trade and failed cases. Development score = (netPF-1)*sqrt(n)/(1+equityDD/10); invalid execution or <60 positions gets -1000. Never rank on return alone. Final development eligibility: >=60 closed positions, positive P&L, PF>=1.15 and clean execution. Validation, recent and older checks: >=30, positive, PF>=1.15, clean. Stop advancement at any failed gate; no retuning on later periods.

1. Timeframe M1/M3/M5/M15/M30/H1/H4. D1 excluded: daily close lies outside original intraday entry hours and would require a different clock/holding hypothesis.
2. Entry next available quote after completed signal (market-close and next-open equivalent here); one further confirming candle; ATR limit offsets0.1/0.25/0.5; fixed index-point limits10/25/50; stop-entry offsets0.1/0.25/0.5ATR. Pending lifetime four signal bars, bounded by cutoff when daily-flat enabled.
3. Stop ATR0.5/0.75/1/1.5/2/3/4; price0.05/0.1/0.2/0.4%; fixed index points20/50/100; previous-candle, five-bar swing or twenty-bar structure with0.1ATR buffer.
4. Stop management none; breakeven0.5/1/1.5R; ATR trail distances1/1.5/2, starts0.5/1/1.5/2R; percent trail0.05/0.1/0.2%; pullback EMA trail; swing5; chandelier1.5/2/3ATR; completed-M15 50%-of-initial-target trigger/20%-lock (1R reference if no target). Stops tighten only; chandelier peak begins after entry. Indicator trails update on new signal bars.
5. Exit fixed0.5/0.75/1/1.25/1.5/2/2.5/3/4/5/6R; noTP+ATR trail; known20-bar extreme; time-only; end-of-entry-session; 50% partial at1R+ATR trail and final target. Minimum lot can prevent partials; disclose counts.
6. Session baseline07–16UTC inclusive; Asia00–08UTC; London07–16UTC; NY09:30–16 local with calendar DST; overlap12–16UTC; NYopen09:30–11 local; all quoted hours.
7. Direction both/long/short.
8. Filters none; EMA200 price agreement; closedH4EMA50 bias; ADX14>=20; DI agreement; ATR20–80 percentile of100 prior readings; spread<=0.1ATR; causal Markov directional confirmation.
9. Management exclude none/Mon/Fri/both; daily attempts1/2/3; maxpositions1/2; extra qualifying reentry after a losing SL; holding120/240/480/960min or8/16 signal bars/unlimited; daily-flat versus overnight; Friday-flat versus weekend; UTC cutoff17/18/19/20. Forced-flat also blocks fresh entries. No martingale.
10. Core signal ATR7/14/28; trend-fastEMA20/35/50/75; slowEMA100/150/200/250 (fast<slow); pullbackEMA10/20/30; pullback touch in previous1/2/3 closed bars; fast-EMA slope3/5/10 bars. Latest close still must break previous high/low and be beyond pullback EMA. Exactly400 completed bars used, preserving baseline finite initialization.
11. Joint plateau over three active dimensions, prioritizing stop distance, RR or trailing distance, pending offset, holding time, fast EMA or ATR; factors0.8/1/1.2. At least2/3 neighbors positive and execution-clean; medianPF>1; >=2 active axes. Score selects three distinct finalists before validation, not after.

The regime skill's script is absent. Adapt its causal state/transition framework locally: states from20-bar close return below-0.5%, within±0.5%, above+0.5%; 252 past transitions ending one bar before the current closed bar; Laplace+1 smoothing, >=20 outgoing transitions for current state; allow a direction only when its next-state probability exceeds the opposite. Threshold adapted for intraday bars (ours), not a claim to reproduce packaged defaults or GARCH/HMM. ATR percentile also uses prior closed values only. News filters excluded without a verified complete point-in-time calendar; do not invent events. Higher-timeframe data must already be closed at signal time.

## Carryovers and execution

Timed exits are first-available-quote requests, NOT guaranteed calendar-time fills. The baseline's29 delayed timed exits/13 cross-date positions in5y remain included. This exploratory search permits and reports such quote-gap delays, plus explicitly modeled overnight/weekend variants. They are not silently treated as error-free strict-intraday systems. No entry/close/modify/cancel failure, invalid accepted geometry, stopout, missing risk or end-of-test forced liquidation is eligible. Preserve gross/net, swaps, late-exit counts and peak holding times. Any survivor with unintended carryovers cannot be promoted as strictly intraday without a separately specified execution remedy.

## Robustness for a survivor

Only after validation/recent/older pass, confirm development and6m/1y/3y/5y in Model4 plus frozen direction-control. Count all trials. Run10000 block5 bootstrap paths, order reshuffles,10/20% trade removal, chronological thirds, recent-halfPF and deflated Sharpe accounting for every tried configuration. Require returnp05>0, PFp05>1, DSR>=95%. Stress measured extra spread/fill costs; simulated150ms is not measured live slippage. Native report equityDD remains distinct from closed-trade bootstrapDD. FTMO/portfolio analysis only for a survivor and with current official rules/relevant native equity evidence; missing evidence prevents readiness claims. Fixed related-index transfer may diagnose robustness but is not an additional asset search. Risk overlays are not used to select the edge.

Archive native reports/XML, exact cases, source/EX5, compile logs, deals, traces and hashes. Show frequency, return, PF, net win rate, native equityDD and streaks. Best observed development/validation result does not mean validated or best possible. Full research proceeds to its legitimate stop gate. Stop for the user's review after this Nasdaq study.

## Pre-search implementation review

The unchanged-default parity test completed first:103 positions and $2521.70 net exactly matched, zero compiler errors/warnings. Before the first optimization batch, the ranking implementation was finalized to keep three economically distinct settings: inactive offset, stop distance, RR, trail parameters and unused cutoff do not create separate finalist slots. Every executed configuration still counts as a trial. Parity setup source/plan is preserved in `parity-setup/`; current search plan is `run-config-search.json`. This change affects selection only, not the research EA. The reentry flag specifically recognizes a negative-gross stop-loss exit deal, not a whole-position net-profit classifier.
