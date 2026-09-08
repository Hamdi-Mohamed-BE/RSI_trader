# Relative-Value Pairs — Step 2

Research package for BTCUSD/ETHUSD and XAUUSD/XAGUSD. Start with **REPORT.md** after completion; `summary.json` contains structured results, and `all-settings.md` lists every screened configuration.

## Safety

The compiled EA is **Strategy Tester only**: it refuses to initialize on a normal demo or live chart. Neither pair has been installed in production BAT files or the website. One pair trade has two opposing legs and a combined planned risk of 1% of equity; execution/stop gaps can exceed planned risk. All native tests run in the existing isolated portable demo research terminal. Do not launch simultaneous jobs against that same terminal.

## Files

- `PLAN.md`: scope and selection rules recorded before results.
- `Data/`: compressed original broker M5 rates, contract specifications and documented cost floors.
- `selection-lock.json`: candidates frozen before inspecting final-year performance.
- `screen-results.json`: Python synchronized-M5 screening and cost sensitivities (not MT5 tick results).
- `Native/`: MT5 HTML reports, exact closed-basket ledgers, causal-feature comparisons and execution/history audit summaries.
- `Sets/`: exact MT5 test inputs.
- `EA/`: source, compiled research EA and compile log.
- `Charts/`: final-year, three-year, full-grid, PF/win-rate and Monte Carlo figures.
- `walk-forward.json`: additional quarterly screen diagnostic, not an untouched new validation sample.
- `VERIFICATION.txt`: executed verification checks.

## Reproduce

Use Python 3.13 and the local `.venv` environment (ignored by Git). Dependencies are listed in `requirements.txt`. The original rates and completed reports are saved, so **you do not need to rerun MT5 to read or regenerate charts**.

1. `acquire_data.py`: optional fresh read-only broker export. This uses the isolated portable research terminal and its saved demo login, not the user's active trading terminal. Do not use alongside native tests.
2. `research.py`: 3,132 distinct training configurations, validation shortlist, locked final-year and cost screens.
3. `native.py --smoke`: short multi-symbol and cash-reconciliation checks.
4. `native.py`: generated Every Tick / random-delay final-year and three-year execution checks.
5. `native.py --real`: request broker real-tick mode; availability is not guaranteed. Consult audit files rather than assuming every tick was genuine.
6. `execution_sensitivity.py`: locked settings at 250ms execution and repeat random-delay realizations.
7. `diagnostics.py`, `walk_forward.py`: relationship checks and rolling diagnostic.
8. `verify_research.py`: causal-prefix and native ledger checks.
9. `build_report.py`: rebuild report/graphs from saved evidence only.

The configured native terminal path is `../_Backtests/MT5-DMC-20260811`. The source/binary uses USD-profit CFD contracts only. A future standalone trading version, portfolio deployment and broker-specific live validation are deliberately **not authorized by these research results**.
