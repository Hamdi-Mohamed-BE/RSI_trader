US500 CFD clock strategy — full research pipeline, 14 October 2026

Development: 2020-01-01 to 2023-10-14 exclusive.
Validation: 2023-10-14 to 2024-10-14 exclusive.
Final OOS: 2024-10-14 to 2026-10-14 exclusive, exactly two calendar years.
Prior 2020-2023 raw results were inspected; this is a retrospective parameter
holdout, not a claim of untouched market history. No live portfolio changes.

Our frozen 8500-rule grid: 50 entry times, 17 holds, five weekdays, two sides.
Selection prioritizes nearby parameter stability, after development/validation
cost/coverage/chronology gates. No indicator, SL, TP or trailing rule added.
Final frozen candidate: Tuesday short 09:35 ET, close 09:50 ET.
Original: Thursday long 10:10 ET, close 10:15 ET.
Fixed 1 CFD lot, $10,000 balance. NOT stop-defined 1% risk; no protective stop.

Result: both fail the final holdout. Candidate API PF 0.80, -1.03% return,
105 trades; original API PF 0.92, -0.20%, 101 trades and three missing windows.
Isolated MT5: candidate PF 0.78, -1.19%, 105 trades; original PF 0.87, -0.33%,
100 trades. Tester 39% real ticks; earlier unavailable ticks simulated.
Trial15 API / Trial16 native source and 150ms modelled execution differ.
No P/L parity claim; timing, cash reconciliation and discrepancies are retained.

Checks: 5000 joint week-sign null worlds across all 8500 rules, 252 CSCV
partitions, 10000 bootstrap paths each at 1/5/10-week blocks, DSR including
all unique configurations, cost stress, time/hold/day neighbors, quarterly
development-only walk-forward, full calendar-year/recent breakdown and ledger.
15 synthetic tests plus independent API/native/hash/accounting audit passed.
Passing implementation checks is not passing the strategy performance gates.
Family-max p for the search's best development Sharpe: 0.340; no clear discovery.
Candidate's 5-week bootstrap profit frequency: 18.48%; median return -1.03%.

Broker spread included. Extra 0.60/1.10-point costs are assumed sensitivity,
NOT measured slippage/commission. This requirement remains a failed gate.
No original ES futures fees, multipliers, roll or liquidity are reproduced.
Current CFD point-value applied to historical quotes; historical margin/lot
limits and rejection feedback are not reconstructed in the Python reference.

Reproduce in a fresh copy: collect.py (supported read-only MT5 API),
research.py select, research.py final, native.py, audit.py, report.py,
then test_research.py and check_report.py. Existing frozen selection refuses
re-ranking. Holdout source cannot load before the final manifest is written.
The research MQL5 EA refuses all live/demo chart execution.
Native account-bound tester configs/process snapshots/journals remain local.
HTML static structure checked; browser policy blocks local file previews.
