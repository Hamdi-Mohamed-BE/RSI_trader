# Calyx NY Hourly Profiles — research package

Open **Results.html** for all results, hours, charts, costs, gates and Monte Carlo.
One compiled EA: **CalyxHourlyProfiles.ex5**. Three profile SETs: US30.set,
US100.set, SP500.set. The MQ5 source is retained beside it.

This package is NOT installed on active MT5 and is NOT added to BATs/catalogue.
Real-account use is disabled by default. The tested setting is a fixed one-lot
CFD size, NOT a cash-risk amount or percentage. There is no stop loss. Do not
copy one lot to another broker expecting the same dollars per point or margin.
Long-history account failures must be reviewed before even demo allocation.

If you later choose to run an isolated demo: copy EX5 into that terminal's
MQL5/Experts folder, refresh Navigator, attach once to each desired symbol chart,
load its matching SET, verify chart symbol/profile/NY clock and lot size, and
enable Algo Trading yourself. The EA's chart timeframe does not change the
clock-based schedule; tests use M1. Use a unique magic if intentionally running
multiple instances on the same symbol. Do not change magic or holding time
while its positions are open. Do not run it on a netting account.

The chosen NY schedules are listed in RULES.md. Custom comma-separated BUY and
SELL hours override profile defaults when either list is nonempty. Both empty
means use that asset's frozen defaults. Unknown aliases require explicit
US30/US100/SP500 profile selection; do not assume a name denotes that contract.

Reproduce with the bundled Python runtime (numpy/pandas), on this workstation:

1. `python run_native.py` — frozen selection, clean compile, isolated native
   baseline/time/delay sensitivity (27 passes; existing exact runs resume).
2. `python extras.py` — three full-horizon $1m diagnostic passes and a separate
   tester-only restart/manual-close functional test.
3. `python analyse.py` — source-bound native reconciliation, metrics,
   10,000-path day-block/shuffle/missed-trade Monte Carlo and cost gates.
4. `python post_review.py` — historical spread-quality and additional risk flags.
5. `python report.py` then `python verify.py` — offline report and evidence tests.

Runner uses only `_Backtests/MT5-DMC-20260811` with an empty chart profile and
live/DLL/remote/cloud execution disabled. Its private `.ini` files inherit local
test-account connection settings; they are ignored by Git and must NOT be
shared. For sharing, send compiled EA/SETs/report/rules only, not native configs.

No untouched future holdout exists: latest-year hours were selected on that
year, and the quarter overlaps it. Earlier 3-/5-year backcasts are not a causal
walk-forward selection test. Full pipeline evaluates this as an unavailable
promotion gate, not a pass. The three timing neighbors are diagnostics, not
chosen optimizations. The account stop-outs are retained; five-year Monte Carlo
is not fabricated over terminated-account missing periods. Full-period hour
contributions come from explicitly separate $1m execution-capital diagnostics.

Many native entry bid/ask quotes have zero spread, even in the 2026 real-tick
segment. Recorded tester costs are not proof of realistic historical/live
spread coverage. The report supplies measured extra-friction sensitivity and
marks historical bid/ask integrity as unverified. Native tester order checking
also does not establish that live gap/news execution will be the same.
