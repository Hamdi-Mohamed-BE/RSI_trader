# Frozen NY Hourly Profiles — research only

One MQL5 build, separately selectable US30, US100 and SP500 profiles. Auto profile
uses chart-symbol aliases/descriptions; custom comma-separated hour lists can be
supplied. NY daylight saving is explicit. Tester server clock is UTC for the
Exness history; live offset is detected from the server and GMT clocks.

Selection: all hour/direction cells in the saved native one-year comparison with
net PF >= 1.20 and net win rate >= 50%. No additional recent-quarter screen.

- US30: BUY 02,06; SELL 00,15,22.
- US100 / USTEC: BUY 02,13,20; SELL 14,22.
- SP500 / US500: SELL 22.

Trade at the first available tick in the scheduled NY minute, Monday–Friday.
Exit 60 minutes after the scheduled entry minute. No SL, TP or trailing stop.
One owned position per chart-symbol/magic; close overdue positions before a new
entry. Closed-market exits retry, and their actual P&L is retained, never removed
from the deployable-EA results. Entry is consumed before sending: failures,
manual closures and restarts cannot duplicate the same hour/day signal.
Broker position time recovers the exit after restart; global state persists the
consumed signal. A hedging account is required to isolate ownership.

Fixed ONE CFD lot; USD 10,000 actual native starting balance, leverage 1:2000.
This is not 1% risk: there is no protective stop. Futures contract multipliers
are not interchangeable. Below-minimum lots round upward, subject to checks.
Real-account use is disabled by default. No BAT/active chart installation.

## Pipeline protocol, frozen before new performance runs

Native MT5 Model 4, local isolated tester, 150ms delay, broker costs. Fixed hours
are unchanged across baseline 5y (2021-10-03), 3y (2023-10-03), 1y (2025-10-03)
and 3m (2026-07-03), all ending 2026-10-03 exclusive. Additional all-real 2026
and 500ms delay stress. Development stage is intentionally **not re-selection**:
small predeclared entry/holding-time neighbors diagnose sensitivity, not choose
a new winner. Main selected profile always remains minute 00 / hold 60.

Original hourly table excluded missing/delayed holds and ran independently
compared strategies on a $1m execution account. New tests use $10k, combined
selected hours and retain every actual deal. This can materially change results.

Year/quarter are selection-period diagnostics, NOT untouched holdout. Older
3-/5-year extensions are historical backcasts of a recently chosen profile,
not prospective out-of-sample proof. No fresh forward period exists yet.
Historical selection inspected 132 nonempty hourly/direction cells, and each
new inspected variant is recorded. Do not promote based on unadjusted Sharpe.

Monte Carlo: 10,000 chronological-day block resamples, block lengths 1/5/10,
fixed-dollar trade P&L (not compounding risk-%), preserving within-day trades;
trade-order reshuffles for DD/streaks only; missed-fill 10%/20%; doubled recorded
commissions and extra measured adverse-fill friction. These are conditional
historical sensitivity distributions, NOT forecast profit/pass probabilities.
Separate monthly/yearly/hour breakdowns and true native floating-equity DD.
Baseline raw gate: both 3y/5y positive, PF>=1.15, >=30 trades. Statistical gates
from saved policy; real ticks begin 2026-01-01; earlier generated sections
remain labeled. Missing independent-broker/prospective evidence is not a pass.

Coverage diagnostic amendment: after native stop-outs appeared, add one fixed
lot / $1m execution-capital 5-year pass per asset. This is only to recover the
full-period hour-level signals; it is not a $10k account simulation, not a new
selected variant and never replaces failed baseline evidence. Its net dollars
and actual $1m return are shown separately; individual hour closed-balance
drawdowns rebased to $10k are ledger diagnostics, not isolated equity tests.
