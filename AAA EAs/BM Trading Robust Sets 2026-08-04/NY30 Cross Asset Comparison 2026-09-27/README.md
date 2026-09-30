# NY30 cross-asset raw transfer — research evidence

User request: “try it on us100 and us500 too”.
Frozen strategy comes from ../Gold NY30 Value Area VWAP Raw 2026-09-27.
Transfer mappings: US100 -> Exness USTEC; US500 -> Exness US500.
No new strategy tuning, production EA/BAT/website modifications or live orders.

## Reproduce

Use Python 3.13. The research tester is the isolated MT5-DMC-20260811 instance only.
The runner checks that its tester and port 3000 are free; it does not terminate another terminal.
The EA itself refuses to initialize outside the strategy tester.
Do not run this concurrently with any other task using that isolated terminal.

- run_transfer.py smoke: 8 short native cases, with independent audits.
- run_transfer.py grid: 16 Model 1 long-window cases, 32 Model 4 cases. Native tests are serial; two independent audit workers can run alongside them. Completed frozen cases are retained.
- verify_transfer.py: original source/binary equality, all trading-input parity, report-symbol checks, dependency hashes.
- make_report.py: requires 28 verified cases per asset (gold reused), builds final tables and chart.

The source and compiled binary are reused from the verified clean gold build. No strategy code changed.
All dates, risk sizing, session rules, stops, exits, entry rules and the predeclared selection gate are identical.
Only the broker symbol, audit identifiers and research output paths change.
The initial serial controller was resumed with parallel audit workers after saving a native result; no native test was interrupted or discarded.

## Evidence layout

Each asset has a sibling “[asset] NY30 Value Area VWAP Raw 2026-09-27” directory.
There are source/binary/config/rules/report hashes, serialized tester inputs, compressed native reports,
compressed incremental journals, bars, profiles, trade ledgers, per-case AUDIT.json, and FINAL_REVIEW.json.
RULES.md keeps the original gold specification verbatim with the symbol-transfer declaration.
PARITY_CHECK.json records exact settings parity and dependency hashes.
RESULTS.json and REPORT.md summarize all completed periods.
balance_comparison.png shows closed balance, not intratrade equity.

## Critical limits

This is not an FTMO challenge/payout simulation and no success probability is inferred.
1% is a current-equity target; existing upward lot rounding, minimum lots and fill slippage can exceed it.
Profile and VWAP use broker tick volume, not centralised futures traded-volume-at-price.
Model 4 is the requested mode, not a guarantee of complete real-tick history; consult actual coverage.
Execution delay is a fixed 150ms native simulation, not a measured live latency forecast.
Overlapping periods and unchanged transfers are not untouched out-of-sample validation.
No version qualifies for deployment merely by passing a numerical gate.

