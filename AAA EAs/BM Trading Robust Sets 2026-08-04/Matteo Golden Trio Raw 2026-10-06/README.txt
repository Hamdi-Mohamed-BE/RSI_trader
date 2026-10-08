GOLDEN TRIO RAW RESEARCH — 2026-10-06
Open Results.html for the overview; each strategy has its own detailed report,
calendar years, recent slices, monthly table, trade ledger and native MT5 report.

Research wrappers + shared Engine.mqh and matching 1pct.set files are in this
folder. The compiled binaries explicitly refuse to initialise outside the MT5
Strategy Tester. They are NOT live-deployment builds and were not added to BATs.

Frozen rules and missing-source defaults: PROTOCOL.txt and run-config.json.
Primary source: https://www.youtube.com/watch?v=A0G14JYYVTk
Original source code/presets were not published in the material retrieved.
These are US100 CFD adaptations, not exchange futures or claimed prop results.

Run from this directory using the existing EA-store uv environment with cached
pandas/numpy: run.py compile; run.py smoke; run.py run (all three sequentially).
An optional trailing argument 1, 2 or 3 selects a single strategy.
verify.py and check_reports.py provide independent trace and artifact checks.
Tester settings/account header/journals are private local evidence. Do not push
native/tester.ini, private journals or account data to a public repository.
No optimisation or production promotion was requested. A future full pipeline
must use the canonical last-two-year OOS and mark it previously inspected.
