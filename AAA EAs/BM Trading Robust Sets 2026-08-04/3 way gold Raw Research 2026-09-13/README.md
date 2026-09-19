# 3 way gold

Raw v0.1 research package, 2026-09-13. MQL binary version 1.00. No optimization and no live deployment.

This is a transparent implementation inspired by the user's three-engine gold-bot concept, not the creator's undisclosed bot and not a replication of the advertised +504% / 13% DD results.

- [Frozen rules and engine-by-engine research](RULES.md)
- [Results, full stats and monthly breakdown](3%20WAY%20GOLD%20RESULTS.md)
- [Native EA source](EA/3%20way%20gold.mq5)
- [Frozen all-three SET](Sets/3%20way%20gold%20RAW%20-%20All%20three%20-%20RESEARCH%20ONLY.set)
- Native MT5 HTML reports: Backtest Reports/
- Full native deal, signal, candle and equity evidence: Audit/
- Period results: Runs/
- Monthly and yearly machine-readable ledgers: monthly-breakdown.csv/json and yearly-breakdown.csv/json

## Later testing

The EA deliberately refuses live-chart initialization. It requires XAUUSD H1 and a hedging account in the Strategy Tester. No DLL or external trading service is required. The existing live portfolio, BAT installers and website are not changed.

The runner uses the project's existing isolated Exness tester, with live Experts disabled and an empty chart profile. It does not relaunch, log out or modify the connected normal terminal. Native model 4 requests real ticks, but pre-2026 history can use generated ticks; see report quality logs. Test settings use $10,000 and 1:2000 leverage, not prop-firm rules.

Risk is a nominal 0.30% per engine, not a hard cap. Broker minimum lots and the project's round-up rule can materially exceed it. Preserve the original evidence if conducting any later experiment; do not overwrite these raw results with optimized ones.

## Verification

15 Python unit checks plus 16 native MQL signal/sizing self-check cases. Every closed-hour decision is replayed independently; channel boundaries, OHLC, true range, ATR and warmed-up EMA values are checked against exported H1 candles. Fills, positions and net costs reconcile to MT5's native report. Historical results remain exploratory and do not establish future or prop-firm profitability.

The first 6-month run is archived in Preflight/. A quote-validation correction accepted zero spreads as valid. No trading signal or risk parameter changed; the original and corrected 6-month ledgers are compared by make_report.py.
