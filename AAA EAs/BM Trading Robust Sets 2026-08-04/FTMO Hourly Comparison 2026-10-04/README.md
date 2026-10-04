# FTMO hourly portfolio comparison — 4 October 2026

Open `Results.html` for the shared closed-balance graph and tables. `Results.json`
contains the source fingerprints, contribution totals, skipped entries, historical
reservation sensitivities, and reference/stressed paired Monte Carlo outcomes.

This is **exploratory cached-ledger research**, not a native FTMO backtest,
validated equity drawdown, pass probability, or payout forecast. The current FTMO
guard rejects missing protective stops, so its launcher remains unchanged and
neither hourly EA is installed there. No active MT5 terminal was changed.

The common evidence window is **3 October 2025–31 August 2026**, 333 calendar days.
Baseline uses the current 14-EA FTMO roster, no news, $10,000 shared starting cash,
$50 planned risk, and the closest available standalone cached modes. Squeeze
uses Standard rather than the website's Safe mode to match the FTMO filter switch;
Nasdaq uses its DI/ATR dynamic ledger. 3-Way Gold's market-entry setting still
differs from the standalone SET. Entry risk is estimated from cache records, not
independently reconstructed initial orders. Multi-module/partial-close state is
simplified to one open cached trade per EA. Exact guarded results need new native
tests; do not promote based on this report alone.

Hourly volume uses 0.5% of current shared balance against a frozen historical
completed-trade loss reference, rounding down to an assumed FTMO 0.01 lot step,
with a 0.01 minimum fallback. These are assumed FTMO specs, distinct from the
native Exness sizing smoke tests. Historical loss is **not** a protective stop or
future loss bound. Reference size was selected using the same recent evidence.

Replay retains chronological shared cash, estimated margin, 7 entries/day,
3 daily losses, $225 total/$150 same-symbol risk reservation, $300 daily reserve
and $9,200 equity-reserve buffer. This is not tick-level equity. 1x/3x/10x hourly
historical reservations are hypothetical stress scenarios, not mathematical
upper/lower bounds. Costs retain source spread/fills and add explicit commission
floors; stressed cases additionally haircut gross wins 10%, enlarge gross losses
10%, add slippage and adverse carry assumptions. These are not FTMO historical
quotes. Rejected entries can change strategy state in ways a cached replay misses.

There are **1,000 paired paths per portfolio per cost case**, a 365-day horizon,
joint four-week calendar blocks and seed 20261004. All EAs share each block draw.
Selected-hour overfitting, regime changes, generated/zero-spread history, missing
floating equity, unavailable warm-start positions and simplified broker execution
are larger uncertainties than Monte Carlo sampling error.

The two evaluation targets are 10% and 5%; daily/max loss checks are 5% and 10%,
with Prague day resets and four traded days per phase. Phases/payouts wait for
modelled open positions to close. The reward model uses the normal initial 80%
split and 14-day first-request clock, plus assumed 2/5 business-day handovers and
4-business-day processing. It stops at the **first** payout, not annual income;
time medians are conditional on success and fees/refunds are excluded.

Official rules reviewed 4 October 2026:

- https://ftmo.com/en/trading-objectives/
- https://ftmo.com/en/faq/how-do-i-withdraw-my-profits/
- https://ftmo.com/en/faq/what-is-the-swing-account-type-and-how-does-it-work/

Reproduce from `AAA EAs/EA store`:

```powershell
uv run python "..\BM Trading Robust Sets 2026-08-04\FTMO Hourly Comparison 2026-10-04\compare.py" --paths 1000
uv run python "..\BM Trading Robust Sets 2026-08-04\FTMO Hourly Comparison 2026-10-04\compare.py" --refresh-report
```

Conclusion: **US30 alone is the better follow-up candidate; adding both crowds
daily entry/loss limits and substantially weakens the modelled portfolio.** Keep
the real FTMO guarded launcher unchanged until a bounded-risk version is tested
natively. Normal BAT inclusion is a separate owner-requested experimental change.
