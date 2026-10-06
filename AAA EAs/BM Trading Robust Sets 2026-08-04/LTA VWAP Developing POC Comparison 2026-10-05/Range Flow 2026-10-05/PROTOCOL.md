# New M5 flow in ranging conditions — frozen research

User request: use only the new flow, not the original LTA entry AND flow, in ranging markets. This is a research-only extension. No production, live terminal, BAT, website or Git changes.

Main window: 2023-10-05 00:00 through 2026-10-05 00:00 exclusive (2023-10-05–2026-10-04 inclusive). Exness XAUUSD, USD10,000 initial capital, 1% intended current-equity stop risk; unchanged broker ceil/min-lot sizing, spread, commissions, swap, native Model4 and 150ms delay. Actual stop risk can exceed 1%. Real ticks begin 2026-01-01; earlier ticks are generated.

Freeze before running: new-flow mode1 and all parent flow entries, stops, targets, partials and BE unchanged. Original LTA execution signals are NOT required. Parent D1/H1 direction and momentum controls, one-position rule and two-loss pause remain. Safe directional Markov and adaptive portfolio controls OFF. This isolates the new range gate, not a full strategy rewrite.

Range definition (not optimized): use completed candles only. Label latest completed D1 as Bear/Sideways/Bull using its trailing20-session close return: below -5%, within ±5%, above +5%. This is the regime skill's fixed default label, implemented using the existing tester's HAMA_SafeRegimeStateAt helper. Require at least252 prior labels to be available. Estimate the transition matrix on earlier completed states only for diagnostic next-state probabilities; these probabilities are NOT an additional entry threshold. Cache daily classification at the new broker D1 bar. A Sideways label is a coarse return-based proxy, not proof of a stationary range.

Main range version additionally requires the last completed H1 ADX(14) <20. Buffer0, shift1 only; H1 bar must be completed before entry. Never use the open daily/hourly candle. This blocks strong local trends inside a coarse sideways daily label.

Predeclared cases: ungated flow3Y, daily-sideways-only flow3Y (diagnostic ablation), daily-sideways + H1 ADX<20 flow3Y (main requested case). An ungated fresh1Y off-switch parity must match the prior FLOW_M5 full native position history exactly before interpreting the main tests. No ADX threshold, lookback, stop, partial, profit target or direction search is authorized here.

Gate vetoes NEW entries only; existing positions keep original stops/targets and partial/BE management even if regime changes. No force exit on regime change. The last-three-completed-M5-bars ±.12ATR stop, yesterday's frozen VA edge target, 50% partial and entry-price BE after a subsequent M5 close beyond yesterday's POC remain. Existing entries past prior POC remain possible; no POC-ahead or minimum-RR gate.

Count whole positions, all partial/final exit legs and costs once. Primary DD is native floating-equity relative DD; daily-equity Sharpe uses five-minute sampled day-end equity. Report three continuous annual segments and the last3months separately, not fresh-account reruns. They retain accumulated equity and state. Keep skill/helper fallback explicit: the skill's Python script is absent; existing native regime code plus audited closed-bar ADX is used. Run past-only gate audits, position/deal cost reconciliation, off-switch parity, no-trade source guards and production hashes. This is an exploratory filter test on already observed history, not an unseen holdout or full validation pipeline.
