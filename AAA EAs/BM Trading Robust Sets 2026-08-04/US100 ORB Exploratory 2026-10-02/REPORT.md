# US100 ORB: risk improved, latest-year edge did not survive

Exploratory only. No deployment.

15-minute range 09:30–09:45 NY; LONG ONLY; previous completed H1 close above EMA100; first later completed M5 close above range high; market entry next tick; SL at range low; target 3R; last entry before 15:30 NY. Exit requested at 15:55 NY or 10 minutes before the current broker weekday session endpoint, whichever is earlier. One qualifying signal attempt per NY day. Risk remains 1% of balance, rounded down, skip below minimum. No trailing, breakeven, grid or martingale.

| Period/version | Return | Net PF | Win rate | Native equity DD | Trades | Daily closed Sharpe | Win/loss streak | Carryovers |
|---|---|---|---|---|---|---|---|---|
| Development: 2021–24 | +33.61% | 1.271 | 47.5% | 9.79% | 236 | 0.95 | 6/6 | 1 |
| Validation: 2024–25 | +17.90% | 1.490 | 54.2% | 5.89% | 83 | 1.62 | 4/4 | 2 |
| Locked latest year | -1.69% | 0.958 | 49.4% | 9.82% | 89 | -0.12 | 4/7 | 3 |
| Latest 6 months | +3.51% | 1.138 | 51.9% | 9.85% | 52 | 0.62 | 4/2 | 1 |
| Full 3 years: exploratory | +40.97% | 1.292 | 52.9% | 9.84% | 255 | 1.14 | 4/7 | 5 |
| Full 5 years: exploratory | +54.73% | 1.232 | 49.3% | 9.87% | 408 | 0.88 | 6/7 | 6 |

## Raw versus selected

| Latest year — original raw | -9.61% | 0.929 | 43.2% | 31.70% | 257 | -0.47 | 5/6 | 15 |
| Latest year — pre-close raw | -7.77% | 0.941 | 44.4% | 31.66% | 257 | -0.37 | 7/6 | 4 |
| Latest year — selected version | -1.69% | 0.958 | 49.4% | 9.82% | 89 | -0.12 | 4/7 | 3 |
| Full 5 years — original raw | +63.06% | 1.065 | 44.3% | 31.77% | 1285 | 0.59 | 7/9 | 69 |
| Full 5 years — pre-close raw | +64.70% | 1.068 | 44.7% | 31.79% | 1285 | 0.60 | 7/9 | 11 |
| Full 5 years — selected version | +54.73% | 1.232 | 49.3% | 9.87% | 408 | 0.88 | 6/7 | 6 |

## Limitations

- 27 unique tested settings counted, including prior raw US500 candidate, controls and delay sensitivity; repeated periods and model confirmations do not create new alpha settings. This is a bounded one-factor staged search, not an exhaustive global optimum.
- Opening range, target, entry cutoff, direction and simple H1 EMA filter were selected only on 2021-10-02–2024-10-01 development data. Native M1-OHLC screening followed by model-4 development confirmation of three frozen alternatives. One primary locked before validation/test; no adjustment after the latest-year loss.
- Broker CFD history, not NQ futures. Selected five-/three-/one-year native history-quality fields report 14%/23%/60% real ticks respectively, including the 90-day warmup; latest 6-month report is 100% real ticks and validation is 0%. The original raw reports had no warmup and reported 15%/25%/75%. These denominators differ, not the underlying broker feed. Model 4 does not make older generated ticks real. Historical market data had already been researched, so this is not a pristine untouched holdout.
- Native market spreads, commission and swaps included. Risk budget excludes fees and gap/slippage. Extra execution delay is an illustrative native sensitivity, not a broker-measured cost calibration; the mandatory calibrated-extra-cost promotion gate remains incomplete.
- The current broker weekday session schedule is not a historical holiday or seasonal calendar. Carryovers remain and are included in profits, swaps and drawdowns. Operational improvement is reported separately from entry/target/filter changes.
- Five-year and three-year selected totals include development data and overlap the latest year: they are exploratory illustrations, not independent out-of-sample proofs. The latest-year negative return and PF below 1 outweigh an attractive full-history curve.
- Reported Sharpe annualises calendar-day closed-balance returns at sqrt(365). Native MT5 Sharpe is stored separately in evidence. Native equity DD includes floating losses; plotted balances exclude them except the explicitly minute-sampled equity figure.
- 10,000 circular block-bootstrap paths, block length 5, Wilson intervals and DSR corrected for all campaign settings. Resampling is a diagnostic, not a return forecast. Closed-P&L prop breach proxies in audit JSON are not FTMO pass/payout predictions.
- No forward demo, prospective data holdout, deployment, active-EA change, website update, Git push or other tier-list strategy started.
