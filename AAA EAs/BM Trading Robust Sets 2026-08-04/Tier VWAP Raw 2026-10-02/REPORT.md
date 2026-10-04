# VWAP mean reversion — raw baseline

Both assets fail the raw gate.

Anchor at 09:30 NY; first completed M5 rejection/reclaim of ±2 weighted SD after 10:00 and before 15:00; buy lower-band rejection or sell upper-band rejection. Enter next tick, target signal-close VWAP, 1:1 initial stop. One signal attempt per day, 1% current-balance requested risk; request flat at 15:30 NY or session pre-close.

| Asset / window | Net return | Net PF | Win rate | Native equity DD | Trades | Closed Sharpe | Max win/loss run | Carryovers |
|---|---|---|---|---|---|---|---|---|
| USTEC-1y | -11.58% | 0.895 | 47.3% | 22.77% | 241 | -0.73 | 5/8 | 0 |
| USTEC-3y | -49.30% | 0.808 | 46.0% | 55.31% | 709 | -1.42 | 7/10 | 0 |
| USTEC-5y | -64.34% | 0.835 | 46.4% | 67.81% | 1173 | -1.29 | 7/10 | 0 |
| USTEC-6m | +0.22% | 1.004 | 50.4% | 9.08% | 121 | 0.11 | 4/6 | 0 |
| US500-1y | -35.79% | 0.693 | 43.1% | 35.79% | 248 | -2.76 | 5/8 | 0 |
| US500-3y | -84.59% | 0.558 | 39.4% | 84.86% | 701 | -4.01 | 6/12 | 0 |
| US500-5y | -95.37% | 0.599 | 39.6% | 95.39% | 1168 | -3.95 | 7/12 | 0 |
| US500-6m | -20.47% | 0.693 | 44.4% | 20.47% | 124 | -2.83 | 5/8 | 0 |

Independent reconstruction checked 4,485 closed positions and 1,570,548 exported M1 inputs across overlapping runs. Signal VWAP/SD, M5 extrema, causal timestamps, stops/targets and ledger totals passed. S&P500 rejected one entry on 9 September 2026 with native invalid-stops retcode10016, repeated in each overlapping window; this was not treated as a fill or silently retried. Its clean-execution flag remains false. Maximum filled initial stop risk / selected budget: 1.964×. Four unit tests passed.

## Limitations

- The video names VWAP mean reversion but supplies no rules. This is one explicitly frozen interpretation, not proof for or against every VWAP strategy. No optimisation was run.
- Broker CFD feed; typical-price VWAP weighted by tick counts, not NQ/ES exchange volume. Each signal uses only completed M1 bars from 09:30 NY through the completed M5 signal; market order occurs afterwards.
- Native Model 4, 150 ms delay. Actual broker real ticks begin 2026-01-01; earlier history uses generated ticks. Native percentage labels are shown for each report; the six-month window is the cleanest real-tick evidence.
- Independent $10,000 tests, 1% current-balance risk before fees and adverse fill changes. Lot size is rounded down and below-minimum trades skipped. Initial filled risk reached almost 1.96% of balance on Nasdaq and 1.31% on S&P500 due to tight distances and fill movement. Fees/gaps can increase losses further. No minimum-lot override.
- SL and fixed VWAP TP approximately 1:1 at entry quote after tick rounding. No trailing stop, breakeven, martingale or grid. Native commission/spread/swap included. Broker-measured incremental execution-cost stress missing, so promotion is blocked.
- Close requested at 15:30 NY, or 10 minutes before current weekday broker session endpoint. Current schedule is not a historical holiday calendar. Any carryovers/end-of-test exits are disclosed and retained in the results.
- Windows overlap and share previously researched market history: these are configuration-frozen raw comparisons, not a pristine out-of-sample validation. A different 3SD-touch VWAP study previously tried 108 variants and failed. DSR with 2 candidates covers only the current asset comparison; broader idea-selection bias remains.
- Closed Sharpe uses daily closed-balance returns, calendar days, square-root-of-365 annualisation. Floating equity is sampled once per minute for plots; table equity DD comes from the native tick path, not estimated from closed trades.
- 10,000 block-bootstrap paths, block length 5. Resampling/DSR are diagnostics, not forecasts. Internal 5%/10% closed-P&L risk proxies are not FTMO pass probabilities or payout expectations.
- No active EA, BAT, website, broker account, portfolio, FTMO settings or Git remote changed. Stop for review before optimisation or idea 3.
