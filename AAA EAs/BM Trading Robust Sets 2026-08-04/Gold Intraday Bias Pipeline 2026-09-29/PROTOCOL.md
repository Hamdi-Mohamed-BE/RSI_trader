# Gold clock-bias full pipeline — rules frozen before native results

User approved testing improvements on 29 September 2026. Canonical PIPELINE.md and OPTIMIZATION SEARCH SPACE.json govern this gated research. Stages 1–6 are authorized; no production, website, installer, account or live-terminal changes. Source hypothesis is the previous study's **buy XAUUSD at 23:00 London, close after 120 elapsed minutes**. London DST: last Sunday of March at 01:00 UTC to last Sunday of October at 01:00 UTC. Broker clock UTC.

## Stage 1–4: native baseline gate

Raw strategy has no stop. Use constant 0.10 lot on $10,000, not a fictional 1%-risk claim. Protected/search versions require an explicit initial stop and ordinary rounded-UP 1% sizing. Do not compare increased leverage as an edge improvement. The absence of a raw stop makes it research-only.

Enter once per London weekday on the first available tick within the five-minute entry slot; missed slots are skipped, not filled hours later. Exit at/after the actual fill time plus 120 minutes on the first executable quote. Flat before Friday 20:45 UTC and NY rollover if a control would reach it. Costs are native broker spread, commission, swap and 150ms simulated delay. Never select trades using knowledge of future missing bars. This corrects an executability limitation in the original bar screen, whose complete-future-window filter was retrospective. Entry/exit missing bars and native deviations are reported, not silently discarded.

Control: one long per UTC weekday, same size/hold, half-hour slot selected by fixed date hash `((day_index*1103515245+290929) modulo 2147483647) modulo 48`. Skip known NY rollover-crossing windows. This is a fixed random-clock control, not a chosen losing neighbor. Compare mean P&L per trade as sample counts differ; show net profit and other metrics too.

Smoke first; Model 1 on 3y/5y raw and control; Model 4 plus 150ms on 6m/1y and passing 3y/5y. Real-tick coverage and generated history reported per period. Raw gate: both 3y and 5y positive, PF>=1.15, >=30 trades, and greater mean net P&L/trade than the control. Failure stops improvement search per canonical pipeline. Infrastructure repairs are not parameter tuning; preserve failed attempts and explain them.

## Stage 5 if raw gate passes

Full applicable search dimensions are in run-config.json. Baseline remains unchanged. Development 2021-09-27 to 2024-03-27; validation through 2025-09-27 selects one. The recent year is already seen and is an audit, **not a new holdout**. Reserve 2018-01-02 to 2021-09-27 for a once-only older-period replication after freezing the final candidate; this is new to this strategy but not globally pristine or forward-in-time. If history is unavailable, do not manufacture it or substitute known data as pristine.

Use staged search and retain top three, all attempts counted, then local two/three-dimensional neighbors. Entries and exits based only on completed bars/current quotes. Python replay can screen development if stop-order ambiguity is conservatively resolved and native parity confirms finalists; native results override replay. Native optimizer alternatives may be used if practical. A new parameter range cannot be added merely because initial results disappoint.

## Stage 6 if final gates pass

10,000 five-trade block bootstrap paths, trade-order reshuffle, 10/20% missed-trade scenarios, measured extra costs, equity-aware FTMO simulation and overlap with the current portfolio. Use the existing audit/FTMO helpers after inspecting them, keep evidence types separate. Strict promotion gates need positive p05 return/PF>1, stable subperiods and passing native execution/coverage checks. Missing synchronized risk/cost evidence remains a limitation. No live or forward-test profitability guarantee.

Report exactly how far the pipeline got and why. A stopped failed pipeline is a completed rejection, not an unfinished obligation to optimize a losing baseline.
