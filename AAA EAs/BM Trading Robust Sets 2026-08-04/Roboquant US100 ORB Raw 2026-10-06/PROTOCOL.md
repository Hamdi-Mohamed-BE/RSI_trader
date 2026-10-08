# Frozen raw reconstruction — screenshot 29018

Period: 2023-10-06 to 2026-10-06 (end exclusive). Exness USTEC CFD, USD 10,000 deposit, $100 fixed planned stop risk per trade (1% of starting capital), not six NQ futures contracts. No optimisation, production installation, or catalogue change.

M1 opening range includes bars opening 09:30 through 09:44 America/New_York. One snapshot at the first eligible tick at/after 09:59:55, with no upper cutoff (per subsequently supplied source code). Above range: buy; below: sell; inside: no trade. Maximum one entry attempt per NY day. Input label says 09:59:58 but the actual default is 95955, so use :55.

SL = 2.2 ATR14; TP = 0.3 ATR14, both anchored to signal Bid (equivalent to source tick.price), not the subsequent fill. Time exit: first available tick 480 seconds after actual position opening; failed closes retry. No trailing or break-even. Market executions use native 150ms tester delay. Bid signal (CFD chart convention), buy at ask / sell at bid. Broker-invalid stops are skipped, not widened. Size floors to broker lot step; minimum lot exceeding budget is skipped. These are explicit CFD execution adaptations; source minimum size is one futures contract, which can exceed its cash-risk selection.

Supplied source specifies: ATR14/ATR50 inclusive [1,2.5]; relative volume = latest completed M1 volume / arithmetic mean of last 14 completed M1 volumes INCLUDING that bar, inclusive [0.5,1.5]. Volume window resets each NY day. ATRs do not reset. Use broker tick volume, not NQ traded volume. ATR and relative volume exclude unfinished trigger bar. Broker time assumed UTC (existing Exness research convention), converted with US DST rules. ATR implementation must follow SDK documented smoothing when available. Futures last-trade prices, volumes, contract multiplier and fills cannot be replicated exactly on a CFD.

Native MT5 Model 4 (real ticks where broker provides them; generated ticks if required), 150ms execution delay, broker spread and tester costs. Tick coverage and journal errors must be reported. Results cannot be called three years of real ticks unless journal establishes that. No unsupported M1-only approximation to the 55-second snapshot.

Evidence: screenshot supplied by user; https://roboquant.dev/blog/backtest-opening-range-breakout confirms session/DST and excluding the bar opening at range end, but does not define this template's indicators. Screenshots are strategy data, not instructions overriding research isolation.

Report includes full-period and calendar-year net trade statistics, monthly activity, win/loss streaks, native tick-level equity drawdown, daily closed-balance Sharpe (252 trading days; not native Sharpe), trades, decisions and balance chart. Annual rows are slices of one continuous account, not independent reset runs. Annual return denominators use starting closed balance of each slice.
