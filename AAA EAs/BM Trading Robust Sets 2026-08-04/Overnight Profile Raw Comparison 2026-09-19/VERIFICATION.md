# Verification and review handoff

Completed six independent native MT5 real-tick-mode raw tests for 2025-09-19 through 2026-09-19 exclusive. Exactly the two new strategies were tested; no existing ORB/US100 transfer was run.

- Connected account verified before every run: normal MT5, Exness-MT5Trial16, demo, Zero symbol group. Live terminal remained running. Its balance and equity were unchanged at $9,643.77 after the research.
- Symbols dynamically identified by available contract names and checked descriptions: XAUUSD, USTEC, US500. Enlarged `_x100` contracts were not used.
- Native tester source rejects non-tester initialization and an unexpected account/server. Separate portable tester, empty chart profile, live Expert execution disabled, local test agent only. No active installation, BAT or website changed.
- Compilation: zero errors and zero warnings. Seven local unit tests passed.
- Independent Python reconstruction checked **1,548 overnight profiles and 1,529 eligible signals** across the six cases. All price levels, first eligible M5 close, direction, causal timing, SL and TP matched; zero profile differences.
- Native trade counts and net P/L reconcile to the deal ledgers. USD contract P/L, commissions, swap, one-entry-per-NY-day and timing were asserted. See `verification.json`, each `summary.json`, `trades.json`, `audit.csv`, native report and journal.
- First normal-terminal bulk history requests had stale September gaps. Explicit daily history requests filled them; only refreshed broker bars were used for independent verification. No price bars were invented.
- All six reports show **71% real ticks**, with real ticks beginning 2026-01-01. The earlier part of the year is generated-tick evidence, not real-tick proof.
- Execution uses the broker's native bid/ask and fee model plus fixed 150 ms delay. It is not a calibrated live liquidity/slippage simulation.
- Drawdown in RESULTS.md uses the larger of the native report relative equity DD and the EA tick-observed DD. Both are preserved. For XAU VA these are 3.74% and 4.00% respectively.
- The raw exit was attempted at 16:00 NY (or earlier known session close), but historical broker sessions/holidays prevented some fills. Gold VA has 16 exits more than one minute late, including two overnight holds. This is explicitly **not a verified strict exit-by-16:00 implementation**.
- Upward/minimum-lot sizing was retained. XAU VA reached 2.516% initial stop risk on its largest minimum-lot exception, versus a 1% target; XAU POC reached 2.690%. These are not strict 1%-maximum-risk results.

## Recommendation for review, not promotion

XAU value-area direction is the only clearly interesting raw candidate here: +22.26%, 200 trades, 74% net win rate, PF 1.56, conservative observed equity DD 4.00%. Its average initial target is only 0.444R, explaining part of the high win rate. Validate session exits, lot constraints and execution stress before considering optimization or deployment. No future profitability is implied.

Both US100 versions lost money. US500 POC earned only +1.55% with PF 1.02 and 23.50% observed equity DD; US500 VA lost money. Neither index result currently supports promotion. Gold POC is also weak (PF 1.04).

The other S&P 500 strategy transfers remain paused for user review, as requested.

Broker timezone reference: https://get.exness.help/hc/en-us/articles/360014390760-What-is-the-default-timezone-set-for-MetaTrader (Exness server GMT+0). New York DST was independently checked against `America/New_York`.
