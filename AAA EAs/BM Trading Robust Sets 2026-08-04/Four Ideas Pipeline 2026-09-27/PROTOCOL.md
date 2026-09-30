# Four screenshot ideas — pipeline protocol, frozen before extended tests

Research only. No live terminal, account, production EA, BAT, website or portfolio change.

## Raw evidence

Reuse the exact hashed research EA and rules in `Four Screenshot Ideas Raw 2026-09-27`.
No change to the signals, scheduled exits, sizing, or control definitions. The completed
one-year Model 4 results are already inspected; they are diagnostic evidence, NOT an
untouched holdout. Original reports remain immutable.

Run all four strategies and their predeclared controls on 3y and 5y with Model 1,
then Model 4 with 150 ms delay. Also run all four on 6m with Model 4. Windows end
2026-09-27 exclusive and start 2021-09-27 / 2023-09-27 / 2026-03-27.
Start equity $10,000. USDJPY and ORB risk 1% current equity, rounding upward under
the canonical raw-testing convention. The two no-stop longs keep $10,000 initial
notional exposure rounded DOWN; this is not a bounded 1% loss risk. Broker leverage
in this research replay is not FTMO leverage.

## Stage 4 gate (before any optimization)

The canonical pipeline requires positive net P&L, net PF >=1.15 and >=30 trades
on BOTH 3y and 5y Model 4 runs, plus improvement over the control. We operationalize
the otherwise unspecified control comparison as a greater net-return / maximum-equity-
drawdown ratio in BOTH windows. This compares risk-adjusted performance rather than
rewarding unequal time in the market. Controls are diagnostic, not perfect causal tests.
Use net deals including swap and commission, not MT5's gross-only profit factor.

A failure does not receive parameter optimization to rescue it. A near miss is
reported separately and needs an explicit exception before a new hypothesis search.
Model 1 is an exploration screen, not a substitute for Model 4 confirmation.

## Known timing / data limitations

The source broker is unspecified. Screenshot GMT+2/+3 is implemented as New York +7h;
the research feed is UTC. Real ticks on this broker begin 2026-01-01. Older Model 4
segments may be generated, and history quality must be reported for EACH run.
Scheduled exits rejected as market-closed are retried; this is retained in the raw
replication and audited rather than silently moving exits or deleting trades.
Native symbol-session metadata is not proof of historical session specifications.
Source-broker timing parity and FTMO-specific historical spread/execution are NOT established.

## Conditional later stages

Only an eligible raw strategy proceeds to the canonical staged search dimensions and
Monte Carlo. Before searching, freeze its applicable parameter grid and all trial counts,
development 2021-09-27 to 2024-03-27, validation 2024-03-27 to 2025-09-27, with the
already-seen last year reported as retrospective confirmation. Reserve earlier UNUSED
2019-09-27 to 2021-09-27 for a one-time historical holdout if available. This older
holdout is a different regime, not a future-forward test. An unavailable clean holdout
prevents claiming fully independent validation; forward-demo evidence is then required.

Require native parity for default-off changes, stable neighbouring settings, 10,000
block-bootstrap paths of length 5, reshuffles, 10/20% random missed trades, measured
cost stress, FTMO rules and portfolio marginal-effect checks. Never manufacture measured
costs from arbitrary penalties. No deployment recommendation without those gates.

FTMO assessment uses the current 2-Step Swing contract, not a normal-account return
table. Native intratrade equity and Prague daily reset, target phases, costs, margin,
and all open-risk overlap must be included before reporting actionable pass rates.

This protocol predates the extended native results. All tested combinations are retained.
