US500 CPI - CONTINUATION VS FAILED-SPIKE REVERSION
Frozen raw comparison - 16 October 2026

Scope and authorization
  S&P 500 / Exness US500 CFD, authorized after the US100 comparison.
  Same rules, not an asset-specific optimization. This is not ES futures
  and uses no ES futures contract multiplier. Other assets require review.
  No live strategy, account, portfolio, installer/BAT or website changes.
  The MQL5 engine refuses initialization outside the Strategy Tester.

Dates and data status
  Requested: 2020-01-01 to 2026-10-16 exclusive.
  Development label: before 2023-10-16. Validation label: 2023-10-16 to
  2024-10-16 exclusive. Retrospective final evaluation: 2024-10-16 to
  2026-10-16 exclusive, not untouched history or a claim of optimization.
  Exact 81 scheduled CPI release epochs come from retained BLS receipts.
  Headline/core CPI form one simultaneous event. New York EST/EDT is
  accounted for; Exness tester timestamps and exported price epochs are UTC.

Frozen rules
  Dynamic 0.25% nominal equity risk at the initial stop, $10,000 start,
  broker lots rounded DOWN; skip when minimum lot would exceed budget.
  Pre-news anchor: exact last completed M1 close before the release.
  Pre-event ATR: simple mean of fourteen M1 true ranges, requiring fifteen
  consecutive strictly pre-release M1 candles. The first fixed release M1
  close must move at least one ATR and finish in its directional outer25%.
  Stop buffer: 0.1 pre-event ATR plus one tick, rounded outward.

  Mode0 continuation: first executable break of the fixed first-minute
  high/low; stop beyond its opposite extreme; 1.5R target; entry before
  release+5 minutes; maximum hold15 minutes from fill.

  Mode1 reversion: first subsequent completed M1 close crossing the fixed
  candle midpoint against the impulse; stop beyond the spike extreme;
  target pre-news anchor, subject to minimum available entry RR1.5;
  entry before release+10 minutes; maximum hold30 minutes.

  Mode2 anchor diagnostic: same fade without the minimum1.5R entry gate.
  Midpoint entry often cannot offer1.5R to the anchor; this predeclared
  non-selection diagnostic separates restrictive geometry from market edge.

  One signal attempt per model per event, consumed on a rejected trigger.
  No retries, fallback entry, grid, martingale, trailing, break-even or
  partials. Quote-age/closed-bar execution checks are two seconds.
  Spread must not exceed10% of stop distance. Further hard-flat deadline
  release+60 minutes; actual available fills can exceed planned stop risk.

Cases and execution limitations
  Three models x two quote policies = six preregistered fixed cases.
  Cases0-2 retain available archive quotes, including zero-spread entries,
  as an execution-imperfect diagnostic. Cases3-5 reject zero-spread entry
  quotes. Positive spread alone does not establish real historical ticks.
  Known generated fallback ticks before2026 and zero-spread event quotes
  preclude presenting the reference curves as verified live performance.
  The150ms simulated delay is a scenario, not measured live latency.
  Recorded costs are retained; missing true news liquidity is not invented.
  No actual-minus-consensus filter: complete historical pre-release market
  consensus has not been verified. There is no proven70% continuation rate.

Execution and safety
  Six SEQUENTIAL native fixed-case replays, Optimization=0. No XML search,
  genetic optimization, ranking-based reselection or simultaneous tick-cache
  copies. Every case explicitly passes US500; inherited USTEC is prohibited.
  Shared isolated tester lease, empty chart profile, Experts/live trading
  disabled, no live trading API imported, local agents only, no cloud.
  Do not start another study against the shared tester while it is occupied.
  Private native/**/tester.ini is git-ignored and must not be published.
  This folder has no separate compiler-only amendment; its transferred
  source was frozen directly before native execution.

Independent descriptive study
  event_study.py reads only the frozen US500-IS.npz and US500-OOS.npz from
  Thursday Five Minute US500 Full Pipeline2026-10-14. Source hashes must
  match that DATA.json. A whole event uses one archive partition, never
  stitched or interpolated. The storage split on2024-10-14 is unrelated
  to this study's2024-10-16 evaluation boundary.
  It measures signed increments from the FIRST M1 close to completed
  release+5/+15/+30 minute prices, EXCLUDING the initial jump. Unconditional
  nonzero-impulse and significant-impulse cohorts are reported separately.
  These are bid-OHLC statistics, not executable EA win rates or returns.
  Cached prices end2026-10-13 23:56UTC. October14 CPI remains scheduled
  but missing in this independent export; it is not replaced by a fake fill.

Artifacts and reproduction
  config.json, CASES.json, calendar.json, FROZEN.json: frozen protocol.
  native/: separate immutable fixed-case reports, inputs, journals/ledgers.
  RESULTS.json: reconciled native cases; EVENT-STUDY.json: descriptive data.
  python prepare.py
  python -m unittest test_protocol -v
  python run_study.py
  python event_study.py
  python analysis_report.py

Show the completed raw results for review. Do not progress to full
optimization, live installation, other assets or GitHub pushing without
a subsequent user request. No strategy is promoted by this comparison.
Execution receipt — 16 October 2026
  One local tester-agent handshake failed before case 2 began testing.
  Its native folder/journal is retained as an unsuccessful startup, not a
  backtest result. The IDENTICAL frozen case completed in the distinct
  cpi-us500-raw-20261016-case-2-retry-1 folder. No trading rule, parameter,
  date, risk or execution delay was changed. All six completed cases have
  fresh native reports and independently reconciled cash ledgers.

