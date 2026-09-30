# RSI + MACD raw research

Created after the Nasdaq DI launcher option was tested and pushed as Git commit
`dd5b449530e66ec6fd6858787e635aaacafa7cff` on `new-telegram-copy`.

The DI comparison previously cancelled by the user remains cancelled. No other
live configuration is changed. Prior PDH/PDL sweep and liquidity-continuation
studies already reached completed rejection decisions; this is a separate study.

Read `RULES.md` and `run-config.json` first. Four frozen rule definitions across
eleven instruments make 44 strategy/asset combinations, each evaluated over four
overlapping windows (176 main native cases). Four engineering smoke cases are
additional, not independent evidence of an edge. Raw-stage gate failures stop
before optimization. Passing requires user review before further stages.

`status.json` is the current runner status. `REPORT.md` / `RESULTS.json` are snapshots
of completed cases, not live progress feeds. They explicitly label incomplete work.
`VERIFICATION.json` records the latest completed audit. Retain unsuccessful cases
and reruns; do not select only favorable assets or periods.

The runner uses only `_Backtests/MT5-DMC-20260811`, the empty research profile, and
the existing private research connection. It refuses an occupied isolated terminal
or tester port. It does not connect to the normal MT5 terminal, install production
EAs, edit website data, or place live orders. Native reports, complete deals and
audits remain private in `native/`; do not publish tester INIs or raw account logs.

To resume after an interruption, ensure no owned research runner/tester is still
active, then run `run.py grid` with the existing Python environment. Finished cases
are skipped only when frozen build hashes match. Do not recompile mid-grid. Use
`verify.py`, then `report.py`, after the grid. If verification fails, report the
failure and investigate; never silently drop the failed case or promote a winner.

The source is tester-only. The shared sizing convention rounds lots up; actual
stop risk can exceed the requested 1%. The data are Exness CFD research history,
not an FTMO execution simulation. No win rate, profitability or payout is promised.
