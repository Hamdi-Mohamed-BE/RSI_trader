# Previous-day sweep rejection: raw M5 vs M15

Research-only study requested 2026-09-28. No live terminal, account, BAT,
website or production EA is modified. No optimization is authorized by this
raw comparison. The source transcript is not a complete RoboQuant template;
our missing-rule assumptions are frozen in `RULES.md`.

## Read results

- `REPORT.md`: side-by-side native statistics and limitations.
- `RESULTS.json`: all results, monthly breakdowns and frozen gate decisions.
- `VERIFICATION.json`: timing, signal geometry, sizing, deal accounting and
  independent historical-bar reconstruction.
- `balance-1y.png`: closed-balance chart, NOT floating equity.
- `REVIEW.md`: final review, timing-audit resolution and research decision.

## Operations

Use the existing native Python 3.13 environment. `run.py compile`, then
`run.py smoke`, then `run.py grid` performs 4 smoke and 64 main tests.
The runner checks the exact isolated tester path and port 3000, never kills
another process, and does not import/initialize an active MT5 connection.
Only `_Backtests/MT5-DMC-20260811` is used, with an empty chart profile,
live Experts disabled, local tester agents and native 150 ms execution delay.

One native runner at a time. Finished cases resume only with matching frozen
build/source/rules/config hashes. Do not change a strategy input or overwrite
evidence and resume into the same namespace. Stop the owned runner explicitly
before changing orchestration; do not terminate the normal MT5 terminal.

`verify.py`, `report.py`, and `charts.py` are read-only with respect to MT5
and may inspect completed runs while the grid continues. They write study
artifacts only. A partial report is not a completed gate decision.

After the tester is free, `export_minutes.py` uses a separate tester-only,
no-orders EA to export native M1 history. `verify.py` uses those minute records
to distinguish nominal M5/M15 bar labels from actual first-quote availability.
This is required for the frozen less-than-60-second freshness guard.

`native/<case>/tester.ini` contains the pre-existing isolated research account
reference, as do `minute-audit/*.ini`. They and raw journals must remain local unless separately privacy
reviewed. This task does not authorize a GitHub push or live deployment.
