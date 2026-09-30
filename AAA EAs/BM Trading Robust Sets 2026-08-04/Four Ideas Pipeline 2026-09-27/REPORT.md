# Four screenshot strategies — pipeline outcome

Completed 2026-09-27. **No version is approved for production or FTMO deployment.**

All four raw strategies went through the frozen qualification gate. Only USDJPY morning breakout passed and proceeded to staged parameter optimization. Its validation-selected candidate failed the one-time historical holdout, so that branch stopped too. This is a completed rejection decision, not a claim that every possible variation was optimized or that the chance of funding is zero.

## Work completed

- 36 new native MT5 raw/control evaluations: 16 Model 1 screens, 16 Model 4 long-window confirmations, and four Model 4 six-month runs. The existing eight one-year strategy/control reports were reused without modification.
- Three passive native session/quote-coverage probes; they cannot submit trades.
- Two one-year native parity checks: the original handler and the extended engine at raw settings both match the original completed trades exactly.
- 384 staged optimizer evaluations covering 339 distinct parameter vectors, including the neighbourhood checks. Repeated baselines and inactive-field duplicates are retained and counted conservatively, not claimed as independent discoveries.
- Three separate-period native finalist validations and one historical holdout. No re-tuning after the holdout failed.
- Independently rechecked 19,952 extended raw/control trades: cash totals, orders, clocks, geometry, historical SMA inputs, costs and scheduled-exit delays. Reviewed optimizer manifests, source/binary/report hashes and final native cash ledgers.
- All research builds compiled with zero errors and zero warnings. No live trading API calls, production EA changes, BAT changes, website changes, account changes or Git push.

## Raw results — all requested windows

Periods end 2026-09-27 exclusive; starts are 2026-03-27, 2025-09-27, 2023-09-27 and 2021-09-27. Windows overlap and are not independent experiments. Returns are total-period returns, not annualized.

Separate $10,000 native research accounts, Exness-MT5Trial16, 150 ms simulated execution delay and recorded bid/ask/commission/swap. Breakouts use 1% current-equity intended stop risk rounded UP, which is not a guaranteed loss cap. The no-stop US30 and US100 daily-long strategies use $10,000 fixed initial notional rounded DOWN, NOT 1% risk. Do not compare these as equally risky portfolios.

Win rate, PF and streaks are based on net completed-trade results; drawdown is native maximum relative floating-equity drawdown. Frequency includes weekdays with no trades.

| Strategy | Window | Trades | /month | /weekday | Return | Net PF | Net win | Equity DD | Max W/L |
|---|---|---|---|---|---|---|---|---|---|
| USDJPY morning range breakout | 6m | 127 | 21.0 | 0.97 | 19.95% | 1.36 | 42.52% | 24.35% | 17/10 |
| USDJPY morning range breakout | 1y | 252 | 21.0 | 0.97 | 25.24% | 1.21 | 42.86% | 32.21% | 17/10 |
| USDJPY morning range breakout | 3y | 759 | 21.1 | 0.97 | 167.19% | 1.28 | 44.01% | 32.06% | 17/11 |
| USDJPY morning range breakout | 5y | 1178 | 19.6 | 0.90 | 246.22% | 1.24 | 43.97% | 32.02% | 17/14 |
| US30 Turnaround Tuesday | 6m | 7 | 1.2 | 0.05 | 4.21% | 3.98 | 71.43% | 2.08% | 4/2 |
| US30 Turnaround Tuesday | 1y | 16 | 1.3 | 0.06 | 11.18% | 4.22 | 81.25% | 3.28% | 11/2 |
| US30 Turnaround Tuesday | 3y | 53 | 1.5 | 0.07 | 20.49% | 2.20 | 71.70% | 7.68% | 11/2 |
| US30 Turnaround Tuesday | 5y | 58 | 1.0 | 0.04 | 21.74% | 2.16 | 70.69% | 7.60% | 11/2 |
| US100 daily long | 6m | 130 | 21.5 | 0.99 | 21.38% | 1.39 | 57.69% | 12.12% | 11/6 |
| US100 daily long | 1y | 258 | 21.5 | 0.99 | 11.53% | 1.10 | 53.10% | 13.63% | 11/6 |
| US100 daily long | 3y | 772 | 21.4 | 0.99 | 35.43% | 1.11 | 54.27% | 28.69% | 11/8 |
| US100 daily long | 5y | 848 | 14.1 | 0.65 | 31.46% | 1.09 | 53.54% | 29.67% | 11/8 |
| US100 New York ORB | 6m | 130 | 21.5 | 0.99 | -12.37% | 0.79 | 46.92% | 25.86% | 9/6 |
| US100 New York ORB | 1y | 256 | 21.3 | 0.98 | -9.90% | 0.91 | 47.27% | 25.94% | 9/6 |
| US100 New York ORB | 3y | 770 | 21.4 | 0.98 | 17.05% | 1.04 | 49.48% | 25.94% | 9/6 |
| US100 New York ORB | 5y | 1285 | 21.4 | 0.98 | 27.38% | 1.04 | 48.95% | 25.89% | 9/8 |

## Frozen raw gate and decision

Both 3y and 5y must have positive net P&L, net PF >=1.15, >=30 trades, and higher return/equity-DD than the predeclared control. This last measure operationalizes the canonical pipeline's “better than control” requirement and was frozen before the extended tests. A failing strategy is not optimized solely to rescue its backtest.

| Strategy | 3y return/DD | 3y control return/DD | 5y return/DD | 5y control return/DD | Decision |
|---|---|---|---|---|---|
| USDJPY morning range breakout | 5.21 | -0.81 | 7.69 | -0.86 | PASS_NUMERIC_GATE |
| US30 Turnaround Tuesday | 2.67 | 3.73 | 2.86 | 4.19 | FAIL |
| US100 daily long | 1.23 | 1.66 | 1.06 | 0.31 | FAIL |
| US100 New York ORB | 0.66 | 0.06 | 1.06 | -0.04 | FAIL |

- **USDJPY morning breakout:** passes raw numeric gate; 32% equity DD at raw risk is already a serious risk issue. Proceeded to optimization, then rejected on holdout.
- **US30 Turnaround Tuesday:** PF looks good, but the 25-day SMA filter does not beat unfiltered Monday longs on the frozen risk-adjusted comparison. No-stop sizing and missing early overnight quotes are additional limitations. Not optimized.
- **US100 daily long:** net PF 1.11 / 1.09 on 3y / 5y, below 1.15. Strong recent performance does not override the long-window failure. Not optimized.
- **US100 NY ORB:** net PF about 1.04 on both long windows and a losing last year/six months. Not optimized.

## What USDJPY optimization tested

Staged search on 2021-09-27–2024-03-27. Top three development candidates were carried through applicable dimensions: M1 through H4 signal timeframes; pending/closed-bar/confirmation/retest entries; range, ATR, fixed, percentage, candle and swing stops; BE, ATR, percent, MA, swing, chandelier and step-lock trailing; 0.5R through 6R, no TP and other exits; shifted intraday ranges; direction; filters; weekdays; reentry/trade counts; max hold; entry buffer and range duration.

D1 has no completed same-day signal before the intraday exit. Pyramiding/weekend holds are outside this one-position intraday hypothesis. A separate next-bar market entry duplicates the first available tick after a completed bar. News and volatility-regime overlays were not run without a complete matched point-in-time dataset. This is the frozen applicable staged grid, not an exhaustive Cartesian search of every conceivable strategy.

| Stage | Evaluations |
|---|---|
| timeframe_entry | 29 |
| entry | 15 |
| stop | 48 |
| trailing | 75 |
| exit | 49 |
| session | 18 |
| direction | 9 |
| filters | 18 |
| management | 33 |
| range_duration | 9 |
| neighborhood-0 | 27 |
| neighborhood-1 | 27 |
| neighborhood-2 | 27 |

Neighbourhood audit: each of the three finalists had 27 evaluations but only **nine distinct active neighbouring combinations**. The step-lock variant ignores the trailing-distance field used as the third coordinate, causing equal triplication; the range-time and exit-time coordinates remain active. All nine active neighbours were profitable on development. This does not establish robustness across market regimes; the holdout disproved it.

## Native finalist results on separate periods

Validation: 2024-03-27–2025-09-27. Candidate selected using the predeclared net-PF/return-DD score, not by inspecting holdout outcomes. All three validation runs had unacceptable drawdown for deployment.

| Candidate | Trades | /month | /weekday | Return | Net PF | Net win | Equity DD | Max W/L |
|---|---|---|---|---|---|---|---|---|
| 0 | 806 | 44.7 | 2.05 | 265.70% | 1.02 | 28.78% | 91.81% | 7/20 |
| 1 (selected) | 784 | 43.5 | 1.99 | 651.29% | 1.04 | 29.21% | 86.40% | 7/25 |
| 2 | 868 | 48.1 | 2.21 | -94.90% | 0.88 | 27.30% | 98.12% | 8/39 |

Historical holdout: **2020-09-27–2021-09-27**, tested once on the selected candidate. It is an earlier unused regime, not a prospective forward test. The already-inspected most recent year was not called an untouched holdout.

| Evidence | Trades | /month | /weekday | Return | Net PF | Net win | Equity DD | Max W/L |
|---|---|---|---|---|---|---|---|---|
| Selected candidate: held-out year | 446 | 37.2 | 1.72 | -98.86% | 0.20 | 17.71% | 98.99% | 4/34 |

**Rejected settings — do not deploy:** range 09:00–13:00 on the declared synthetic broker clock (NY+7); pending stops both sides, cancel opposite on fill; initial stop 0.5 × ATR(14,M1); no TP; step-lock trailing starts at 1R, with the tested 0.5R-step/0.2R-lock formula; up to three entries with stop-exit reentry; flat 20:00; no direction or extra filter. These are substantially changed research settings, not the original screenshot rules.

The selected candidate ended the validation period at +651.29%, but lost 86.4% from an equity peak along the way. On the held-out year it reduced $10,000 to **$113.93**. A large final return alone would have selected an unsuitable strategy.

## FTMO suitability: no candidate to add

FTMO 2-Step uses 10% / 5% phase targets, a 5% daily loss amount, a static 10% maximum-loss amount, and at least four trading days per evaluation phase. Daily equity includes floating P&L, swaps and commissions and resets at 00:00 CE(S)T. On $10,000, the relevant daily amount is $500 and the static initial equity floor is $9,000. [Official objectives](https://ftmo.com/en/trading-objectives/).

The official current symbol API reports USDJPY contract size 100,000 USD and Swing leverage 1:30. [FTMO symbol specifications](https://ftmo.com/en/symbols/) / [official data](https://ftmo.com/wp-json/ftmo/symbols). This was checked on 2026-09-27; account-specific settings must still be verified before any future deployment.

- **validation-1**: first trade 5.22 lots; required standalone margin at 1:30 is $17,400.00, versus $10,000 starting equity. 772 of 784 filled Exness-replay orders require more than the ENTIRE equity-at-placement under the FTMO leverage counterfactual.
  Median native round-trip commission consumed 0.214% of equity, on top of intended stop risk. Maximum fill-to-original-stop exposure reached 7.50% before fees.
  The Exness replay closed balance first went below $9,000 at 2024-03-29T10:40:35 UTC, after trade 7, at $8,049.88.

- **holdout**: first trade 26.32 lots; required standalone margin at 1:30 is $87,733.33, versus $10,000 starting equity. 446 of 446 filled Exness-replay orders require more than the ENTIRE equity-at-placement under the FTMO leverage counterfactual.
  Median native round-trip commission consumed 0.461% of equity, on top of intended stop risk. Maximum fill-to-original-stop exposure reached 2.56% before fees.
  The Exness replay closed balance first went below $9,000 at 2020-09-30T10:09:21 UTC, after trade 6, at $8,999.00.

These are **diagnostic counterfactuals, not an executable FTMO backtest or pass probability**. FTMO margin would reject or reduce many orders, producing a different trade path. Maximum relative equity DD is also not the same thing as FTMO's static loss rule. The early closed-balance violations above are a separate explicit check, not an inference from the DD percentage.

No pass/funding/payout percentages are reported: the candidate failed economic validation and its native sizing is not FTMO-executable. No Monte Carlo, full FTMO lifecycle or portfolio-addition simulation was run after the holdout stop gate. A failed held-out strategy should not be rehabilitated by reshuffling the same trades or selecting a replacement using that now-exposed holdout.

## Data, sessions and execution limitations

- Model 4 real-tick coverage: 6m 100%, 1y 73%, 3y 24%, 5y 14%. The separate validation and historical holdout were **0% real ticks**, generated from the available broker bars. Model 4 is not synonymous with an all-real-tick history. The fast Model 1 reports' “100%” quality is not a real-tick claim. [MetaTrader tick modelling](https://www.metatrader5.com/en/terminal/help/algotrading/tick_generation).
- Passive five-year coverage probes show no US30/USTEC quotes at the required synthetic-broker 01:05 entry minute through May 2023. Entries become available in June 2023. The no-stop strategies' nominal five-year runs therefore do not represent five years of usable entry-session coverage.
- Current native index trade-session metadata closes 21:00–22:00 UTC on weekdays. The intended winter 23:50 synthetic-broker exit is 21:50 UTC, inside that closure. Historical holiday/quote availability also matters. Delayed closes are retained in the evidence, not silently moved earlier. These are broker-constrained reproductions; source-broker and FTMO session parity is not established.
- This rejection is not proof that every implementation of the screenshot concepts fails universally. It is a conclusion about these explicit rules, controls, available data and frozen search.
- Simulated 150 ms delay is not measured live slippage. No invented measured-cost stress was supplied. Historical broker spec/commission/swap schedules and FTMO fills were not reconstructed.

## Integrity and handoff

Original raw source/rules/build hashes remained unchanged. All extended native reports reconcile to their deals. The independent FX arithmetic check records 63 small conversion-price approximation exceptions (maximum $1.76) rather than assuming that the conversion quote equals the stop execution price; exact report/deal net-cash reconciliation remains enforced.

Artifacts: `GATE.json` (all raw net stats); `TIMING_COVERAGE.json` (monthly quote/session evidence); `Optimization/SEARCH_RESULTS.json` (all trials); `Optimization/VALIDATION.json`, `SELECTED.json`, `HOLDOUT_GATE.json`, `STOP.json`; `FINAL_CHECKS.json` (independent checks); compressed native reports/journals in both native folders. See both frozen protocols for interpretation and scope.

**Recommendation: leave the current trading system and FTMO configuration unchanged.** The raw USDJPY idea remains a research lead only. Any follow-up would need a newly frozen broker-executable risk/cost specification and fresh validation data, not a silent fallback chosen after this failed holdout.
