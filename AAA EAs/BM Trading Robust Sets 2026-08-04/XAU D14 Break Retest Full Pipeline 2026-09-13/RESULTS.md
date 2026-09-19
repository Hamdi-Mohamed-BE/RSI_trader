# XAU D14 / H1 / M5 break and retest — full optimization results

Verdict: **NOT APPROVED FOR DEPLOYMENT**.

This is a bounded, staged parameter search, not proof of a globally best strategy. XAUUSD only. US100, the live portfolio, installers and website remain unchanged. All money below is simulated, not earned income.

Completed 165 native MT5 runs; 115 distinct parameter settings and 117 setting/delay combinations counted for conservative multiple-testing adjustment. All 165 native signal/accounting audits passed; 14 independent unit tests passed; raw-default parity reproduced all seven recent raw trades, fills and costs exactly.

## Selected configuration

Selected using development and validation only, then frozen before evaluating its final-year outcome. This is the best finalist under the predeclared score, not necessarily the highest-return or highest-win-rate configuration in every period.

| Setting | Selected value |
|---|---|
| Direction | Long only |
| Daily filter | Last 14 completed D1 candles; compare older/newer seven-bar high-low ranges; mixed direction = no entry |
| H1 structure | Strict swing with 1 completed bars on each side; break after the intervening opposite swing |
| H1 zone | Entire broken origin candle |
| M5 holding | At least two rejection wicks in 3 consecutive completed bars; entire body outside zone |
| M5 entry | Confirmed 2-bar-each-side swing, higher low/lower high and closing break; entry on next available tick |
| Stop | Last M5 swing + one tick + 0.25 x closed M5 ATR(14), beyond the swing |
| Take profit | 1R reward for 1R risk, before trading costs |
| Trailing / BE | Off |
| Time exit | 6 elapsed hours; checked once per M5 bar on an available tick |
| Maximum zone age | No extra age limit; normal structural invalidation remains |
| Entry session | 00:00–24:00 broker time |
| Sizing | 1% of current equity target; round UP to broker lot step / minimum lot; one position, no martingale |

## Raw versus selected — same starting capital and windows

Each window starts independently at $10,000. Returns and PF include recorded commission and swap; spread is embedded in native fills. DD is maximum relative floating-equity drawdown, not just closed-balance DD.

| Window | Version | Trades | Net win rate | Net return | Net USD | Net PF | Equity DD |
|---|---|---|---|---|---|---|---|
| 6m | Raw | 7 | 28.57% | -1.24% | $-124.04 | 0.76 | 5.20% |
| 6m | Selected | 10 | 80.00% | +7.27% | $726.77 | 5.01 | 2.03% |
| 1y | Raw | 15 | 53.33% | +9.13% | $912.74 | 2.12 | 5.27% |
| 1y | Selected | 30 | 53.33% | +3.68% | $367.51 | 1.27 | 8.51% |
| 3y | Raw | 41 | 43.90% | +10.80% | $1,080.26 | 1.41 | 7.56% |
| 3y | Selected | 77 | 59.74% | +16.01% | $1,601.27 | 1.49 | 8.45% |
| 5y | Raw | 66 | 36.36% | +0.80% | $79.64 | 1.02 | 17.52% |
| 5y | Selected | 115 | 59.13% | +21.21% | $2,121.18 | 1.41 | 8.58% |

## Evidence separation

| Role | From / to exclusive | Trades | Net win rate | Net return | Net USD | Net PF | Equity DD |
|---|---|---|---|---|---|---|---|
| Development | 2021.09.05 / 2024.09.05 | 62 | 62.90% | +14.46% | $1,446.49 | 1.61 | 3.89% |
| Selection validation | 2024.09.05 / 2025.09.05 | 23 | 56.52% | +2.63% | $262.65 | 1.27 | 4.39% |
| Search-excluded final year | 2025.09.05 / 2026.09.05 | 30 | 53.33% | +3.68% | $367.51 | 1.27 | 8.51% |

The original raw results in the final year were already inspected before this search. It was excluded from parameter selection, but it is NOT a genuinely unseen prospective holdout. The overlapping 3y/5y totals also include development/selection data; they must not be presented as out-of-sample results.

## Fees, losses and trade duration

| Window | Commission | Swap | Average win | Average loss | Worst trade | Longest losing streak | Average hold |
|---|---|---|---|---|---|---|---|
| 6m | $-5.49 | $0.00 | $113.50 | $-90.62 | $-105.06 | 1 | 2.02h |
| 1y | $-19.89 | $0.00 | $107.90 | $-97.06 | $-113.62 | 8 | 1.50h |
| 3y | $-105.41 | $-146.02 | $105.49 | $-104.88 | $-124.03 | 8 | 2.14h |
| 5y | $-199.29 | $-153.52 | $106.66 | $-109.19 | $-136.34 | 8 | 1.81h |

Five-year planned stop-risk range after lot rounding: 1.000%–1.169% of pre-entry equity. That target excludes commission and gap/slippage losses. Entry and exit costs are included in the reported net outcomes. Fees/swaps are what this MT5 test charged under its loaded broker specifications; historical fee-rate changes were not independently reconstructed.

Longest observed holding time: 54.67 hours. The six-hour time exit is checked on available M5-bar ticks and cannot guarantee an exit while the market is closed. It is not a six-hour hard wall-clock holding cap.

## Lower-risk and execution-delay controls

| Control | Trades | Net win rate | Net return | Net USD | Net PF | Equity DD |
|---|---|---|---|---|---|---|
| 0.5% risk — 1y | 30 | 53.33% | +2.19% | $219.18 | 1.31 | 4.68% |
| 0.5% risk — 5y | 115 | 59.13% | +10.36% | $1,036.26 | 1.41 | 4.54% |
| 500ms execution delay — 1y | 30 | 53.33% | +3.58% | $358.12 | 1.26 | 8.53% |
| 2000ms execution delay — 1y | 30 | 53.33% | +3.64% | $363.78 | 1.26 | 8.58% |

These are native reruns. Lower-risk control retains broker round-up/minimum-lot behavior, so it need not halve results exactly. Delay is fixed, not a claim to simulate every real news/slippage/connection condition.

Management-screen activity: 0 successful trailing/BE updates and 8 time exits across repeated management tests. Both leading exit configurations had 1R hard targets; their 1R/1.5R management triggers produced no trailing updates before take profit. Thus those no-op trials do not establish that trailing improves the strategy, nor provide native branch coverage for active trailing. The selected variant does not use trailing.

## Additional cost stress

| Window | Base net USD | Stressed net USD | Stressed return | Stressed PF | Extra spread | Extra commission | Extra swap |
|---|---|---|---|---|---|---|---|
| 1y | $367.51 | $336.44 | +3.36% | 1.24 | $21.12 | $9.95 | $0.00 |
| 5y | $2,121.18 | $1,439.68 | +14.40% | 1.26 | $428.33 | $99.64 | $153.52 |

This sensitivity keeps realized trades, prices and lots fixed, then subtracts one more measured entry spread, 50% more recorded negative commission and another recorded negative swap. It is not a fresh execution simulation and does not model changed signals or margin.

## Restricted-family walk-forward

| Prior training | Following test | Trades | Net return | Net PF | Equity DD |
|---|---|---|---|---|---|
| 2021.09.05 / 2023.09.05 | 2023.09.05 / 2024.09.05 | 27 | -4.70% | 0.77 | 9.42% |
| 2022.09.05 / 2024.09.05 | 2024.09.05 / 2025.09.05 | 25 | +14.03% | 2.03 | 4.94% |
| 2023.09.05 / 2025.09.05 | 2025.09.05 / 2026.09.05 | 27 | -3.80% | 0.81 | 9.08% |

Profitable folds: 1/3. Normalized compounded realized return: +4.54%. Each native fold starts at $10,000. The normalized stitch is not a separately rerun continuous MT5 account.

This tests a smaller, eight-anchor structural family fixed before the search. Each fold selects only from its own previous two years. It does NOT represent full reoptimization of every exit/filter in each fold.

## Local parameter stability

87.5% of eight one-parameter neighbours were profitable in the selection-validation year; minimum required was 60%. No winner was reselected from these neighbours.

| Changed setting | Trades | Net USD | Net PF | Equity DD |
|---|---|---|---|---|
| InpH1Pivot=2 | 20 | $569.30 | 1.81 | 2.53% |
| InpM5Pivot=1 | 31 | $554.63 | 1.42 | 3.51% |
| InpTargetR=0.75 | 23 | $-1.88 | 1.00 | 5.33% |
| InpTargetR=1.25 | 23 | $551.67 | 1.55 | 3.63% |
| InpStopBufferATR=0.2 | 23 | $242.17 | 1.24 | 4.60% |
| InpStopBufferATR=0.35 | 23 | $478.04 | 1.54 | 3.75% |
| InpHoldBars=2 | 21 | $278.21 | 1.31 | 4.24% |
| InpHoldBars=4 | 24 | $359.17 | 1.36 | 4.46% |

## 10,000-path uncertainty checks

| Window / costs | Return P5 | Return median | Return P95 | DD P95 | PF P5 | Positive paths |
|---|---|---|---|---|---|---|
| 1y | -6.80% | +3.70% | +15.85% | 10.04% | 0.52 | 70.99% |
| 1y-stressed | -7.10% | +3.40% | +15.50% | 10.26% | 0.50 | 69.29% |
| 5y | +1.33% | +21.06% | +44.77% | 11.73% | 1.00 | 96.24% |
| 5y-stressed | -4.85% | +14.40% | +37.18% | 14.41% | 0.90 | 88.46% |

Conditional five-calendar-day circular block resampling includes inactive days over the full window. PF is resampled separately in five-trade blocks. Drawdown is CLOSED P&L only, not floating-equity DD. These are sensitivity distributions conditional on historical trades, NOT probabilities of future profitability, guaranteed income or FTMO challenge passes.

| Window | Win-rate Wilson 95% range | Approx. deflated Sharpe diagnostic | Recent-half PF |
|---|---|---|---|
| 1y | 36.14%–69.77% | 2.62% | 1.24 |
| 5y | 49.99%–67.68% | 24.28% | 1.31 |

The common multiple-testing Sharpe adjustment is a heuristic with an assumed trial dispersion, not a calibrated probability; the tested parameters are correlated. The primary bootstrap above includes full calendar boundaries; the older common audit starts/ends at the first/last trade.

## Frozen acceptance gates

| Gate | Result |
|---|---|
| eligible train validation | PASS |
| positive train | PASS |
| positive validation | PASS |
| positive final year | PASS |
| final year pf at least 1 2 | PASS |
| final year minimum 30 trades | PASS |
| final year equity dd at most 15 | PASS |
| positive cost stressed final year | PASS |
| at least 60pct positive neighbours | PASS |
| walk forward positive | PASS |
| two of three walk forward folds positive | FAIL |
| bootstrap p05 return positive | FAIL |
| all common calyx gates clear | FAIL |

Common audit failures: bootstrap_return_p05_positive, bootstrap_pf_p05_above_1, deflated_sharpe_95pct.

## Calendar-year breakdown of the selected 5y run

| Year | Closed trades | Net USD | Commission | Swap | Win rate | Net PF |
|---|---|---|---|---|---|---|
| 2021 | 8 | $393.56 | $-20.19 | $0.00 | 75.00% | 2.83 |
| 2022 | 17 | $34.85 | $-37.33 | $0.00 | 52.94% | 1.04 |
| 2023 | 17 | $272.78 | $-42.77 | $0.00 | 58.82% | 1.36 |
| 2024 | 26 | $529.92 | $-52.60 | $-153.52 | 61.54% | 1.53 |
| 2025 | 35 | $348.24 | $-39.45 | $0.00 | 54.29% | 1.19 |
| 2026 | 12 | $541.83 | $-6.95 | $0.00 | 66.67% | 2.14 |

2021 and 2026 are partial years. All 61 touched calendar months, including zero-trade months, are in selected-5y-monthly.csv; the first/last month is partial. Monthly USD is simulated realized account profit, not payout income.

## Data coverage and implementation audit

| Window | From / to exclusive | MT5 reported history quality | Native execution errors |
|---|---|---|---|
| 6m | 2026.03.05 / 2026.09.05 | 100% real ticks | 0 |
| 1y | 2025.09.05 / 2026.09.05 | 67% real ticks | 1 |
| 3y | 2023.09.05 / 2026.09.05 | 22% real ticks | 1 |
| 5y | 2021.09.05 / 2026.09.05 | 13% real ticks | 1 |

Real ticks on this feed begin 2026-01-01. Earlier history uses generated ticks even though model 4 was requested. Preliminary search used native one-minute OHLC; finalists and published windows were rerun in model 4. No claim of five complete years of real ticks is made. All windows end at 2026-09-05 exclusive; September 5–13 is not tested here.

Independent audits check completed D1/H1/M5 candles, right-side pivot confirmation, zone boundaries/invalidation, wick conditions, stop/target arithmetic, one attempt per zone, nonoverlapping positions, ratcheting stops and time exits when used, and reconciliation of trade P&L/commission/swap with native reports. Passing these checks reduces known implementation risk but cannot prove absence of every bug.

Rejected/error details for the published windows: {"6m": {}, "1y": {"market closed": 1}, "3y": {"market closed": 1}, "5y": {"market closed": 1}}. Overlapping windows repeat the same rejected event; these counts must not be added as separate real incidents. A native market-closed rejection describes tester behavior under the loaded sessions, not independently verified historical session availability.

## Saved evidence

- PLAN.md: predeclared scope, score, search and acceptance gates.
- frozen-selection.json: parameter freeze and all five finalists.
- Backtest Reports/: native MT5 reports and equity graphs.
- Audit/: event records, native journals and per-trade JSON.
- selected-5y-trades.csv: every trade, stop, target, commission, swap, net P&L and initial-risk R.
- selected-5y-monthly.csv: calendar months including inactive months.
- all-native-runs.csv: every test, including losing/rejected variants.
- audit-results.json and Enhanced Audit/: uncertainty and stress evidence.
- Sets/SELECTED RESEARCH ONLY - XAU D14 Break Retest.set: frozen settings.
- EA/: tester-only source and compiled EA; refuses live initialization.

EA source SHA-256: `5101e6594ac3bfc4bbadcc8a557ca98c76593964d248aef0c74b76b2cfb2e666`.

Method references: [MT5 testing reports](https://www.metatrader5.com/en/terminal/help/algotrading/testing_report) and [MT5 tick generation](https://www.metatrader5.com/en/terminal/help/algotrading/tick_generation).
