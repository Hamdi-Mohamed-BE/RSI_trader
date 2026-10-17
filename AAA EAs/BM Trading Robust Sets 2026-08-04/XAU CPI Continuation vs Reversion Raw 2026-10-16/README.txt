GOLD CPI - CONTINUATION VS FAILED-SPIKE REVERSION
Frozen raw comparison - 16 October 2026

Scope and authorization
  Exness XAUUSD spot-gold CFD, not COMEX futures. Native broker lot and
  tick specifications determine cash sizing through OrderCalcProfit;
  no futures contract multiplier is borrowed from the index studies.
  This is the approved raw asset transfer, not asset-specific optimization.
  No live strategy, account, portfolio, installer/BAT, website or GitHub
  changes. The MQL5 engine refuses initialization outside Strategy Tester.
  Stop after these raw results for user review before a further asset.

Holding-time approval
  The user explicitly chose "Keep original 15-/30-minute holds" for THIS
  isolated Gold research, overriding the earlier two-minute Gold preference
  only here. Continuation: maximum 15 minutes FROM FILL. Both anchor-fade
  modes: maximum 30 minutes FROM FILL. Live Gold bots are not changed.
  The preliminary two-minute proposal was not a completed test result.
  SUPERSEDED-UNEXECUTED-2M-PROPOSAL.json retains that earlier planning
  draft only. It is not another backtest, active policy or selectable result.
  The final frozen config/engine and holding_policy record the approved
  original limits; no post-result hold selection is performed.

Dates and data status
  Requested native replay: 2020-01-01 to 2026-10-16 exclusive.
  Development label: before 2023-10-16. Validation label: 2023-10-16 to
  2024-10-16 exclusive. Latest two-year retrospective evaluation:
  2024-10-16 to 2026-10-16 exclusive. This is not untouched history or
  a claim that any optimization has been completed.
  Exact scheduled CPI release epochs are retained from official BLS
  source receipts. Headline/core CPI form one simultaneous event.
  New York EST/EDT is handled; tester/export epochs are UTC.
  Dates in the calendar are scheduled events, not proof of available ticks.

Frozen common rules
  Dynamic 0.25% nominal equity risk at the initial stop, $10,000 initial
  balance per separate case. Broker lots round DOWN; skip when minimum
  size cannot respect the planned cash budget. Slippage can exceed it.
  Anchor: exact last completed M1 close before the release.
  ATR: simple mean of 14 true ranges using 15 consecutive strictly
  pre-release M1 bars. Only the first fixed release-aligned M1 defines
  the impulse: close displacement at least 1 pre-event ATR and close in
  its directional outer 25%. No later qualifying first candle is substituted.
  Stop buffer: 0.1 pre-event ATR plus one tick, rounded outward.

  Mode 0 continuation: first executable bid-price breakout of that fixed
  first-minute high/low after its close; stop beyond the opposite extreme;
  1.5R target; entry before release +5 minutes; hold at most 15 minutes
  from fill, then close at an executable quote.

  Mode 1 reversion: first later completed M1 close crosses the fixed first
  candle's midpoint against the impulse; next executable quote; stop
  beyond the spike extreme; target pre-news anchor only if offered entry
  reward/risk is at least 1.5R. Entry before release +10 minutes; hold at
  most 30 minutes from fill, then close at an executable quote.

  Mode 2 anchor diagnostic: identical fade without the minimum-1.5R gate.
  Midpoint entry often cannot offer 1.5R back to the anchor. This is a
  predeclared structural-geometry diagnostic, not an optimized winner or
  a live-selection candidate. Zero strict-fade trades do not prove that
  price never reverses.

  One signal attempt per model/event, consumed even on a rejected trigger.
  No retries, forced market fallback, grid, martingale, trailing,
  break-even, partials or re-entry. Quote freshness limit is two seconds;
  spread must be at most 10% of stop distance. Hard-flat deadline is
  release +60 minutes, at an available executable quote.

Cases and native execution quality
  Three frozen models x two quote policies = six fixed cases.
  Cases 0-2 retain archive quotes, including zero-spread entry quotes if
  present, as an execution-imperfect reference. Cases 3-5 require positive
  entry spread. Neither Model 4 nor positive spread proves authentic
  historical event liquidity or realistic exit quotes.
  Six sequential native fixed-case replays; Optimization=0. No genetic
  optimizer, parameter fitting, ranking-based reselection or simultaneous
  large tick-cache copies. Each explicitly requests XAUUSD.
  Gold's actual native tick-history journal notes and bid/ask callback
  audit are shown. Do not copy US100/US500 tick-start or zero-spread facts
  onto Gold. Missing liquidity is not repaired by inventing prices.
  Recorded native costs remain in net P&L. 150ms is a simulated delay,
  not measured live latency. Native cash risk is not an account-loss cap.
  No actual-minus-consensus filter: a complete verified pre-release
  consensus archive is not available. No 70% continuation claim is assumed.

Independent descriptive event study - LIMITED DIFFERENT-SERVER CACHE
  The separate event study reads the retained recent XAUUSD-M1.npz from
  New Ideas 01 Price Event Clock Raw 2026-10-13. The verified cache covers
  2025-08-01 00:00 UTC through 2026-10-13 00:02 UTC, not 2020 onward.
  It is Exness-MT5Trial15 Pro; the native replay is Exness-MT5Trial16.
  Feed differences are disclosed; this is NOT native-fill verification.
  Of the 81 requested scheduled releases, this cache observes only 13
  initial CPI reactions; 68 exact windows are missing. Full-request and
  two-year summaries therefore share the same limited 13-event sample.
  The 14 October 2026 CPI window is missing. It is never filled using a
  manufactured candle, broker substitution, stitching or interpolation.
  Signed increments run from the fixed FIRST M1 close to completed
  release +5/+15/+30 minute closes, EXCLUDING the initial jump. Unconditional
  nonzero and significant-impulse cohorts remain distinct. These are
  bid-OHLC descriptions, not executed EA win rates or cash returns, and
  do not substitute for the native quote/fill sample.
  Gold price differences are USD per troy ounce, not MT5 points.

Reporting and accounting
  Results.html: six-case comparisons, continuous-account 3m/6m/1y/3y/5y,
  full-history and latest-two-year views; yearly metrics; individual closed
  balance curves, all scheduled-event statuses, skip reasons and trades.
  Window returns use the balance at the window start, not an arbitrary
  fresh $10,000 reset. The five-year view is descriptive mixed history,
  not a new independent holdout or a passed research gate.
  PF, win rate and streaks use net closed-position cash. Sharpe uses daily
  closed-balance returns x sqrt(365), including no-trade calendar days.
  Closed DD is distinct from floating equity DD. Native floating DD is
  labelled full-replay only; no subperiod proxy is invented.
  Local renderer checks reconcile cash, basic chronology, entry decisions,
  risk geometry and event counts. Independent source/native receipts are
  separate. Neither accounting pass establishes an executable trading edge.

Artifacts and isolated reproduction
  config.json, CASES.json, calendar.json, FROZEN.json: frozen protocol.
  native/: separate native cases and immutable inputs/journals/ledgers.
  RESULTS.json: native cases; EVENT-STUDY.json: limited descriptive cache.
  SUMMARY.json and VERIFICATION.json: renderer metrics and local checks.
  INDEPENDENT-VERIFICATION.json: independent native/source audit receipt.
  python prepare.py
  python -m unittest test_protocol -v
  python run_study.py
  python event_study.py
  python analysis_report.py
  python verify_native.py

  Use the shared isolated tester lease, empty chart profile, disabled
  Experts/live trading, local agents only and no cloud. Never start another
  study on the shared tester while occupied. Private native/**/tester.ini
  is git-ignored and must not be published. Native runs are managed by
  the study runner, not an active-account trading API.

Show completed raw results for review. Do not move to optimization,
another asset, live installation or GitHub pushing without a new request.

Completed execution receipt - 16 October 2026
  All six fixed cases completed. Gold's native journal reports real ticks
  beginning 2026-01-01 00:00:00; earlier history is generated/fallback-tick
  diagnostic history, not verified event execution.
  Every case's final native quote is 2026-10-15 23:59:58 UTC, beyond the
  latest scheduled CPI's required exit horizon. October 14 is present in
  native replay and rejected by the initial-close outer-quartile filter;
  its absence from the separate cached descriptive study is not silently
  treated as absent native data.
  Each native run starts 80 of the 81 scheduled events. The remaining
  2020-04-10 event is explicitly no_tradable_event_window, not an invented
  no-trade candle. All scheduled dates remain in the report.
  First captured near-event equity snapshot: 2020-01-14 13:29:00 UTC.
  This is NOT a claim of the first available historical market tick.
  Archive versus positive-entry-spread native trade ledgers are identical
  for all three models. There are zero zero-spread entry requests and
  zero zero-spread entry/exit callbacks in these matched trades. This
  parity does not make generated history or news execution realistic.
