# NY30 Value Area + VWAP - Gold vs US100 vs US500

None of the new profile/VWAP variants passes the frozen long-window raw gate.

Positive new variants over the latest six months: US500 Reversal 12.20%. This does not override the long-window gate.

Research only. Unchanged gold strategy transferred to USTEC (US100) and US500 in the isolated Exness tester. Live trading, production EAs, BATs and website were not changed.

## Test design and interpretation

- Four predeclared versions: reversal, continuation, combined (shared limits), plain M1-close ORB control. Identical compiled binary/source across all assets; no tuning.
- Combined means reversal + continuation on ONE asset. Gold, US100 and US500 are separate tests, not a simultaneous three-asset portfolio or an overlay on your production system.
- 09:30-10:00 New York opening profile; M1 entries; 64 bins; 70% value area. Broker M1 tick-volume/HLC3 proxy, NOT exchange volume-at-price. VWAP anchored 09:30; +/-1 volume-weighted standard deviation.
- Reversal fades an opening-range excursion after a later close back inside value area; gross break-even on favorable VWAP touch. Continuation requires a band/VA breakout and later retest. Fixed 3R target; structural stop plus one symbol tick; skip stops under three current spreads.
- Two entries maximum/day for combined/control, one attempt/engine; one position; entry cutoff 15:30 NY, flat request 15:55, broker-open execution only.
- USD 10,000 starts, 1% current-equity TARGET, lots rounded upward exactly as in gold. Rounding, minimum lots and fills can exceed 1%; actual maxima below. This is NOT a strict 1% cap or an FTMO simulation. Tester leverage setting 1:2000.
- Initial-risk maxima measure actual fill to ORIGINAL stop price, before commission, swaps and stop-fill slippage. They are not maximum possible loss or realized loss.
- Broker spread/commission/swap as charged by native tester, plus 150ms execution delay. Delay-based slippage is simulated, not measured live execution. Historical broker specification/cost changes are not independently reconstructed.
- End date 2026-09-27 exclusive. Windows overlap: descriptive backtests, not independent out-of-sample validation. Model 4 requests real ticks but generates missing history; actual coverage is disclosed.
- Net win rate and PF recomputed AFTER commission/swap. Gross break-even can be net loss. Equity DD is maximum relative floating-equity drawdown from native report, not balance-curve DD.
- Trades/day uses all Monday-Friday dates, including holidays/no-trade days. Streaks use net outcomes; exactly flat outcomes break streaks.
- Frozen raw gate: positive return, PF >=1.15, >=30 trades, beat control on PF and return/equity-DD on BOTH 3y and 5y. No automatic optimization/promotion.

## 6m: 2026.03.27 to 2026.09.27 exclusive

| Asset | Version | Trades | /month | /weekday | Net USD | Return | Net win | Net PF | Equity DD | Max W/L |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Gold | Reversal | 75 | 12.4 | 0.57 | -350.13 | -3.50% | 6.67% | 0.79 | 8.66% | 1/29 |
| Gold | Continuation | 121 | 20.0 | 0.92 | -409.78 | -4.10% | 25.62% | 0.96 | 16.67% | 3/8 |
| Gold | Combined | 196 | 32.4 | 1.50 | -378.41 | -3.78% | 18.88% | 0.97 | 15.75% | 2/13 |
| Gold | Plain ORB | 170 | 28.1 | 1.30 | +619.84 | +6.20% | 27.06% | 1.05 | 19.75% | 5/19 |
| US100 | Reversal | 64 | 10.6 | 0.49 | -1,379.25 | -13.79% | 4.69% | 0.27 | 15.20% | 1/17 |
| US100 | Continuation | 120 | 19.9 | 0.92 | -2,122.21 | -21.22% | 20.00% | 0.77 | 26.12% | 3/17 |
| US100 | Combined | 181 | 29.9 | 1.38 | -3,845.73 | -38.46% | 13.26% | 0.60 | 42.21% | 2/29 |
| US100 | Plain ORB | 169 | 28.0 | 1.29 | +1,859.56 | +18.60% | 28.99% | 1.13 | 12.67% | 2/7 |
| US500 | Reversal | 66 | 10.9 | 0.50 | +1,219.62 | +12.20% | 15.15% | 1.64 | 7.85% | 1/11 |
| US500 | Continuation | 119 | 19.7 | 0.91 | -1,982.01 | -19.82% | 25.21% | 0.80 | 26.82% | 3/9 |
| US500 | Combined | 185 | 30.6 | 1.41 | -621.13 | -6.21% | 22.16% | 0.95 | 19.41% | 2/11 |
| US500 | Plain ORB | 176 | 29.1 | 1.34 | +508.83 | +5.09% | 29.55% | 1.04 | 26.86% | 3/13 |

## 1y: 2025.09.27 to 2026.09.27 exclusive

| Asset | Version | Trades | /month | /weekday | Net USD | Return | Net win | Net PF | Equity DD | Max W/L |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Gold | Reversal | 157 | 13.1 | 0.60 | -1,685.26 | -16.85% | 6.37% | 0.60 | 21.35% | 1/29 |
| Gold | Continuation | 242 | 20.2 | 0.93 | -2,050.62 | -20.51% | 23.97% | 0.89 | 30.05% | 3/9 |
| Gold | Combined | 395 | 32.9 | 1.52 | -3,913.06 | -39.13% | 16.46% | 0.78 | 41.67% | 2/23 |
| Gold | Plain ORB | 341 | 28.4 | 1.31 | -624.12 | -6.24% | 25.81% | 0.98 | 31.82% | 5/19 |
| US100 | Reversal | 133 | 11.1 | 0.51 | -2,485.56 | -24.86% | 5.26% | 0.33 | 25.08% | 1/27 |
| US100 | Continuation | 230 | 19.2 | 0.88 | -4,801.04 | -48.01% | 18.70% | 0.65 | 49.81% | 3/17 |
| US100 | Combined | 357 | 29.8 | 1.37 | -5,894.91 | -58.95% | 14.01% | 0.62 | 60.07% | 3/29 |
| US100 | Plain ORB | 325 | 27.1 | 1.25 | -740.82 | -7.41% | 25.85% | 0.97 | 30.70% | 2/11 |
| US500 | Reversal | 140 | 11.7 | 0.54 | +1,587.38 | +15.87% | 15.00% | 1.35 | 10.14% | 2/17 |
| US500 | Continuation | 228 | 19.0 | 0.88 | -3,048.78 | -30.49% | 25.00% | 0.82 | 39.41% | 5/13 |
| US500 | Combined | 365 | 30.4 | 1.40 | -2,285.37 | -22.85% | 20.82% | 0.89 | 36.18% | 3/18 |
| US500 | Plain ORB | 338 | 28.2 | 1.30 | -1,390.18 | -13.90% | 26.92% | 0.94 | 28.87% | 4/21 |

## 3y: 2023.09.27 to 2026.09.27 exclusive

| Asset | Version | Trades | /month | /weekday | Net USD | Return | Net win | Net PF | Equity DD | Max W/L |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Gold | Reversal | 448 | 12.4 | 0.57 | -2,780.96 | -27.81% | 8.93% | 0.76 | 31.18% | 2/42 |
| Gold | Continuation | 711 | 19.7 | 0.91 | -5,238.43 | -52.38% | 24.05% | 0.87 | 53.22% | 4/20 |
| Gold | Combined | 1136 | 31.5 | 1.45 | -7,813.21 | -78.13% | 17.17% | 0.75 | 79.48% | 4/29 |
| Gold | Plain ORB | 996 | 27.7 | 1.27 | -7,384.98 | -73.85% | 23.80% | 0.79 | 79.24% | 5/27 |
| US100 | Reversal | 417 | 11.6 | 0.53 | -4,947.66 | -49.48% | 6.95% | 0.50 | 50.24% | 2/32 |
| US100 | Continuation | 607 | 16.9 | 0.78 | -8,044.36 | -80.44% | 19.77% | 0.66 | 81.89% | 3/18 |
| US100 | Combined | 1013 | 28.1 | 1.29 | -8,910.04 | -89.10% | 14.71% | 0.61 | 89.67% | 3/29 |
| US100 | Plain ORB | 933 | 25.9 | 1.19 | -7,832.42 | -78.32% | 22.72% | 0.75 | 83.33% | 4/21 |
| US500 | Reversal | 414 | 11.5 | 0.53 | -3,180.99 | -31.81% | 10.63% | 0.72 | 48.17% | 2/41 |
| US500 | Continuation | 498 | 13.8 | 0.64 | -5,826.54 | -58.27% | 23.90% | 0.80 | 64.19% | 5/22 |
| US500 | Combined | 901 | 25.0 | 1.15 | -6,992.08 | -69.92% | 17.87% | 0.76 | 75.60% | 3/27 |
| US500 | Plain ORB | 846 | 23.5 | 1.08 | -6,693.26 | -66.93% | 24.59% | 0.79 | 72.95% | 4/21 |

## 5y: 2021.09.27 to 2026.09.27 exclusive

| Asset | Version | Trades | /month | /weekday | Net USD | Return | Net win | Net PF | Equity DD | Max W/L |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Gold | Reversal | 716 | 11.9 | 0.55 | -4,749.08 | -47.49% | 10.06% | 0.74 | 49.79% | 4/42 |
| Gold | Continuation | 1115 | 18.6 | 0.85 | -7,766.62 | -77.67% | 23.59% | 0.83 | 82.02% | 5/20 |
| Gold | Combined | 1792 | 29.9 | 1.37 | -9,312.19 | -93.12% | 17.63% | 0.77 | 94.78% | 5/29 |
| Gold | Plain ORB | 1600 | 26.7 | 1.23 | -7,882.86 | -78.83% | 25.12% | 0.88 | 83.43% | 5/27 |
| US100 | Reversal | 700 | 11.7 | 0.54 | -5,611.42 | -56.11% | 9.57% | 0.72 | 63.11% | 3/47 |
| US100 | Continuation | 959 | 16.0 | 0.73 | -8,758.54 | -87.59% | 21.17% | 0.78 | 88.82% | 4/18 |
| US100 | Combined | 1635 | 27.3 | 1.25 | -9,365.85 | -93.66% | 16.39% | 0.80 | 94.81% | 5/29 |
| US100 | Plain ORB | 1529 | 25.5 | 1.17 | -9,317.63 | -93.18% | 22.37% | 0.76 | 94.79% | 4/21 |
| US500 | Reversal | 708 | 11.8 | 0.54 | -5,602.11 | -56.02% | 10.73% | 0.68 | 63.55% | 3/41 |
| US500 | Continuation | 717 | 12.0 | 0.55 | -7,943.08 | -79.43% | 22.45% | 0.71 | 80.39% | 5/22 |
| US500 | Combined | 1398 | 23.3 | 1.07 | -9,023.76 | -90.24% | 16.52% | 0.66 | 90.97% | 3/37 |
| US500 | Plain ORB | 1322 | 22.0 | 1.01 | -8,942.90 | -89.43% | 23.45% | 0.74 | 91.57% | 4/21 |

## Frozen gate results

| Asset | Version | Decision |
|---|---|---|
| Gold | Reversal | FAIL raw numerical gate |
| Gold | Continuation | FAIL raw numerical gate |
| Gold | Combined | FAIL raw numerical gate |
| US100 | Reversal | FAIL raw numerical gate |
| US100 | Continuation | FAIL raw numerical gate |
| US100 | Combined | FAIL raw numerical gate |
| US500 | Reversal | FAIL raw numerical gate |
| US500 | Continuation | FAIL raw numerical gate |
| US500 | Combined | FAIL raw numerical gate |

## Coverage and actual initial-risk maxima

| Asset | Period | Reported real-tick coverage | Max risk reversal | Continuation | Combined | Control |
|---|---|---|---:|---:|---:|---:|
| Gold | 6m | 100% real ticks | 1.119% | 1.265% | 1.265% | 1.245% |
| Gold | 1y | 73% real ticks | 1.377% | 1.262% | 1.776% | 1.835% |
| Gold | 3y | 24% real ticks | 1.596% | 1.275% | 2.530% | 2.015% |
| Gold | 5y | 14% real ticks | 1.386% | 1.684% | 8.444% | 1.952% |

Gold native specification: NY30_SPEC|XAUUSD|tick_size=0.00100000|contract=100.0000|min_lot=0.0100|lot_step=0.0100|stops=0|utc_offset=0. Real-tick journal: real ticks begin from 2026.01.01 00:00:00.

| US100 | 6m | 100% real ticks | 1.046% | 1.217% | 1.220% | 1.132% |
| US100 | 1y | 73% real ticks | 1.082% | 1.217% | 1.217% | 1.148% |
| US100 | 3y | 24% real ticks | 1.083% | 1.218% | 1.232% | 1.150% |
| US100 | 5y | 14% real ticks | 1.082% | 1.235% | 1.427% | 1.476% |

US100 native specification: NY30_SPEC|USTEC|tick_size=0.01000000|contract=1.0000|min_lot=0.0500|lot_step=0.0100|stops=0|utc_offset=0. Real-tick journal: real ticks begin from 2026.01.01 00:00:00.

| US500 | 6m | 100% real ticks | 1.068% | 1.319% | 1.490% | 1.263% |
| US500 | 1y | 73% real ticks | 1.069% | 1.319% | 1.490% | 1.263% |
| US500 | 3y | 24% real ticks | 1.069% | 1.319% | 1.490% | 1.263% |
| US500 | 5y | 14% real ticks | 1.069% | 1.319% | 1.491% | 1.268% |

US500 native specification: NY30_SPEC|US500|tick_size=0.01000000|contract=1.0000|min_lot=0.1400|lot_step=0.0100|stops=0|utc_offset=0. Real-tick journal: real ticks begin from 2026.01.01 00:00:00.

Gold 5y combined includes a minimum-lot trade after severe balance erosion. Initial risk is NOT realized loss on that trade. Upward rounding is retained for comparison, not recommended as a hard-risk implementation.

## Last 6 months: monthly net USD and closed trades

Partial March/September months included. Closed-trade profits are NOT funded payouts. Each version has its own 10,000 USD starting account.

### Gold

| Month | Reversal USD (trades) | Continuation USD (trades) | Combined USD (trades) | Control USD (trades) |
|---|---:|---:|---:|---:|
| 2026-03 | +0.00 (0) | +520.79 (3) | +520.79 (3) | +117.41 (3) |
| 2026-04 | -22.71 (11) | -530.17 (20) | -571.85 (31) | -76.91 (28) |
| 2026-05 | -216.07 (12) | +790.36 (19) | +586.14 (31) | +147.55 (27) |
| 2026-06 | -318.81 (11) | -98.42 (20) | -434.86 (31) | +1,005.22 (27) |
| 2026-07 | +268.79 (14) | +94.53 (22) | +347.72 (36) | -1,231.77 (34) |
| 2026-08 | +175.45 (11) | -161.26 (20) | +28.87 (31) | +910.79 (22) |
| 2026-09 | -236.78 (16) | -1,025.61 (17) | -855.22 (33) | -252.45 (29) |

### US100

| Month | Reversal USD (trades) | Continuation USD (trades) | Combined USD (trades) | Control USD (trades) |
|---|---:|---:|---:|---:|
| 2026-03 | -1.22 (1) | -297.06 (3) | -298.24 (4) | -307.81 (3) |
| 2026-04 | -351.23 (10) | -605.70 (21) | -1,283.40 (31) | +805.85 (26) |
| 2026-05 | -440.37 (13) | -753.83 (19) | -1,524.53 (31) | -73.86 (28) |
| 2026-06 | -16.18 (13) | +835.97 (18) | +745.07 (30) | +686.96 (29) |
| 2026-07 | -4.39 (11) | +408.79 (23) | +336.87 (33) | +713.34 (33) |
| 2026-08 | -284.47 (7) | -817.22 (19) | -900.27 (26) | +309.09 (25) |
| 2026-09 | -281.39 (9) | -893.16 (17) | -921.23 (26) | -274.01 (25) |

### US500

| Month | Reversal USD (trades) | Continuation USD (trades) | Combined USD (trades) | Control USD (trades) |
|---|---:|---:|---:|---:|
| 2026-03 | +303.77 (1) | -312.34 (3) | -35.87 (4) | -37.40 (4) |
| 2026-04 | -247.06 (10) | +496.74 (20) | +208.29 (30) | +1,739.36 (29) |
| 2026-05 | +546.03 (13) | -216.28 (20) | +324.84 (33) | -1,988.47 (32) |
| 2026-06 | +257.13 (13) | -954.74 (20) | -772.84 (33) | +430.72 (28) |
| 2026-07 | -287.60 (12) | +218.40 (22) | -9.56 (34) | -364.21 (29) |
| 2026-08 | +368.62 (10) | -805.03 (17) | -586.02 (27) | +65.40 (28) |
| 2026-09 | +278.73 (7) | -408.76 (17) | +250.03 (24) | +663.43 (26) |

## 6m costs, break-even and average streaks

| Asset | Version | Commission USD | Swap USD | BE moved / net losses | Avg win/loss streak | UTC-date overnight crossings |
|---|---|---:|---:|---:|---:|---:|
| Gold | Reversal | -60.62 | 0.00 | 60/55 | 1.00/11.67 | 0 |
| Gold | Continuation | -331.55 | 0.00 | 0/0 | 1.24/3.60 | 0 |
| Gold | Combined | -391.05 | 0.00 | 60/55 | 1.09/4.68 | 0 |
| Gold | Plain ORB | -293.46 | 0.00 | 0/0 | 1.31/3.54 | 0 |
| US100 | Reversal | -70.77 | 0.00 | 45/42 | 1.00/15.25 | 0 |
| US100 | Continuation | -461.66 | 0.00 | 0/0 | 1.26/5.05 | 1 |
| US100 | Combined | -458.31 | 0.00 | 44/41 | 1.26/7.85 | 1 |
| US100 | Plain ORB | -568.29 | 0.00 | 0/0 | 1.23/2.93 | 0 |
| US500 | Reversal | -208.74 | 0.00 | 51/41 | 1.00/6.22 | 0 |
| US500 | Continuation | -1,482.39 | 0.00 | 0/0 | 1.30/3.87 | 0 |
| US500 | Combined | -1,798.04 | 0.00 | 51/41 | 1.24/4.36 | 0 |
| US500 | Plain ORB | -1,431.47 | 0.00 | 0/0 | 1.27/3.02 | 0 |

## Model 1 long-window screen (NOT real ticks)

| Asset | Period | Version | Return | Net PF | Equity DD | Trades |
|---|---|---|---:|---:|---:|---:|
| Gold | 3y | Reversal | -24.24% | 0.79 | 27.96% | 448 |
| Gold | 3y | Continuation | -48.77% | 0.88 | 51.64% | 711 |
| Gold | 3y | Combined | -76.73% | 0.76 | 78.24% | 1136 |
| Gold | 3y | Plain ORB | -72.51% | 0.80 | 78.32% | 996 |
| Gold | 5y | Reversal | -43.75% | 0.76 | 46.15% | 716 |
| Gold | 5y | Continuation | -75.19% | 0.84 | 80.32% | 1115 |
| Gold | 5y | Combined | -92.35% | 0.78 | 93.76% | 1792 |
| Gold | 5y | Plain ORB | -76.56% | 0.89 | 82.42% | 1600 |
| US100 | 3y | Reversal | -44.59% | 0.55 | 45.45% | 417 |
| US100 | 3y | Continuation | -81.04% | 0.66 | 82.53% | 607 |
| US100 | 3y | Combined | -88.43% | 0.62 | 89.11% | 1013 |
| US100 | 3y | Plain ORB | -77.46% | 0.76 | 82.52% | 933 |
| US100 | 5y | Reversal | -49.58% | 0.76 | 57.77% | 700 |
| US100 | 5y | Continuation | -87.52% | 0.78 | 88.96% | 959 |
| US100 | 5y | Combined | -92.65% | 0.81 | 94.12% | 1635 |
| US100 | 5y | Plain ORB | -92.43% | 0.77 | 94.19% | 1529 |
| US500 | 3y | Reversal | -31.03% | 0.73 | 47.02% | 414 |
| US500 | 3y | Continuation | -61.37% | 0.78 | 67.11% | 493 |
| US500 | 3y | Combined | -70.02% | 0.76 | 75.73% | 897 |
| US500 | 3y | Plain ORB | -72.34% | 0.77 | 77.96% | 843 |
| US500 | 5y | Reversal | -53.47% | 0.70 | 61.01% | 708 |
| US500 | 5y | Continuation | -80.20% | 0.70 | 81.14% | 712 |
| US500 | 5y | Combined | -89.44% | 0.68 | 90.25% | 1394 |
| US500 | 5y | Plain ORB | -90.47% | 0.75 | 92.60% | 1319 |

## Verification

84 verified native cases: 56 new indices cases (48 main + 8 smoke), plus 28 existing gold cases reused. All reports reconcile to deal ledgers; all final reviews pass. Totals: {"profile_checks": 54188, "bar_indicator_checks": 20573708, "signal_checks": 51224, "trade_checks": 51224, "breakeven_checks": 10054}.

Shared source SHA-256: 1f28e8055c8229f1f17c79b739c20059c4ece46b98dc2eb063de9ed208306f71.

Shared binary SHA-256: 94dfa79ce4a5f2ed1986340c674f685d51c48cf414cb6097285079b3d4a84641.

Charts show closed-trade balance, NOT floating equity. Complete rows and ledgers are in RESULTS.json and each asset's research directory.
