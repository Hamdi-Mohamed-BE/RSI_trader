# Completed after resuming — 2026-09-13

The user resumed with "finish the work". All 165 native MT5 runs, 165 independent native audits, 14 unit tests, statistical/cost stress and the final report are now complete. RESULTS.md and audit-results.json are the final evidence. Verdict: NOT APPROVED FOR DEPLOYMENT. Positive net results and 7/8 profitable neighbours did not overcome the failed 2-of-3 walk-forward consistency gate or negative final-year bootstrap P5 return (-6.80%). The published trade and monthly exports reconcile to the native $2,121.18 five-year profit, -$199.29 commission and -$153.52 swap.

No live EA, BAT, website or portfolio changes were made. No Git push. Do not rerun this work merely because older pause instructions below exist; they are retained as reproduction instructions.

## Resume

Working directory: this folder. Python: C:\Program Files\Python313\python.exe.

1. Read PLAN.md. Confirm research terminal is isolated and current connected broker is still Exness before more native tests. Do not touch the user's normal MT5 terminal or live positions.
2. Run `python run_pipeline.py --stage all`. Completed native reports are cached by configuration/window/model/delay/source hash. This resumes remaining neighbours and restricted-family walk-forward. Frozen selection must NOT change or be retuned based on final-period results.
3. Run `python -m unittest -v test_pipeline.py` (14 tests currently pass).
4. Run `python audit_logic.py --all`. This also refreshes derived per-trade annotations to use PRE-entry signal equity for risk, not accepted-order equity after costs. It does not change the EA or native reports. Earlier partial all-run audit passed; must repeat for remaining runs.
5. Run `python statistical_audit.py` AFTER all native stages finish. Requires final-runs.json and all three walk-forward folds. This performs common Calyx audit, 10,000-path block bootstraps and cost sensitivity. Not yet run.
6. Run `python report_results.py`. Check RESULTS.md and exported ledgers against source data. This renderer requires independent audit coverage of every native run. Do not deploy, update website or push without user authorization.

## Frozen selected settings (research only)

Long only; D1 14-bar direction; H1 pivot 1 each side, full origin-candle zone; M5 pivot 2 each side; two strict-body rejection wicks in three bars; swing stop + one tick + 0.25 M5 ATR(14); fixed TP 1R; no BE/trailing; time exit 6 hours; no extra zone-age/session restriction; 1% equity target rounded UP/minimum lot. Tester-only EA refuses live initialization.

Source SHA-256: 5101e6594ac3bfc4bbadcc8a557ca98c76593964d248aef0c74b76b2cfb2e666.

## Completed provisional native outputs

- 6m: 10 trades, 80% net wins, +7.2677%, PF 5.010, relative equity DD 2.03%.
- 1y: 30 trades, +3.6751%, PF about 1.270, DD 8.51%.
- 3y: 77 trades, +16.01% (use exact saved JSON), PF about 1.492, DD 8.45%.
- 5y: 115 trades, 59.1304% net wins, +21.2118% / $2,121.18, PF 1.41333, DD 8.58%; commission -$199.29, swap -$153.52.
- Safe 0.5%: 1y +2.19% DD 4.68%; 5y +10.36% DD 4.54% (exact values in Runs).
- Latency controls started/completed; neighbours in progress when sleep requested. Use files to determine exact remaining work.

All windows end 2026-09-05 exclusive, start independently at $10K. Raw baseline in sibling D14 H1 M5 Break Retest Raw 2026-09-13/results.json. Raw XAU returns: 6m -1.2404%, 1y +9.1274%, 3y +10.8026%, 5y +0.7964%. Do not hide the worse optimized 1y result.

## Required caveats

- Latest year excluded from parameter search, but original raw results already inspected: NOT truly unseen holdout.
- Real ticks begin 2026-01-01. Final quality: 6m100%, 1y67%, 3y22%, 5y13% real ticks; older history generated. Preliminary search model1 native M1-OHLC, confirmations model4.
- Native fixed 1ms default, separate 500/2000ms tests; native spread/commission/swap are included, not independent historical fee reconstruction.
- Native tester rejected a signal at 2025-12-22 21:05 as market closed; overlapping windows repeat the same event, not separate incidents.
- Management screens had zero actual trail/BE updates because both leading configurations used 1R targets; don't claim active trailing validation. Time exits did execute and passed audit.
- No final verdict until all gates/statistics are evaluated. A profitable backtest is not guaranteed future profit.
