NASDAQ OPENING-CANDLE DURATION — RESEARCH ONLY

Open Results.html after the status says COMPLETE and VERIFICATION.json passes.
The current 5-minute production EA is the baseline. Other variants change only
the first opening candle, not the indicator/trailing calculation timeframe.
Entries are checked at 09:31/09:33/09:35/09:40/09:45 New York, with DST handled.

Evidence:
RESULTS.json: all complete native runs and full net-position ledgers.
SUMMARY.json: comparable metrics and return differences versus current M5.
BASELINE-PARITY.json: whole-three-month production/adapter trade parity.
VERIFICATION.json: independent cash, count, date, cost and indicator checks.
native/<case>/trades.csv: full UTC and New York timestamps and test-end exits.
native/<case>/checks.json: completed-candle and M5-indicator timestamps.

The adapter includes the production source without editing its trade-management
functions. It deliberately refuses live execution. No live charts, BATs or
website catalogue were modified. This is not a live installer release.

To reproduce, from the existing EA-store environment:
uv run --with pandas python "../BM Trading Robust Sets 2026-08-04/Nasdaq Opening Candle Duration Comparison 2026-10-07/run.py" compile
uv run --with pandas python "../BM Trading Robust Sets 2026-08-04/Nasdaq Opening Candle Duration Comparison 2026-10-07/run.py" grid
uv run --with pandas python "../BM Trading Robust Sets 2026-08-04/Nasdaq Opening Candle Duration Comparison 2026-10-07/report.py"

Existing successful results are frozen and reused. The runner acquires the shared
research tester lease and refuses to stop unrelated terminals. The isolated
tester must be idle, and its Calyx Research Empty chart profile must stay empty.
Private account INIs and journals are ignored by Git. Original unrelated research
folders are preserved. No commit/push was requested for this comparison.
