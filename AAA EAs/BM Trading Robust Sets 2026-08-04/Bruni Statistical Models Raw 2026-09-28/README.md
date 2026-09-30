# Bruni research package

Research-only; do not attach the EX5 to a live chart. It refuses to initialize outside Strategy Tester.

Read REPORT.md and RULES.md first. `run-config.json` is frozen and hashed. No optimization or production installation is included.

The scripts require the established workspace, Python3.13, numpy/pandas/scipy/numba and the isolated portable MT5 installation. They never import the live MT5 Python API. The existing evidence source must remain at its original dated research path.

Reproduce offline statistics: `python study.py`.

Reconcile retained native reports: `python native_analysis.py --prop`.

Audit: `python verify.py`. It checks the original live process identity from this research session, so its live-process assertion must be reviewed rather than disabled after a legitimate user restart.

Build the final report after verification: `python report.py`.

Native tester sequence, one process at a time: `python run.py compile`, then `smoke`, `year`, `recent`, `screen`, `confirm`. The runner reuses matching frozen successful runs. It never stops a pre-existing terminal and only terminates its own child process on a timeout. Research binary goes into the isolated tester's AAA Research folder only. Existing production EAs, profiles and SETs are not edited.

`export_daily.py` collects no-trade D1 prices from the isolated tester. The initial attempt requested at least1000 rows, but only540–542 were made available; the collector threshold was reduced to500, above the model's252-return training minimum. The unsuccessful journal is preserved. Actual exported history starts January2025. There was no after-results change to model parameters or the native entry specification.

`prop_engine.py` is a versioned research fork of the existing offline minute-equity simulator. Differences: causal sizing multiplier; source minimum lot0.05 for USTEC; <=30-second QuickStrike classification in preparation; pre-policy positive-profit denominator; separate absorbing QuickStrike compliance-block state. Fixed-policy parity is tested where these changes are inactive.

Only RULES.md/run-config.json and native EA/binary are part of the native frozen build hash. Implementation bug repairs to JSON serialization, test-module import naming and Windows timestamp formatting did not alter strategy outcomes. The report generation and verification code can be rerun without launching MT5.

No full adaptive-state Monte Carlo or regime-flipped native strategy is claimed. The 10,000-path paired block bootstrap is a diagnostic on realized daily differences; it does not retrain state estimators on each synthetic path. All raw candidates failed before the pipeline's promotion/optimization stages.
