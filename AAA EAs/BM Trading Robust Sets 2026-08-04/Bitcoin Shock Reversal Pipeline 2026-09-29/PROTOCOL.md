# Bitcoin shock reversal — pipeline confirmation, 2026-09-29

Scope: user's "go" advances to Bitcoin only after Nasdaq review. Gold, Nasdaq and GBPUSD remain unchanged. No live trading, production, installer, website or Git push. The previous Nasdaq exploratory override does not waive Bitcoin's raw gate.

## Frozen baseline and gate

Reuse the exact source/EX5, original RULES.md and original run-config.json from Market Style Bots Raw 2026-09-29. This copied configuration records the original raw-study authorization; this protocol records the current continuation. Verify all BUILD.json hashes before execution. No recompilation or strategy parameter changes. Original clean compile and smoke evidence are retained.

BTCUSD mode1, Exness-MT5Trial16 research CFD, H1 completed candles. A penultimate candle body >=2 times ATR14 calculated before that candle is the shock. The next closed candle reverses its body direction while remaining beyond EMA20 on the shock's side. Enter opposite the shock at the next hour's first executable quote within five minutes. 400 completed bars, finite EMA initialization, ATR is mean true range. Stop1.5ATR14; target1.5R; nominal1% equity risk rounded UP; one position and at most one attempted qualifying trade per UTC date. Entry07:00–16:59UTC; weekends permitted. Exit after6h, at20UTC, or five minutes before the current weekday session end, whichever is first executable. All concrete rules are the original study's implementation, not a claimed exact replication of the clip.

Control: same qualifying opportunities and stop/target distances, direction assigned by the original hash/seed290929. Audit actual entry-date matching and compare mean net R; one seed is a noisy benchmark, not a statistical significance test.

Raw gate fixed before fresh results: positive, PF>=1.15 and >=30 positions in BOTH3y and5y, better mean net R than matched control, valid execution. Require positive1y for a current shortlist. Retain and report delayed exits/overnight/swap flags; no fabricated calendar-time fills. Fail stops at stage4. Any exploratory optimization of a rejected baseline needs a separate explicit exception. If it passes, report for review before stage5. No Monte Carlo or prop-firm claims for a failed baseline.

## Native evidence

All periods end2026-09-27 exclusive. Six months starts2026-03-27;1y2025-09-27;3y2023-09-27;5y2021-09-27. Warmup90calendar days; no warmup trades. Reuse the original6m/1y Model4 and3y/5y Model1 raw/control evidence unchanged. Execute four new3y/5y Model4 raw/control runs in the isolated MT5-DMC-20260811 only, empty profile, live Experts/DLL disabled, local agents, serial shared lease and process/port guards. DepositUSD10000, leverage1:2000, simulated150msdelay, broker-model costs. Never initialize the normal MT5/Ava API.

Archive reports, journals, ledgers, traces, input checks, source/build hashes and run manifests. Model4 may use generated ticks where recorded ticks are absent; inspect BTC's own history instead of borrowing Nasdaq coverage. No five-year-real-tick claim without evidence. Overlapping previously seen periods are not independent or untouched holdouts. Native modeled spread/fees/delay are not independently measured live execution costs.

## Audit and reporting

Recompute counts, net PF/returns/win rate, mean net R, risk, frequencies, net win/loss streaks and closed-balance DD from closed positions; retain native floating-equity DD separately. For BTC, trades/day uses ALL quoted dates (weekends included) with eligible07–16UTC bars, not weekdays only or only traded days. Months use elapsed days/30.4375. Independently check each archived executed signal against the native H1 archive, including pre-shock ATR timing and control direction; verify full close volumes, costs, cash, signal timing, warmup/date boundaries and source/report identities. Inspect minute traces around6h/20UTC deadlines; document gaps without claiming their exact historical cause. No trades removed from results. Finish with a review report and wait before GBPUSD.
