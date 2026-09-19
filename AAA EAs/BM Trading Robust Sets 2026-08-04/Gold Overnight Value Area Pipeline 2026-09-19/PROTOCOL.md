# Gold Overnight Value Area — frozen full-pipeline protocol

Research only. User requested Gold first, then STOP for review. Do not start S&P optimization, deploy an EA, edit BATs/website, or push Git.

Baseline: `Overnight Profile Raw Comparison 2026-09-19/Overnight Profile Raw.mq5`, VA mode. NY 18:00–09:30 profile; M1 typical-price tick-volume histogram; 70% area in 64 bins; first completed M5 close outside value area, stop at opposite VA edge, target overnight extreme; 1% equity planned risk with upward/minimum-lot rounding; one attempt/day. Previous one-year result is already seen and is not an untouched holdout.

## Chronology and gates (freeze before search)

- Requested full window: 2021-09-19 to 2026-09-19 exclusive. Also restart independent 3y, 1y and 6m tests ending at the same boundary.
- Development: 2021-09-19 to 2024-09-19. Validation: 2024-09-19 to 2025-09-19. Latest year: 2025-09-19 to 2026-09-19, opened only after parameters are frozen; label it a previously-seen-era diagnostic, not virgin holdout.
- Discovery on broker M1/M5 bars is a Python OHLC approximation, not native tick evidence. Use spread, observed baseline median round-trip commission $5.50/lot, conservative stop-first handling of ambiguous minutes, current broker contract and lot rounding. Native MT5 decides final selection among up to three diverse finalists plus raw baseline.
- Stage A: histogram bins {32,64,96}; VA percent {60,70,80}; stop {opposite VA, POC}; minimum initial reward/risk {0,.25,.5}; last entry NY {11:00,13:00,15:00}; target overnight extreme; exit 15:30 NY; no management. 162 configurations, plus unchanged baseline.
- Stage B: best three diverse Stage A configurations on development only; target {overnight extreme,.5R,1R,1.5R}; management {none,BE at .5R,trail .5R after 1R}; risk fixed at 1%. At most 36 extra configurations. Do not optimize risk to inflate headline return.
- Training score: 30 log(net PF clipped [.05,3]) + 2 return/max(DD,1) - .5 DD; penalty below 300 trades. Native eligibility: training >=300 and validation >=60 trades, both net-positive with PF>=1.10 and equity DD<=20%. Rank eligible first, then the worse normalized training/validation score. If no candidate passes, report NO PROMOTION; do not silently relax the gate.
- Walk-forward diagnostic: for origins 2023-09-19, 2024-03-19, 2024-09-19, 2025-03-19, select using preceding two years and evaluate next six months on the frozen candidate family. Never select using a future fold. Report its screening-only fidelity.

## Execution and operational changes

Candidate research source adds parameters without changing the raw default rules. Moving candidate time exit to 15:30 NY is an explicit operational change, intended to reduce market-closed exits observed in baseline. Still clamp to known broker trading-session end and count all delayed/overnight exits. Current symbol sessions cannot establish every historical holiday. No invented exit fills or historic swap rates.

Same connected Exness Zero demo contract, native MT5 real-tick mode (Model 4), $10,000, 1:2000 current leverage, default 150 ms delay. Broker commissions/swaps from deals, actual report tick quality disclosed. No governor. Tester-only login/server guard; normal terminal used for read-only data. Baseline full ledger must reproduce the prior year before interpreting changed settings.

## Verification and stresses

- Data monotonicity, duplicate/OHLC consistency, daily/monthly coverage, weekend/session gaps and first/last bars; no fabricated bars. Source/build/SET/report hashes.
- Completed-bar profile/signal checks; NY DST/Monday boundaries; native ledger costs and cash totals; entry stop risk and rounding; same-day and late exits.
- Native selected and raw 6m/1y/3y/5y; native delay 500 ms and 1000 ms for latest year; neighboring bin/VA/minimum-R settings on development/validation.
- Extra-cost sensitivity on fixed native ledgers: +$0.10/$0.25/$0.50 per ounce per round trip and +50% commission. Explicitly a cash-flow overlay, not execution re-simulation. Missed winners/worse fills and weekly-block bootstrap, fixed seed, equity-DD limitations disclosed.
- Year/month/direction analysis, 1% and 0.5% native risk comparison for lot granularity. No account-pass probabilities unless separately requested.
- Cross-broker and true long-window real-tick confirmation unavailable unless supplied; label this evidence gap rather than invent a second broker.

Definition of done: artifacts, complete comparison, selection/gate verdict, verification and stress results, explicit uncertainty; STOP for user review. S&P candidates remain queued.
