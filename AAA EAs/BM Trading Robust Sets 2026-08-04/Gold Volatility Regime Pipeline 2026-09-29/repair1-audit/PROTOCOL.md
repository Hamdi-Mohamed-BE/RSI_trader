# Gold volatility regime: approved pipeline, 2026-09-29

User requests the listed bots one by one, with review before the next. GOLD ONLY is active. The list contains four assets despite saying three; subsequent assets await clarification/review. No live account, Ava, installer, website, production SET, Git push or deployment is in scope.

## Immutable baseline and eligibility

Baseline is `Market Style Bots Raw 2026-09-29/MarketStyles.mq5`, mode 2, not the earlier gold clock-bias bot. Its raw native 3y/5y gate passed. Preserve baseline source/build/reports. The search EA must reproduce baseline trades and cash on the latest year before search starts. Ordinary risk targets 1% equity, rounded UP to lot step/minimum; actual risk can exceed 1%. Pyramiding splits this target between two position slots. Risk scaling is not a means of choosing the edge.

The regime skill's advertised runner is absent. Reuse the already disclosed causal volatility-state implementation, not an invented GARCH/HMM reproduction. All indicator inputs are completed bars. Transitions exclude the latest transition. State smoothing can mechanically create persistence and is not forecast proof.

## Frozen periods and evidence types

- Development: 2021-09-27 to 2024-03-27 exclusive. Native Model 1 staged search only.
- Validation: 2024-03-27 to 2025-09-27 exclusive. Native Model 4 ranks plateau finalists, minimum 30 positions, PF >=1.15 and positive net return.
- Recent frozen check: 2025-09-27 to 2026-09-27 exclusive. Same rules/threshold; already inspected for the baseline, NOT untouched.
- Strategy-unused older transfer holdout: 2019-09-27 to 2021-09-27 exclusive, if full native history exists. One selected configuration only; no retuning. Not future-forward evidence, nor globally pristine history across all previous research.
- 180-day warmup: the maximum 454 completed H4 bars can span over 100 calendar days. This pre-test correction replaces the initial 90-day plan, before any search result is observed. Explicitly verify no missing-history/start-date substitution. Development and recent raw periods overlap previously seen baseline evidence, disclosed selection bias.
- Tester: isolated portable `_Backtests/MT5-DMC-20260811`, empty profile, Experts/live/DLL disabled, one tester process at a time, local agents only. Exness-MT5Trial16 XAUUSD, $10,000 USD, 1:2000 research leverage, 150ms delay, actual native costs retained. Recorded real ticks begin January 2026, earlier ticks generated. No FTMO-native claim.

## Full staged search over applicable dimensions

Keep the best three distinct settings at each stage, count every case including repeated cases and rejected/zero-trade settings. This is a broad staged beam search, not the exhaustive Cartesian product or a global optimum. Score uses net position PF, sample count and equity drawdown; never cash return alone. Final development eligibility: >=60 positions, PF >=1.15, positive return and no failed entry/close/modify, invalid geometry accepted by broker, margin stop-out, or unreconciled ledger.

1. Timeframe: M1/M3/M5/M15/M30/H1/H4. D1 excluded: this is an intraday completed-candle entry model and a daily bar closes outside baseline entry hours; an independent daily/swing model would change the hypothesis.
2. Entry: next executable quote after signal close (market-on-close and next-bar-open coincide here, counted once); extra completed-bar confirmation; limit retracement ATR offsets .1/.25/.5; fixed-dollar offsets 1/3/5; continuation stop offsets .1/.25/.5 ATR. Pending lifetime four signal bars, bounded by flat time; cancellations audited.
3. Stop: ATR .5/.75/1/1.5/2/3/4; price .05/.1/.2%; fixed-dollar 5/10/20; signal extreme, five-bar swing or twenty-bar structure, plus .1 ATR buffer.
4. Management: none; BE .5/1/1.5R; ATR trail with starts .5/1/1.5/2R and distances1/1.5/2ATR; percent trail .05/.1/.2%; EMA20, swing5, chandelier1.5/2/3ATR; completed-M15 50%-trigger/20%-lock (initial target distance or1R). Trails tighten only. Post-entry extremes only for chandelier.
5. Exit: fixed .5/.75/1/1.25/1.5/2/2.5/3/4/5/6R; no TP + ATR trail; next known twenty-bar high/low; pure time exit; session exit; partial50% at1R + ATR trail, retaining configured final target. Skip partial if broker lot minimum makes it invalid; disclose.
6. Session: baseline07–16 UTC inclusive; Asia00–08UTC; London07–16UTC; NY09:30–16 local; overlap12–16UTC; NYopen09:30–11 local; all quote hours. US DST calculated causally by calendar.
7. Direction both/long/short.
8. Extra filters none/EMA200 bias/H4EMA50 bias/ADX14>=20/DI agreement/ATR20–80 percentile over100 prior readings/spread<=.1ATR. Core EMA direction remains part of the hypothesis. News blackout excluded: no independently verified complete point-in-time calendar for the entire old-history window; do not fabricate releases.
9. Trade management: weekday exclusions none/Mon/Fri/both; maximum1/2/3 attempts per day; cap1/2 positions; optional one extra qualifying entry after a net losing SL; holding120/240/480/960min or8/16 signal bars/unlimited; daily/session flat vs overnight; Friday flat vs weekend holding. Forced-flat rules also block reopening. Pending orders consume daily attempts even if unfilled. No martingale.
10. Regime: fast ATR7/14/28, slow ATR50/100/200, Hot threshold1.1/1.2/1.3/1.5, persistence.45/.55/.65/.75, transition window126/252, EMA20/50/100, slope3/5/10. Calm remains .8; cases keep Hot above Calm. Use max(400, slowATR+transitionWindow+2) bars so all states have past-only support; baseline remains exactly400 bars.
11. Joint neighbourhood: three active numeric dimensions selected from stop distance, fixed RR/trail distance, pending offset, hold time, hot threshold/ATR. Perturb -20%/0/+20%. Require >=2/3 positive neighbours and median PF>1, at least two genuinely active axes. Freeze before validation; no post-holdout rescue.

If no finalist survives a gate, stop advancement and report rejection rather than tune the evaluation period. Native baseline and selected candidate use identical comparison dates. Full 6m/1y/3y/5y confirmations and control on the chosen candidate only after validation. Random direction uses fixed seed290929 and original qualifying signal; if occupancy or pending execution breaks matched timing, disclose rather than claim exact pair matching.

## Robustness and completion

On the frozen best version's native Model4 trades, run10,000 block-bootstrap paths (block5), trade-order reshuffles, random removal10/20%, deflated Sharpe with ALL tried cases, chronological subsets and measured extra execution-cost stress. Policy requires returnp05>0, PFp05>1 and DSR>=95% for forward-test eligibility. Historical resampling is not a future probability guarantee.

Only a survivor proceeds to FTMO scenario/portfolio overlap. Recheck official current FTMO rules before simulating; label closed-P/L versus tick-equity evidence and actual historical overlap. Missing reliable cost/equity/history evidence prevents readiness claims. Risk variants (0.5% and current adaptive policy) are separately labeled overlays, not edge optimization. Silver transfer may be tested only as a fixed-rule robustness diagnostic, not an additional asset optimization.

Compile0errors/0warnings; archive source, compiled binaries, exact case tables/SETs, optimizer XML, native reports, deal ledgers, risk/cost traces, build hashes, all failures and configuration counts. Every results table includes frequency, return, PF, win%, equity DD and streaks. Full pipeline means research to its valid stop gate: production/deployment require separate approval. STOP after Gold for user review.
