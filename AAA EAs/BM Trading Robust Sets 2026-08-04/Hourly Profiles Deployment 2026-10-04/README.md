# Hourly profile deployment — 4 October 2026

Owner-requested experimental addition to all maintained normal portfolio BATs.
US30 and US100 remain hedging-only and retain frozen NY hours, 60-minute timed
exits, duplicate protection and no SL/TP. No live terminal was modified by building.

Sizing uses the largest net completed-trade adverse price move from the published
1-year and 6-month ledgers ending 3 October 2026 exclusive. This is not a five-year
maximum or intratrade maximum adverse excursion. Original ledgers are unchanged.

At every entry: cash budget = current balance × selected percentage / 100,
or the user's fixed cash amount. Default hourly percentage is 0.5% when no explicit
percentage is supplied. Other EAs keep their existing default. The selected broker's
OrderCalcProfit converts the frozen adverse price scenario into account currency;
budget divided by loss per lot gives volume. Historical recorded costs are included
as price-equivalent units; current broker costs are not guaranteed by this conversion.
Volume rounds DOWN and respects broker minimum. The owner-authorized minimum-lot
fallback can exceed the scenario budget when the desired size is below the minimum.
Above broker maximum or failed margin/order checks block entry. Adaptive mode applies
the existing closed-loss entry block and per-EA/drawdown multipliers to the budget.

**There is no maximum-loss guarantee and no protective stop.** Future losses,
floating losses, gaps, delayed exits and fees can exceed the historical reference.
Original 1-lot website statistics are archived benchmarks, not proof of performance
of percentage sizing or of the expanded shared portfolio. This separate build permits
real-account initialization when installed; installing with Algo Trading ON can trade.

The separate FTMO guard, Ava/netting and licensed client Top 5 packages are not changed.
The FTMO comparison is separate research and does not authorize deploying no-SL EAs
past its existing open-risk protections.
