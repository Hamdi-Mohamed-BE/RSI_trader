# Gold intraday bias — pipeline result

**Not improved or validated yet. The unchanged strategy failed the native baseline gate. Optimization and Monte Carlo were not run. A material financing-model discrepancy needs resolving before deciding whether to rehabilitate this candidate. No live deployment.**

Tested rule: buy XAUUSD at 23:00 Europe/London (DST-aware), first quote within five minutes; close after 120 elapsed minutes from the fill. Fixed 0.10 lot, $10,000 initial balance, no stop-loss, 150ms simulated execution delay. This is a research baseline, not a 1%-risk strategy or a live recommendation. The tests use the isolated Exness-MT5Trial16 research environment; broker CFD findings do not automatically transfer to other accounts or gold futures.

## Native results, including configured spread, commission and swap

All windows end 27 September 2026 exclusive; starts are 27 March 2026, 27 September 2025, 27 September 2023 and 27 September 2021 respectively. The windows overlap and are not four independent replications.

| Window / model | Trades | /month | /data day | Net USD | Return | PF | Win rate | Equity DD | Longest W/L |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 6m / real-tick mode | 102 | 16.87 | 0.65 | +191.61 | +1.92% | 1.036 | 40.20% | 18.74% | 6/6 |
| 1y / real-tick mode | 200 | 16.68 | 0.64 | +2,537.96 | +25.38% | 1.198 | 47.00% | 15.67% | 6/7 |
| 3y / 1m OHLC | 599 | 16.64 | 0.64 | +1,926.84 | +19.27% | 1.103 | 42.57% | 19.32% | 7/16 |
| 5y / 1m OHLC | 1014 | 16.90 | 0.65 | -1,244.96 | -12.45% | 0.948 | 38.86% | 48.03% | 7/16 |

Trade/day uses the number of UTC dates with available gold bars; it is not trades per active strategy day. Return is fixed-lot cash P&L divided by the $10,000 starting balance, not an unleveraged price return. Drawdown is native marked-to-market relative equity drawdown. No initial stop means risk is not capped at 1%; a higher return from larger size would not establish an improved edge.

The frozen gate requires both three- and five-year native screens to have positive net P&L, PF at least 1.15, at least 30 trades and better mean P&L/trade than a valid control. Three-year PF fails; five-year net and PF fail independently of the control problem below. The recent year passes the PF threshold alone, but cannot override the longer-window failures. The most recent six months are marginal after configured costs.

## Financing is material — diagnostic, not a corrected backtest

The following decomposition preserves the same native fills, spread, commission and size. The last column removes only the recorded swap arithmetically. It does not constitute a second executable backtest, a verified swap-free account or a passed pipeline.

| Window | Fill-based price P&L | Commission | Recorded swap | Native net | PF excluding only swap |
|---|---:|---:|---:|---:|---:|
| 6m | $+1,098.91 | $-56.10 | $-851.20 | $+191.61 | 1.217 |
| 1y | $+4,316.76 | $-110.00 | $-1,668.80 | $+2,537.96 | 1.351 |
| 3y | $+7,301.89 | $-329.45 | $-5,045.60 | $+1,926.84 | 1.429 |
| 5y | $+7,847.14 | $-557.70 | $-8,534.40 | $-1,244.96 | 1.376 |

Every raw position in these ledgers avoids 17:00 New York, yet receives a swap charge. Positions cross UTC midnight; that pattern is consistent with a tester financing-clock mismatch, but the accrual timestamp itself is not separately logged. Do not read this as proof that the live broker charged incorrectly.

Exness currently documents swap at 21:00 GMT in summer / 22:00 GMT in winter, and states its MetaTrader servers use GMT+0. These raw positions begin at 22:00 or 23:00 UTC, after that published rollover, and close roughly two hours later. The current articles do not establish historical rates, holiday exceptions, or account-specific swap-free eligibility across 2021–2026. Sources: [Exness swap schedule](https://get.exness.help/hc/en-us/articles/360014709151-About-swap), [Exness server timezone](https://get.exness.help/hc/en-us/articles/360014390760-What-is-the-default-timezone-set-for-MetaTrader).

**This supports keeping gold as an unresolved research candidate, not promoting it or declaring the underlying price pattern dead.** Before restarting the gate, establish the intended broker/account's actual rollover time and financing treatment, then implement and freeze a validated cost model. Do not just turn off swap because it improves the result. An accurate accounting repair is not a newly discovered strategy improvement.

## Execution/data qualifications

- 6m: native history quality says **100% real ticks**; observed holding times 120.00–120.02 minutes; no raw entry/close failures.
- 1y: native history quality says **72% real ticks**; observed holding times 120.00–120.02 minutes; no raw entry/close failures.
- 3y: native history quality says **98%**; observed holding times 120.00–120.17 minutes; no raw entry/close failures.
- 5y: native history quality says **98%**; observed holding times 120.00–122.00 minutes; no raw entry/close failures.

Real ticks begin 1 January 2026 on this feed. Therefore the one-year real-tick-mode run includes generated history, while the six-month run reports 100% real ticks. The three-/five-year runs are one-minute-OHLC screens, not long-horizon real-tick confirmations. “98% history quality” in those screens is not “98% real ticks.” The [MetaTrader documentation](https://www.metatrader5.com/en/terminal/help/algotrading/testing) describes modeling modes and the simulated execution delay.

The smoke run reconciles, but its final raw position was closed administratively at test end after 119.42 minutes. That exception is retained, not presented as a normal scheduled exit. No such forced end-of-test close occurred in the four principal raw runs.

## Control diagnostics — not valid pass/fail benchmarks

The fixed random-clock controls attempted exits during market-closed periods (retcode 10018), and some positions lasted up to 301 minutes. The unmodified smoke control also had an extended hold without a close rejection because no executable quote arrived at the intended exit. These controls are not clean two-hour comparators. Their cash ledgers are retained for transparency, but **no claim that gold beats/loses to a valid control is made**. Correct session-aware control construction is required before advancing.

| Window / model | Trades | /month | /data day | Net USD | Return | PF | Win rate | Equity DD | Longest W/L |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 3y / 1m OHLC | 663 | 18.41 | 0.71 | +3,259.54 | +32.60% | 1.123 | 50.68% | 22.06% | 8/8 |
| 5y / 1m OHLC | 1108 | 18.47 | 0.71 | +1,521.84 | +15.22% | 1.044 | 49.01% | 24.79% | 8/8 |

Native log counts include overlapping terminal/agent copies, so they must not be interpreted as unique rejected orders. Three-/five-year raw trades themselves had zero close failures; their own PF/net gates fail regardless. Recent control reruns and long-horizon real-tick confirmations were not pursued after rejection.

## Why this differs from the earlier promising gold result

The earlier M5 discovery used fixed-notional, spread-only bar returns; no commission, actual native fills, or native financing. This study uses fixed lots and native execution. Returns are therefore not directly comparable. Also, the old screen discarded windows based on future missing bars. That is a retrospective executability filter; the new EA makes decisions causally and does not discard trades because future data will be incomplete.

| Native window | Previous selected trades | Native trades | Matched five-minute entry slots | Native-only slots | Previous-only slots |
|---|---:|---:|---:|---:|---:|
| 6m | 102 | 102 | 102 | 0 | 0 |
| 1y | 199 | 200 | 199 | 1 | 0 |
| 3y | 597 | 599 | 597 | 2 | 0 |
| 5y | 1011 | 1014 | 1011 | 3 | 0 |

Matching entry slots does not imply identical prices, exit times or costs. The old final-year gold PF of about 1.48 did not pass its original neighboring-time stability and multiple-testing checks. Those failures remain on record. We have already examined that year, so it cannot serve as a fresh holdout for a refined strategy. Reserved older history was not opened for optimization or selection during this run.

## How far the full pipeline got

1. Frozen rules, cost treatment, control, windows, search space and gate: recorded before native results.
2. Tester-only EA: compiled with zero errors/warnings. Cash/time/build audits complete, with the smoke boundary and control-session exceptions documented.
3. Native evidence: two smoke tests, four long-window screens, two recent raw audits — eight runs total.
4. Raw gate: **not passed**; financing validity and control construction also remain unresolved.
5. Optimization, new finalist selection and reserved-period replication: **not started**, per the frozen failure gate. Zero tuning configurations evaluated.
6. Monte Carlo, FTMO simulation and portfolio overlap: **not run**; there is no selected, validated improved candidate to stress-test.
7. Production, deployment, website and account changes: **not authorized and not performed**.

A report-only JSON boolean bug was repaired after the screens: the failed gate is now an actual `false`, and continuation requires `passed is True`. Control execution validity was added to the gate. Neither repair changes the EA, frozen strategy, input file or fills; all four build hashes remain unchanged. The raw gate had already failed on its own economics.

## Evidence and next decision

See [frozen protocol](PROTOCOL.md), [machine-readable results](RESULTS.json), [verification](VERIFICATION.json) and the archived reports, deal ledgers, traces and journals under `native/`. All cash calculations were independently reconciled and timestamps checked against IANA timezone rules. Account/configuration credentials are not reproduced in this report.

Next useful step: verify the target account's real financing/session specifications, repair the cost/control implementation, rerun the unchanged baseline, and only if it passes resume the already-frozen optimization plan. This report does not show that optimization improved gold. It shows precisely what must be resolved before that claim can be tested honestly.
