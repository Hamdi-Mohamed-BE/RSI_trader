# Three-year extension — existing LTA M5 signal AND the new flow
Requested 2026-10-05. No optimisation or selection. Preserve prior 1-year study unchanged.
Native start 2023-10-05 00:00 UTC; end 2026-10-05 00:00 exclusive.
One exact prior AND_M5 variant: flow mode2, execution M5, Safe OFF, adaptive controls OFF.
The existing ALL DAY SET, EA source, compiled binary and dependency hashes must equal
the prior frozen experiment. Reuse its compiled tester-only binary; do not alter orders.
Broker Exness-MT5Trial16 XAUUSD CFD; USD10,000 initial equity; leverage1:2000;
1% current equity intended stop risk with unchanged broker ceil/min-lot sizing.
Model4, execution delay150ms, native spread/commission/swap; no synthetic extra costs.
Real ticks only where supplied by broker. Show actual report history quality and journal warnings.
All flow rules and assumptions are in the parent PROTOCOL.md. Legacy AND signal preserves
the legacy structural stop, with yesterday VAH/VAL target, frozen POC, 50% partial
and break-even after a post-entry completed M5 close beyond POC. One position,
macro/structure direction controls and two-loss pause unchanged.
Source/code off-switch parity was already verified in the parent 1-year study.
All native deal rows, positions, costs, signals and partial/BE records must be reconciled.
Count an entire position, including all partial legs/costs, once for PF/win rate/streaks.
Tables use net costs. Native MT5 floating-equity DD primary; mark-to-market daily Sharpe
annualised sqrt252 separately from native MT5 Sharpe. Position-close year metrics and
actual calendar-year cash flows are distinctly labelled. Annual segments are diagnostics
within this continuous compounded 3-year test, NOT independently rerun annual windows.
Requested three-year findings are not a full validation pipeline or out-of-sample proof:
the new rule was already compared on the latest year. No live connection/deployment,
production/BAT/website edits, risk-setting changes, Git commit or push.
