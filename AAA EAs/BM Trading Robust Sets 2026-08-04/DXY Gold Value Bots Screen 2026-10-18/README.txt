DXY GOLD VALUE-BOT SCREEN - 18 October 2026

Next research batch: RSI VWAP Gold H1, original production LTA Concepts M15,
and Gold Overnight Value Area M5. This is not the experimental M5 LTA flow.

The prior study's frozen three-hour DXY conflict rule, optional correlation
diagnostic, hourly bar captures, numerical engine and independent verifier
are reused unchanged. No parameter optimization is performed in this batch.
Compare identical saved windows ending 6 October 2026 exclusive (UTC):
three months, six months, one year, two years, three years, five years.
The primary evaluation windows are one year and three months.
Feature availability is aligned to native filled-entry timestamps, not the
earlier order request or the actual arrival of another symbol's quotes. Bar
completion at an exact hour is an idealized boundary, not a latency simulation.

This is a historical entry-veto SUBSET SCREEN, NOT a new native filtered-EA
backtest. Original executed entries and exits are immutable. Skipping an entry
can make other entries possible in a real EA; this screen cannot recover them.
LTA additionally has a daily two-consecutive-loss pause, so changing earlier
trades could change later signals through that daily state. RSI VWAP's saved
source is long-only. All original production rules/settings remain unchanged.

Gold Overnight's historical journal records 12 invalid-stop log hits, which
represent two unique rejected buy attempts (10 February and 13 April 2026).
They are not 12 missed trades. Source preparation audits and discloses these
without treating rejected attempts as executed positions or fixing the EA.
One Overnight same-second native entry/exit keeps the publisher's 1ms sorting
epsilon in INPUTS. The unchanged analysis uses integer-second close ordering;
that epsilon is not measured millisecond execution precision.

All results use unrestricted fractional lots normalized to a fixed $100
initial-stop risk on a $10,000 reference. No compounding, minimum-lot, margin,
daily-loss or portfolio guards are simulated. Whole-position net costs are
booked at natural close. Closed drawdown is NOT floating-equity drawdown.
The stress case adds $0.10 gold-price cost each side plus a second charge for
negative recorded swap. No new execution path is simulated.

The broker DXY and XAUUSD hourly captures came from Exness-MT5Trial15; the
historical gold EA trades came from Trial16. DXY is the broker's CFD series,
not a direct official ICE spot/futures feed. Original native source reports
15% real ticks across its full history; real ticks begin in January 2026.
These dates have already been researched: no untouched-OOS claim is made.

PLAN.json is declared before results; FROZEN.json binds analysis/source inputs.
INPUTS.json and SOURCE AUDIT.json reconcile admitted positions to native
deals, opening stops, costs, original presets and source-closure evidence.
RESULTS.json is independently recomputed by independent_verify.py; the
VERIFICATION.json receipt must match its exact SHA256 before the report
shows PASS. Results.html contains local period/cost/EA controls and trade detail.

No live EAs, charts, account settings, BATs or website pages are changed.
Nothing is automatically deployed or pushed to GitHub.
