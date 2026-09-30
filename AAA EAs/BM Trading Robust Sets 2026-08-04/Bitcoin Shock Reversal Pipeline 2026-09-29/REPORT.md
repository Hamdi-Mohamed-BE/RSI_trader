# Bitcoin shock reversal — pipeline review

**Decision: rejected at the raw qualification gate. No optimized or live-ready winner.** Gold and Nasdaq are unchanged. GBPUSD has not been advanced.

Unchanged Bitcoin rules produced **+3.71% over five years**, PF **1.049**, native equity drawdown **14.43%**. Three years returned **+6.67%**, PF **1.144**. These are historical simulations on BTCUSD CFDs, not forecasts or exchange-spot returns.

## Confirmed results

Native MT5 Model 4, Exness BTCUSD CFD; USD 10,000 initial equity, nominal 1% equity risk rounded UP, 150ms simulated delay, broker-model spread and recorded fees. Four new 3y/5y raw/control confirmations; original 6m/1y evidence reused without alteration. All windows end September 27, 2026 exclusive.

| Period / case | Trades | /month | /day | Return | PF | Win rate | Equity DD | W/L streak | Mean net R |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 5y strategy | 178 | 2.97 | 0.097 | +3.71% | 1.049 | 47.8% | 14.43% | 10/6 | 0.022 |
| 3y strategy | 106 | 2.94 | 0.097 | +6.67% | 1.144 | 46.2% | 6.47% | 6/6 | 0.065 |
| 1y strategy | 33 | 2.75 | 0.090 | -1.44% | 0.894 | 36.4% | 4.93% | 3/6 | -0.047 |
| 6m strategy | 19 | 3.14 | 0.103 | -1.93% | 0.744 | 26.3% | 4.23% | 1/6 | -0.102 |

Start dates: 5y — 2021-09-27; 3y — 2023-09-27; 1y — 2025-09-27; 6m — 2026-03-27. Windows overlap and have previously been seen; they are not independent or untouched holdouts. /month uses elapsed days / 30.4375. /day uses quoted dates with 07–16 UTC entry bars, **including weekends**. Streaks use net position P&L. Native floating-equity DD is distinct from closed-balance DD.

## Why the gate stopped

- 3y: PF below 1.15.
- 5y: PF below 1.15.
- 1y: nonpositive result excludes current shortlist.

Required: positive 3y and 5y, PF ≥ 1.15 in each, at least 30 trades, beat the matched control in mean net R, valid execution; positive 1y for a current shortlist. Thresholds were frozen before these new runs. No threshold was relaxed to turn a near-miss into a pass. The conclusion applies to this specific implementation, not all Bitcoin mean-reversion strategies.

## Matched random-direction control

The control keeps qualifying opportunities, clock, stop/target distances and sizing rules, but assigns direction using frozen seed 290929. This compares directional information conditional on the selected opportunities; it does not test random entry times or random levels. One seed is not a statistical significance test. Compare mean net R because compounded cash paths differ.

| Period / case | Trades | /month | /day | Return | PF | Win rate | Equity DD | W/L streak | Mean net R |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 5y control | 178 | 2.97 | 0.097 | -15.70% | 0.800 | 40.4% | 22.13% | 6/10 | -0.088 |
| 3y control | 106 | 2.94 | 0.097 | -12.17% | 0.747 | 37.7% | 19.58% | 5/10 | -0.115 |
| 1y control | 33 | 2.75 | 0.090 | -6.96% | 0.558 | 30.3% | 11.11% | 2/9 | -0.204 |
| 6m control | 19 | 3.14 | 0.103 | +0.54% | 1.082 | 36.8% | 5.30% | 2/4 | 0.032 |

- bitcoin-reversal-raw-3y-m4: 106 matched dates; complete matching: True; mean paired net-R advantage +0.1799R.
- bitcoin-reversal-raw-5y-m4: 178 matched dates; complete matching: True; mean paired net-R advantage +0.1103R.

![Bitcoin native comparison](<C:/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04/Bitcoin Shock Reversal Pipeline 2026-09-29/comparison.png>)

Lines are hourly samples of minute-recorded floating equity, not buy-and-hold Bitcoin prices. Table drawdowns use full native tester equity statistics.

## Earlier screen retained

The earlier +3.70% headline was the 5y one-minute-OHLC Model 1 screen. These rows are retained original tests, not newly optimized variants. Model 4 uses a different intrabar execution path.

| Period / case | Trades | /month | /day | Return | PF | Win rate | Equity DD | W/L streak | Mean net R |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 5y strategy | 178 | 2.97 | 0.097 | +3.70% | 1.049 | 47.8% | 14.36% | 10/6 | 0.022 |
| 5y control | 178 | 2.97 | 0.097 | -15.68% | 0.800 | 40.4% | 22.07% | 6/10 | -0.088 |
| 3y strategy | 106 | 2.94 | 0.097 | +6.68% | 1.144 | 46.2% | 6.46% | 6/6 | 0.066 |
| 3y control | 106 | 2.94 | 0.097 | -12.11% | 0.748 | 37.7% | 19.57% | 5/10 | -0.114 |

## Exact unchanged hypothesis

A completed H1 candle body must be at least 2 × ATR14 measured before that shock. The next completed candle reverses body direction, but closes on the shock side of EMA20. Trade opposite the shock at the next hour. Stop: 1.5 × ATR14; target: 1.5R; one attempt/day; entries 07–16 UTC including weekends; exit after six hours, 20:00 UTC, or before a known session close. The clip did not specify these parameters: they are the original research implementation, not a replication claim. No breakeven, trailing, loss escalation or averaging.

## Execution and costs

- 5y: execution/carry flags none; longest hold 6.00h; initial stop risk median 1.021%, maximum 1.278%; closed-balance DD 13.85%, native equity DD 14.43%.
- 3y: execution/carry flags none; longest hold 6.00h; initial stop risk median 1.025%, maximum 1.243%; closed-balance DD 5.43%, native equity DD 6.47%.
- 1y: execution/carry flags none; longest hold 6.00h; initial stop risk median 1.034%, maximum 1.098%; closed-balance DD 4.40%, native equity DD 4.93%.
- 6m: execution/carry flags none; longest hold 6.00h; initial stop risk median 1.036%, maximum 1.099%; closed-balance DD 3.90%, native equity DD 4.23%.

Five-year gross trade P&L $+598.17; commission $-227.40; swap $+0.00; fees $+0.00; net $+370.77. Spread is embedded in bid/ask fills, not separately deducted again.

Five-year raw timed-exit audit: 0 delayed/cross-date positions. Diagnostics use6h/20UTC plus a two-minute tolerance; the session rule can require an earlier exit. All positions remain in the results. Minute-trace gaps can show missing modeled quote activity, not its exact historical cause or available live fills. The session API provides weekday sessions, not a full dated holiday calendar. [Official session API](https://www.mql5.com/en/docs/marketinformation/symbolinfosessiontrade).

## Historical data limits

- 5y native history label: 14% real ticks.
- 3y native history label: 22% real ticks.
- 1y native history label: 59% real ticks.
- 6m native history label: 98% real ticks.

Broker journals report recorded real ticks beginning 2026.01.01. Model4 is therefore not automatically all-real-tick history. MT5 can generate ticks where minute bars exist without tick records. [Official real/generated tick documentation](https://www.metatrader5.com/en/terminal/help/algotrading/tick_generation). History labels include90-day warmup. Simulated150ms delay and the broker fee model are not measured live slippage or an independently verified historical fee series.

## Verification and pipeline stop

- Original source, EX5, rules and configuration matched all original hashes; clean original compile/smoke evidence reused, no strategy recompile or edits.
- Four fresh native runs and eight retained relevant runs audited. **1,240 executed-signal checks**, 568 from fresh runs, passed the independent H1 oracle. Repeated signals across overlapping runs are not independent samples.
- Native report/deal cash, fees, full close volumes, risk sizing, chronology, signal clock, control direction and date matching checked. This verifies executed signals, not every possible tick decision.
- Stage4 failed. Optimization, holdout selection, Monte Carlo, additional-cost stress, FTMO simulation, portfolio integration and deployment were **not run**. No research exception is assumed from Nasdaq’s earlier exception.
- No live orders, normal terminal restart, Ava connection, production SET, installer, website or Git push. Stop for review before GBPUSD.

Files: PROTOCOL.md, RESULTS.json, GATE.json, VERIFICATION.json, CARRYOVER_AUDIT.json, PROVENANCE.json and native/. RESULTS.json includes monthly closed-P&L breakdowns and links to reused evidence. The review ZIP excludes private connection INIs and raw identity-bearing reports/journals.
