# All 32 variants — research run

Authoritative queue: `run_all.py`. Resume it using the EA store virtual-environment Python.
It continues from verified saved batches, with one isolated portable MT5 terminal at a time.
Do not run other native tests concurrently in that terminal.

Progress: `overall-progress.json` and `progress.json`.
Completed pair results: `RESULTS.json` and `SIDE BY SIDE.md`.
Full completion requires 32 rows and a passing `VERIFICATION.json`; a queued run is not completion.
After the queue finishes, run `verify_results.py` in the EA store environment to build and audit the report.
Render the verified chart with `C:\Program Files\Python313\python.exe plot_results.py`.
That installed scientific-Python environment has matplotlib; the EA store environment does not.

`PROTOCOL.md` fixes the chronology and search scope. Each asset has four independent versions.
Validation and final comparisons run as native Model 4 optimization batches for parallel tester
execution. This is only batching: the candidate settings are frozen, not optimized on the comparison
year. `ExportAudit.mqh` exports each case's exact position-ID cash ledger from the isolated tester.
It writes uniquely tagged research CSVs in MetaQuotes/Common/Files/CalyxResearch3WVPAll20260926;
copies are retained beside the native XML. This does not place or alter live orders.

The raw baselines must reproduce before an asset's search starts. Whole-position P/L, including
test-end forced exits that MT5 may label with magic 0, must reconcile to native report profit.
Partial exits are not additional independent wins/trades.

Superseded warm-up/diagnostic attempts are retained separately, not included in final results.
The final EA includes Friday/session close-out entry blocking and pending-order cancellation.
No live EAs, BAT launchers, website settings, account settings, or deployments are changed.
