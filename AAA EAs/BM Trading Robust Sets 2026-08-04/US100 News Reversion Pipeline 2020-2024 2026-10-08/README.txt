US100 scheduled-news fair-price reversion: exploratory pipeline

Scope
  Exness USTEC CFD; CPI, NFP, scheduled FOMC decisions.
  $10,000 start, nominal 1% equity risk at the initial stop.
  No live terminal, portfolio, BAT, website or Git changes.
  The exported EA is TESTER ONLY and explicitly refuses live charts.

Chronology
  2020-01-01 to 2024-01-01: parameter search.
  2024-01-01 to 2025-01-01: finalist validation.
  Frozen settings persisted before 2025+ native evaluation.
  Requested evaluation ends 2026-10-08 exclusive.
  Actual archive ends 2026-10-06; no missing data invented.
  This date split is the user's study-specific override. Global OOS
  policy was not edited. Recent results had already been inspected:
  2025+ is a retrospective chronological holdout, not untouched OOS.

Raw reproduction
  Exact fill/volume/SL/TP/net parity with the original 21-trade
  +12.7988% bidirectional one-year backtest.
  Raw 3-year and 5-year gates failed. User explicitly authorised
  exploratory continuation, research only.

Selection
  SEARCH-PLAN.json declares the eight one-factor stages, beam two,
  minimum-sample penalties and development neighbourhood check.
  Every evaluated development setting is retained in trials.json.
  SELECTION.json records finalist scores; FROZEN.json hashes the
  locked engine, calendar, plan, settings and development evidence.
  No change or event-group reselection after observing 2025+.
  Native Model 4 used throughout search and validation; Model 0
  generated-tick rerun is a post-freeze diagnostic only.
  The failed single-case optimizer attempt is preserved; MT5 rejects
  start=stop for InpCase. Its replacement is a single non-optimizer
  run. No failed batch was represented as a result.

Verification
  Native deals reconcile to native report net P&L and final balance.
  Individual trades checked for direction, causal closed-bar signals,
  sizing, broker-attached SL/TP, one trade per event and time limits.
  Independent M1-cache feature reconstruction matches 158/158 fair
  prices and 158/158 pre-event ATRs across 2020-2024.
  Good Friday CPI on 2020-04-10 has no tradable USTEC event window;
  it is counted as a scheduled no-trade, not omitted from the calendar.
  10,000 circular five-observation Monte Carlo paths are closed-P&L
  proxies, not synthetic trade reexecution or challenge probabilities.
  Daily Sharpe uses actual observed UTC end equity and sqrt(365).
  Native tick-by-tick floating drawdown is authoritative; the minute
  and daily chart paths do not replace it.
  Execution-delay reruns: 150/500/1000 milliseconds.
  Extra-spread sensitivity uses strictly positive 2026 native quotes,
  reports the zero-spread artifacts separately, and cannot pass the
  execution-data-quality gate.
  Official calendar is current-vintage, not archived point-in-time.
  No complete historical market-consensus filter was used.

Files
  Results.html: main readable report, comparisons, graphs, all trials,
    annual contributions, event groups and trade-by-trade breakdown.
  SUMMARY.json: complete audited results.
  VERIFICATION.json and ARTIFACT-VERIFICATION.json: checks and caveats.
  Frozen Research EA: compiled tester-only candidate, source and 1% set.
  native/: reports, source, binaries, raw ledgers, quotes and journals.

Reproduction (existing workspace uv environment)
  prepare.py prepares official release calendar without price selection.
  run_pipeline.py resumes/reuses immutable completed native batches.
  feature_check.py reconstructs pre-event features from cached M1.
  evidence.py audits and computes statistics after the freeze.
  report.py creates the local self-contained report and research export.
  test_pipeline.py and verify_artifact.py check policy/source/artifacts.
  Dependencies: pandas, numpy, requests, beautifulsoup4, timezone data.
  Do not run another study against the shared isolated tester at the
  same time; the existing tester lease is used.
  Never commit or share native/**/tester.ini: private broker header.
  Browser visual QA is unverified because local-file browsing is
  restricted in this session. No restriction was bypassed.

Verification workflow: tokenmaxxer skill.
