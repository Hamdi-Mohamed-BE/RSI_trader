US100 CPI — CONTINUATION VS FAILED-SPIKE REVERSION
Raw, predeclared comparison — 16 October 2026

Scope
  US100 / Exness USTEC CFD only. No other asset is authorized in this
  stage. Pause for owner review after raw results. No live strategy,
  installer/BAT, website, portfolio membership or risk setting is changed.
  The MQL5 engine refuses initialization outside the MT5 Strategy Tester.

Evidence status
  Exploratory research only; no strategy promotion or 70% probability claim.
  We are not optimizing. There are three predeclared models and two quote
  policies, six enumerated cases, with no selection based on their results.
  Related price histories and prior news strategies have already been
  inspected. The last-two-year evaluation is retrospective, not untouched.

Dates and instrument
  Requested replay: 2020-01-01 through 2026-10-15 (end-exclusive 2026-10-16).
  Development label: before 2023-10-16.
  Validation label: 2023-10-16 through 2024-10-15.
  Two-year evaluation: 2024-10-16 through 2026-10-15.
  Exact CPI dates/08:30 New York epochs come from retained BLS source
  receipts, accounting for EST/EDT. Native Exness history is UTC. CPI
  headline/core are one simultaneous event, not separate observations.
  This is not a reproduction on NQ futures and uses no futures multiplier.

Frozen rules
  See config.json, CASES.json, calendar.json and FROZEN.json.
  Risk is dynamic 0.25% of tester equity at the signal, broker lot-size
  rounded DOWN, starting at $10,000. No minimum-lot forced oversizing.
  Release-aligned FIRST M1 close must move >=1 pre-event M1 ATR(14)
  from the pre-news close and finish in its directional outer quartile.
  ATR is the simple average of the 14 true ranges computed using 15
  consecutive, strictly pre-release M1 bars. No release-bar contamination.
  Stop buffer is 0.1 pre-release ATR plus one tick, rounded outward.

  Mode 0: continuation at the first executable break beyond the fixed
  first-minute high/low. Stop beyond the opposite candle extreme; 1.5R
  target; entry before event+5 minutes; hold <=15 minutes from fill.

  Mode 1: first subsequent completed M1 close through the fixed candle
  midpoint against the impulse. Stop beyond the spike extreme; target
  the pre-news anchor; minimum available entry RR 1.5; entry before
  event+10 minutes; hold <=30 minutes from fill.

  Mode 2: explicitly predeclared diagnostic of Mode 1 WITHOUT its 1.5R
  entry gate. A midpoint fade often cannot offer 1.5R to the anchor.
  This diagnostic distinguishes restrictive geometry from market evidence;
  it is not a discovered optimization or automatically selected candidate.

  The first trigger consumes the attempt even if spread, target geometry,
  stale quotes or minimum lot rejects it. No retry/fallback market entry,
  no grid, martingale, trail, break-even, partials or re-entry.
  Pre-release last quote and initial post-release quote must be within
  two seconds of release. Fade close confirmation must be executed within
  two seconds of its close. Spread may not exceed 10% of stop distance.
  All positions have a further hard deadline at event+60 minutes; fills
  and timed exits occur at available quotes, not ideal historical prices.

Quote policies and execution caveat
  Cases 0-2 preserve the available archive as a reference diagnostic,
  including zero-spread quotes. Cases 3-5 reject zero-spread entry quotes.
  Rejecting zero-spread entries DOES NOT prove historical real liquidity.
  Known pre-2026 generated ticks and zero-spread 2026 news quotes prevent
  treating the raw reference equity curves as executable trading evidence.
  Native spread/fees are used as recorded; missing real cost is not invented.
  The simulated 150ms delay is a scenario, not measured live fill latency.
  Slippage may exceed the nominal stop-risk budget. No guaranteed loss cap.

Separate descriptive event study
  event_study.py reads local M1 exports only, independently of the native
  signal engine. It measures incremental signed movement from FIRST M1
  close to +5/+15/+30 minute prices, not persistence of the initial jump.
  All-data and significant-impulse cohorts are separate. Missing candles
  remain missing. Its local cache may end before the newest native event.
  OHLC event statistics are not tick-executable EA win rates.

Safety / reproducibility
  run_study.py reuses only the earlier isolated native runner's plumbing.
  Shared exclusive research-tester lease; occupied tester is never killed.
  Empty chart profile; Experts disabled; no live-trading API imported.
  Local tester only, no remote/cloud agents. Only this owned process can
  be terminated on a genuine timeout/shutdown failure. Native manifests,
  source, sets, ledgers and cash totals are reconciled. Private broker
  tester.ini is ignored by git and must not be published.
  The 'Optimization' flag is used solely to enumerate the SIX FROZEN cases;
  there is no search, ranking-based selection or genetic optimization.
  COMPILER-ONLY-AMENDMENT.json preserves a pre-run mechanical identifier
  rename required to eliminate two name-shadowing compiler warnings.

Reproduce
  python prepare.py
  python -m unittest test_protocol -v
  python run_study.py
  python event_study.py
  python analysis_report.py

Do not run record_compile_amendment.py again. It is a retained one-time
pre-run receipt; the finalized source is frozen and cannot be amended
after the owned native tester process starts.

Review requested
  Show raw results to the owner, then WAIT. Do not progress to EURUSD,
  XAUUSD, full optimization/pipeline, portfolio additions, live installation,
  website changes or pushing to GitHub without a subsequent request.
