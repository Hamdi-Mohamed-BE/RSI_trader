# Gold NY30 Value Area + VWAP — raw native results

Research only; no production deployment. Four definitions frozen before tests, no parameter tuning.

## Interpretation
- USD 10,000 initial balance, target 1% current equity; lots rounded UP per raw pipeline. Includes native broker bid/ask, commission, swaps and 150ms simulated execution delay.
- 09:30–10:00 New York range transferred to XAUUSD; M1 signals, 70% tick-volume profile, anchored VWAP +/-1 volume-weighted SD, structural SL plus one tick, 3R, max two combined entries/day, request flat 15:55. See RULES.md for every assumption.
- Reversal gross break-even at VWAP touch; continuation no BE. One attempt per engine/day.
- **Sizing is NOT a hard 1% cap. Latest 6m actual initial risk reached 1.265%. In the depleted 5y combined path, the 0.01 minimum lot exposed 8.444% of equity on 2026-03-03 (roughly USD 58.71 risk on USD 695.22 equity). Thus the long result includes a minimum-lot sizing effect, not just a constant-percentage strategy edge. A strict live risk policy would skip undersized trades or round down; no such rule was retrofitted after testing.**
- **Win rate and PF below use completed trades AFTER all commission and swap. Native MT5 headline wins can include gross break-even exits that lose after entry costs.** Native metrics are preserved separately.
- DD is native maximum relative EQUITY drawdown, not the closed-balance graph. Streaks use net results. Frequency denominator: calendar months and weekdays in the full window, including no-trade days.
- **Model 4 is requested mode, not proof of historical real ticks. Real ticks begin 2026-01-01. Older segments are generated/mixed; the latest 6m lies inside available real-tick history.**
- Overlapping windows are descriptive in-sample comparisons, NOT independent holdouts. This is not a funded-account simulation or proof of future profitability.

## 6m — 2026.03.27 to 2026.09.27 (end exclusive)

| Version | Trades | /month /weekday | Return | Net USD | Net win rate | Net PF | Max equity DD | Longest W/L |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Reversal | 75 | 12.4 / 0.57 | -3.50% | -350.13 | 6.67% | 0.79 | 8.66% | 1 / 29 |
| Continuation | 121 | 20.0 / 0.92 | -4.10% | -409.78 | 25.62% | 0.96 | 16.67% | 3 / 8 |
| Combined | 196 | 32.4 / 1.50 | -3.78% | -378.41 | 18.88% | 0.97 | 15.75% | 2 / 13 |
| Plain ORB control | 170 | 28.1 / 1.30 | +6.20% | +619.84 | 27.06% | 1.05 | 19.75% | 5 / 19 |

## 1y — 2025.09.27 to 2026.09.27 (end exclusive)

| Version | Trades | /month /weekday | Return | Net USD | Net win rate | Net PF | Max equity DD | Longest W/L |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Reversal | 157 | 13.1 / 0.60 | -16.85% | -1,685.26 | 6.37% | 0.60 | 21.35% | 1 / 29 |
| Continuation | 242 | 20.2 / 0.93 | -20.51% | -2,050.62 | 23.97% | 0.89 | 30.05% | 3 / 9 |
| Combined | 395 | 32.9 / 1.52 | -39.13% | -3,913.06 | 16.46% | 0.78 | 41.67% | 2 / 23 |
| Plain ORB control | 341 | 28.4 / 1.31 | -6.24% | -624.12 | 25.81% | 0.98 | 31.82% | 5 / 19 |

## 3y — 2023.09.27 to 2026.09.27 (end exclusive)

| Version | Trades | /month /weekday | Return | Net USD | Net win rate | Net PF | Max equity DD | Longest W/L |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Reversal | 448 | 12.4 / 0.57 | -27.81% | -2,780.96 | 8.93% | 0.76 | 31.18% | 2 / 42 |
| Continuation | 711 | 19.7 / 0.91 | -52.38% | -5,238.43 | 24.05% | 0.87 | 53.22% | 4 / 20 |
| Combined | 1136 | 31.5 / 1.45 | -78.13% | -7,813.21 | 17.17% | 0.75 | 79.48% | 4 / 29 |
| Plain ORB control | 996 | 27.7 / 1.27 | -73.85% | -7,384.98 | 23.80% | 0.79 | 79.24% | 5 / 27 |

## 5y — 2021.09.27 to 2026.09.27 (end exclusive)

| Version | Trades | /month /weekday | Return | Net USD | Net win rate | Net PF | Max equity DD | Longest W/L |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Reversal | 716 | 11.9 / 0.55 | -47.49% | -4,749.08 | 10.06% | 0.74 | 49.79% | 4 / 42 |
| Continuation | 1115 | 18.6 / 0.85 | -77.67% | -7,766.62 | 23.59% | 0.83 | 82.02% | 5 / 20 |
| Combined | 1792 | 29.9 / 1.37 | -93.12% | -9,312.19 | 17.63% | 0.77 | 94.78% | 5 / 29 |
| Plain ORB control | 1600 | 26.7 / 1.23 | -78.83% | -7,882.86 | 25.12% | 0.88 | 83.43% | 5 / 27 |

## Coverage and execution

| Window | Version | Native history quality | Overnight positions | Max actual initial SL risk | Entry / close / BE failures |
|---|---|---|---:|---:|---:|
| 6m | Reversal | 100% real ticks | 0 | 1.119% | 0 / 0 / 0 |
| 6m | Continuation | 100% real ticks | 0 | 1.265% | 0 / 0 / 0 |
| 6m | Combined | 100% real ticks | 0 | 1.265% | 0 / 0 / 0 |
| 6m | Plain ORB control | 100% real ticks | 0 | 1.245% | 0 / 0 / 0 |
| 1y | Reversal | 73% real ticks | 0 | 1.377% | 0 / 0 / 0 |
| 1y | Continuation | 73% real ticks | 0 | 1.262% | 0 / 0 / 0 |
| 1y | Combined | 73% real ticks | 0 | 1.776% | 0 / 0 / 0 |
| 1y | Plain ORB control | 73% real ticks | 0 | 1.835% | 0 / 0 / 0 |
| 3y | Reversal | 24% real ticks | 0 | 1.596% | 0 / 0 / 0 |
| 3y | Continuation | 24% real ticks | 0 | 1.275% | 0 / 0 / 0 |
| 3y | Combined | 24% real ticks | 0 | 2.530% | 0 / 0 / 0 |
| 3y | Plain ORB control | 24% real ticks | 0 | 2.015% | 0 / 0 / 0 |
| 5y | Reversal | 14% real ticks | 0 | 1.386% | 0 / 0 / 0 |
| 5y | Continuation | 14% real ticks | 0 | 1.684% | 0 / 0 / 0 |
| 5y | Combined | 14% real ticks | 0 | 8.444% | 0 / 0 / 0 |
| 5y | Plain ORB control | 14% real ticks | 0 | 1.952% | 0 / 0 / 0 |

No overnight or closed-market loss is erased. Actual initial risk uses fill-to-original-stop before costs; realized SL losses can exceed that through slippage.
Profile is an M1 HLC3/tick-count binning proxy, NOT COMEX volume-at-price or exact TradingView/Deepcharts parity. Broker history and symbol specs are not independently reconstructed historical fee schedules.

## Predeclared raw gate

- **Reversal: FAIL**. 3y: fail, 5y: fail. Full long-window real-tick confirmation: False.
- **Continuation: FAIL**. 3y: fail, 5y: fail. Full long-window real-tick confirmation: False.
- **Combined: FAIL**. 3y: fail, 5y: fail. Full long-window real-tick confirmation: False.

No variant is promoted without both numeric qualification and data confirmation. Do not automatically optimize a raw failure.

## Model 1 long-window screening — not real-tick confirmation

| Version | Trades | /month /weekday | Return | Net USD | Net win rate | Net PF | Max equity DD | Longest W/L |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **3y** | | | | | | | | |
| Combined | 1136 | 31.5 / 1.45 | -76.73% | -7,673.37 | 17.17% | 0.76 | 78.24% | 4 / 29 |
| Continuation | 711 | 19.7 / 0.91 | -48.77% | -4,876.64 | 24.05% | 0.88 | 51.64% | 4 / 20 |
| Plain ORB control | 996 | 27.7 / 1.27 | -72.51% | -7,250.80 | 23.80% | 0.80 | 78.32% | 5 / 27 |
| Reversal | 448 | 12.4 / 0.57 | -24.24% | -2,423.58 | 9.15% | 0.79 | 27.96% | 2 / 42 |
| **5y** | | | | | | | | |
| Combined | 1792 | 29.9 / 1.37 | -92.35% | -9,235.27 | 17.63% | 0.78 | 93.76% | 5 / 29 |
| Continuation | 1115 | 18.6 / 0.85 | -75.19% | -7,519.09 | 23.59% | 0.84 | 80.32% | 5 / 20 |
| Plain ORB control | 1600 | 26.7 / 1.23 | -76.56% | -7,655.65 | 25.12% | 0.89 | 82.42% | 5 / 27 |
| Reversal | 716 | 11.9 / 0.55 | -43.75% | -4,374.80 | 10.20% | 0.76 | 46.15% | 4 / 42 |

## Monthly net USD — latest 6m

| Month | Reversal | Continuation | Combined | Control |
|---|---:|---:|---:|---:|
| 2026-03 | +0.00 | +520.79 | +520.79 | +117.41 |
| 2026-04 | -22.71 | -530.17 | -571.85 | -76.91 |
| 2026-05 | -216.07 | +790.36 | +586.14 | +147.55 |
| 2026-06 | -318.81 | -98.42 | -434.86 | +1,005.22 |
| 2026-07 | +268.79 | +94.53 | +347.72 | -1,231.77 |
| 2026-08 | +175.45 | -161.26 | +28.87 | +910.79 |
| 2026-09 | -236.78 | -1,025.61 | -855.22 | -252.45 |

First/last calendar months may be partial. All windows' monthly counts, wins, starting/ending balances and returns: RESULTS.json.

## Gross break-even versus net outcomes — latest 6m

| Version | Trades moved to BE | Of those, net losses | Net P&L of all BE-moved trades (USD) |
|---|---:|---:|---:|
| Reversal | 60 | 55 | +1,207.96 |
| Continuation | 0 | 0 | +0.00 |
| Combined | 60 | 55 | +1,299.88 |
| Plain ORB control | 0 | 0 | +0.00 |

Moving the stop to entry does not exit the trade; some BE-protected trades continue to TP. The negative subset includes commission/slippage losses, not just full-stop losses.

## Extra cost sensitivity — latest 6m

Hypothetical ledger subtraction, NOT a native rerun or measured live slippage. Add USD 0.20 / 0.50 per ounce round trip at original lots; future lot sizing, signals, exits and margin are not resimulated.

| Version | Extra round-trip price cost | Net USD | Return | PF |
|---|---:|---:|---:|---:|
| Reversal | 0.20 | -569.93 | -5.70% | 0.69 |
| Reversal | 0.50 | -899.63 | -9.00% | 0.58 |
| Continuation | 0.20 | -1,614.18 | -16.14% | 0.86 |
| Continuation | 0.50 | -3,420.78 | -34.21% | 0.73 |
| Combined | 0.20 | -1,798.61 | -17.99% | 0.86 |
| Combined | 0.50 | -3,928.91 | -39.29% | 0.73 |
| Plain ORB control | 0.20 | -445.76 | -4.46% | 0.97 |
| Plain ORB control | 0.50 | -2,044.16 | -20.44% | 0.87 |

## Verification

- Clean compile: 0 errors/warnings; EA refuses live initialization.
- Four smoke tests plus 24 main serial isolated native tests; fresh reports, inputs, symbol, dates, frozen hashes and delay checked.
- Independent profile/VWAP/band, signal-state, closed-bar timing, stop/target, volume, cash P&L, position overlap, daily cap and break-even audits. Native totals reconcile to completed deals.
- Compressed original reports, journals, M1 bars and profiles plus trade ledgers retained. No live chart/BAT/website/production changes.

## Sources

- Source reel/user transcript: https://www.instagram.com/reel/DacxHJqNuUZ/
- Official indicator description (not published equations): https://helpdesk.deepcharts.com/portal/en/kb/articles/deep-m-ivb
- VWAP concepts: https://www.tradingview.com/support/solutions/43000502018-volume-weighted-average-price-vwap/
- Volume profile concepts and volume types: https://www.tradingview.com/support/solutions/43000502040-volume-profile-indicators-basic-concepts/
