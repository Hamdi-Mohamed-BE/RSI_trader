# Nasdaq trend-pullback — pipeline review

**Decision: stop at the raw qualification gate. No optimized winner or live-ready version.** Gold remains unchanged. Bitcoin and GBPUSD have not been advanced.

The unchanged Nasdaq H1 strategy returned **+57.13% over five years**, but its profit factor was only **1.130**, below the required 1.15. The three-year result was weaker: **+15.23%**, PF **1.075**, and below the frozen random-direction control. Recent strength does not erase the long-period failure. These are historical simulations, not expected future returns.

## Confirmed results

Native MT5 Model 4; Exness USTEC CFD, not NQ futures. USD 10,000 starting balance, nominal 1% equity risk rounded UP, broker-model costs and 150ms simulated execution delay. All periods end 2026-09-27 exclusive. The 3y/5y confirmations are new; the 6m/1y results are reused unchanged from the original study.

| Period / case | Trades | /month | /day | Return | PF | Win rate | Equity DD | W/L streak | Mean net R |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 5y strategy | 570 | 9.50 | 0.441 | +57.13% | 1.130 | 35.6% | 21.95% | 6/15 | 0.091 |
| 3y strategy | 347 | 9.64 | 0.448 | +15.23% | 1.075 | 36.0% | 22.04% | 6/15 | 0.052 |
| 1y strategy | 103 | 8.59 | 0.399 | +25.22% | 1.443 | 45.6% | 12.11% | 6/11 | 0.227 |
| 6m strategy | 56 | 9.26 | 0.427 | +24.62% | 1.819 | 51.8% | 5.92% | 6/3 | 0.403 |

The five-year window starts 2021-09-27; three years starts 2023-09-27; one year starts 2025-09-27; six months starts 2026-03-27. These overlapping, previously seen periods are not independent validations or untouched holdouts. /month uses elapsed calendar months (days / 30.4375); /day uses eligible quoted weekdays during the entry window, not only days with a trade. Streaks use net position P&L after recorded fees. Equity DD is the native report’s floating-equity relative maximum; it is not closed-balance DD.

## Control comparison

The control retains the same qualifying opportunities, stop/target distances and sizing, but randomizes direction using the original frozen seed 290929. Every entry date matched; timing differences are recorded in RESULTS.json. Compare mean net R as well as cash because compounding paths differ. This tests the direction signal conditional on selected opportunities, not whether the selected entry times themselves outperform random times. One seed is not a significance test.

| Period / case | Trades | /month | /day | Return | PF | Win rate | Equity DD | W/L streak | Mean net R |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 5y control | 570 | 9.50 | 0.441 | +54.45% | 1.142 | 35.3% | 22.50% | 6/9 | 0.088 |
| 3y control | 347 | 9.64 | 0.448 | +66.72% | 1.256 | 39.2% | 12.43% | 6/8 | 0.158 |
| 1y control | 103 | 8.59 | 0.399 | +11.08% | 1.185 | 39.8% | 11.19% | 6/8 | 0.110 |
| 6m control | 56 | 9.26 | 0.427 | +7.43% | 1.243 | 42.9% | 8.99% | 6/8 | 0.136 |

Raw gate failures:

- 3y: PF < 1.15.
- 3y: mean net R does not beat control.
- 3y: unresolved raw execution/carry flags.
- 3y: unresolved control execution/carry flags.
- 5y: PF < 1.15.
- 5y: unresolved raw execution/carry flags.
- 5y: unresolved control execution/carry flags.

Even if the carryover warnings were waived, the strategy still fails the performance gate. The conclusion is about this frozen implementation, not every Nasdaq trend strategy.

## Why the numbers differ from the earlier screen

The original +58.66% headline used the faster one-minute-OHLC Model 1 screen. Below are the retained screens, not new parameter variants. Model 4 changes the intrabar path and modeled execution; the EA and inputs were not changed.

| Period / case | Trades | /month | /day | Return | PF | Win rate | Equity DD | W/L streak | Mean net R |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 5y strategy | 570 | 9.50 | 0.441 | +58.66% | 1.135 | 35.6% | 21.14% | 6/15 | 0.092 |
| 5y control | 570 | 9.50 | 0.441 | +55.72% | 1.146 | 35.3% | 22.21% | 6/9 | 0.089 |
| 3y strategy | 347 | 9.64 | 0.448 | +17.04% | 1.084 | 36.0% | 21.21% | 6/15 | 0.056 |
| 3y control | 347 | 9.64 | 0.448 | +68.50% | 1.263 | 39.2% | 12.41% | 6/8 | 0.161 |

## Execution and overnight carryovers

The five-year Model 4 strategy had **29 positions closing more than two minutes past the eight-hour/20:00 UTC deadline**, including **13 crossing a UTC date** and 6 with nonzero swap. The longest hold was **79.50 hours**. Native entry failures, close failures, invalid stops/volume and stopouts were zero; that does not make these carryovers acceptable for a strict intraday mandate. All of these delayed exits closed within one second of the first recorded minute trace at/after their deadline. The table lists the cross-date cases; the full audit also lists same-day delays.

The unchanged EA closes on ticks and consults the broker’s weekday session schedule. Archived minute equity traces show whether there was tester activity around the intended deadlines. Gaps in that trace support missing modeled quote activity, but do not establish the exact holiday cause or prove a live fill would have been available. The session API describes sessions by weekday; it does not supply a full dated historical holiday calendar. [Official session API](https://www.mql5.com/en/docs/marketinformation/symbolinfosessiontrade).

| Position | Open UTC | Close UTC | Hours held | Minute-trace gap across deadline (h) | Net P&L | Swap |
|---|---|---|---:|---:|---:|---:|
| 44 | 2021-11-26T16:00:00+00:00 | 2021-11-28T23:30:00+00:00 | 55.50 | 53.27 | $-37.63 | $+0.00 |
| 124 | 2022-04-14T15:00:00+00:00 | 2022-04-17T22:30:00+00:00 | 79.50 | 74.53 | $+363.76 | $+0.00 |
| 156 | 2022-06-10T14:00:00+00:00 | 2022-06-12T22:30:00+00:00 | 56.50 | 50.53 | $+298.74 | $+0.00 |
| 206 | 2022-08-26T16:00:00+00:00 | 2022-08-28T22:30:00+00:00 | 54.50 | 50.53 | $+386.24 | $+0.00 |
| 580 | 2024-04-19T14:00:00+00:00 | 2024-04-21T22:00:00+00:00 | 56.00 | 50.03 | $+242.70 | $+0.00 |
| 670 | 2024-09-06T15:00:00+00:00 | 2024-09-08T22:00:00+00:00 | 55.00 | 50.02 | $+79.91 | $+0.00 |
| 674 | 2024-09-13T15:00:00+00:00 | 2024-09-15T22:00:00+00:00 | 55.00 | 50.02 | $-54.79 | $-42.30 |
| 704 | 2024-10-11T15:00:00+00:00 | 2024-10-13T22:00:00+00:00 | 55.00 | 50.02 | $-31.34 | $-42.51 |
| 734 | 2024-11-29T16:00:00+00:00 | 2024-12-01T23:00:00+00:00 | 55.00 | 52.77 | $+62.95 | $-46.07 |
| 820 | 2025-03-28T15:00:00+00:00 | 2025-03-30T22:00:00+00:00 | 55.00 | 50.02 | $+325.59 | $+0.00 |
| 834 | 2025-05-02T13:00:00+00:00 | 2025-05-04T22:00:00+00:00 | 57.00 | 50.02 | $+91.27 | $-22.83 |
| 986 | 2025-12-24T16:00:00+00:00 | 2025-12-25T23:00:00+00:00 | 31.00 | 28.77 | $+151.27 | $-24.57 |
| 1036 | 2026-04-03T12:00:02+00:00 | 2026-04-05T22:00:02+00:00 | 58.00 | 56.77 | $-208.43 | $-53.20 |

All carryovers and their P&L remain in the results. No hindsight removal, invented session-end fills or schedule fix was applied. Correcting this would require an explicitly specified new execution variant and separate validation. The complete timestamp audit covers both models and all windows; overlapping windows repeat the same historical situations.

Five-year initial stop risk: median **1.002%**, maximum **1.074%** of entry equity. Lot rounding and fills explain departure from the 1% target. Gaps and costs can increase realized loss further. Five-year closed-balance DD was **20.94%**, versus native floating-equity DD **21.95%**.

## Data limitations

The broker journal says recorded real ticks begin 2026-01-01. Model 4 is therefore mixed real/generated history, not five years of recorded real ticks. MT5 generates ticks when minute bars exist but their tick records are absent. [Official real/generated tick documentation](https://www.metatrader5.com/en/terminal/help/algotrading/tick_generation).

- 5y strategy native history label: 14% real ticks.
- 3y strategy native history label: 22% real ticks.
- 1y strategy native history label: 59% real ticks.
- 6m strategy native history label: 98% real ticks.

These labels include the 90-day warm-up, not just the trading window. Broker-specific spread, swap and commission modeling is not a verified historical fee time series. The 150ms setting is a simulation, not measured live slippage. No inference about another broker, futures contract or prop-firm account is warranted.

## Pipeline status and verification

- Stages 1–2: original frozen rules and tester-only binary reused without strategy edits; original source, EX5, rules and configuration hashes matched.
- Stage 3: four new serial long-window native confirmations plus eight retained raw/control screen and recent-period runs.
- Verification: **3,986 causal signal checks**, including **1,834** on fresh tests, with zero mismatches; deal/report cash, complete close volumes, risk sizing, input dates and matched-control dates reconciled. Repeated signals across overlapping tests are not independent observations.
- Stage 4: **failed**. No further parameter trials, optimized SET, Monte Carlo, FTMO simulation or promotion. Those stages were not completed and no robustness claim is made.
- Gold, the separately deployed Nasdaq 5-minute bot, installers, website and live trading were not changed.

The canonical pipeline says to stop on a raw failure. Exploratory optimization would require an explicit override and would remain research, not validation of this failed baseline. **Awaiting user review before any next asset or exception.**

Evidence: [frozen protocol](PROTOCOL.md), [full results](RESULTS.json), [gate](GATE.json), [verification](VERIFICATION.json), [carryover audit](CARRYOVER_AUDIT.json), [provenance](PROVENANCE.json). Private tester connection INIs are not intended for sharing.
