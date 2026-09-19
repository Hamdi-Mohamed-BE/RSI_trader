# Overnight Profile — raw native MT5 comparison

Window: 2025.09.19 through 2026.09.19 exclusive. Each strategy starts with $10,000 at 1% equity risk. No optimization.

| Asset | Direction | Return | Net USD | Trades | Net win rate | Net PF | Equity DD | Commission | Swap | Real-tick quality |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| US500 | POC | +1.55% | +154.78 | 221 | 60.18% | 1.02 | 23.50% | -404.58 | -23.87 | 71% real ticks |
| US500 | VA | -5.82% | -582.22 | 191 | 72.25% | 0.87 | 13.27% | -204.81 | -13.62 | 71% real ticks |
| USTEC | POC | -11.57% | -1157.13 | 209 | 60.29% | 0.84 | 19.72% | -134.03 | 0.00 | 71% real ticks |
| USTEC | VA | -6.44% | -644.27 | 183 | 69.95% | 0.86 | 9.24% | -84.22 | -10.65 | 71% real ticks |
| XAUUSD | POC | +3.40% | +340.24 | 236 | 58.90% | 1.04 | 9.29% | -60.96 | -2.20 | 71% real ticks |
| XAUUSD | VA | +22.26% | +2225.75 | 200 | 74.00% | 1.56 | 4.00% | -39.99 | 0.00 | 71% real ticks |

## Interpretation and limitations

- VA means close above/below the 70% value area; POC means close above/below its point of control. See RULES.md for the exact frozen assumptions.
- Bid/ask spread and reported deal commissions/swaps are included. Native 150 ms delay creates modeled execution effects, not proof of live fill quality.
- Profile uses completed M1 tick-volume at typical price, not futures traded volume. Reported generated-tick periods must not be described as real-tick proof.
- Equity DD displayed is the larger of MT5 reported relative equity DD and the tick-by-tick EA equity audit. Both values are retained below; this conservatively avoids hiding a higher observed drawdown. It is not balance-only drawdown.
- First and last monthly rows are partial months (September 19 onward / through September 18). Historical broker session/holiday closures can reject/delay the 16:00 NY exit. Therefore these results are NOT proof of a strict exit-by-16:00 strategy; late exits and overnight holdings are explicitly counted.
- No website or BAT updates, no deployment, no older strategy transfers.

## Signal and sizing audit

| Asset / mode | Profile days | Missing profiles | Signals | Invalid geometry | Rejected | Late exits >1m | Overnight holds | Max initial stop risk |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| US500 POC | 258 | 0 | 258 | 36 | 1 | 3 | 1 | 1.410% |
| US500 VA | 258 | 0 | 255 | 63 | 1 | 4 | 1 | 1.057% |
| USTEC POC | 258 | 0 | 258 | 49 | 0 | 2 | 0 | 1.062% |
| USTEC VA | 258 | 0 | 257 | 74 | 0 | 5 | 1 | 1.054% |
| XAUUSD POC | 258 | 0 | 258 | 21 | 1 | 12 | 2 | 2.690% |
| XAUUSD VA | 258 | 0 | 243 | 41 | 2 | 16 | 2 | 2.516% |

## Exit, drawdown and streak detail

| Asset / mode | Average initial RR | Win streak | Loss streak | MT5 equity DD | Tick-audit equity DD | Average net trade |
|---|---:|---:|---:|---:|---:|---:|
| US500 POC | 1.272R | 8 | 6 | 23.42% | 23.50% | $+0.70 |
| US500 VA | 0.404R | 9 | 5 | 13.23% | 13.27% | $-3.05 |
| USTEC POC | 1.007R | 10 | 4 | 19.67% | 19.72% | $-5.54 |
| USTEC VA | 0.389R | 17 | 6 | 9.22% | 9.24% | $-3.52 |
| XAUUSD POC | 1.139R | 10 | 6 | 9.14% | 9.29% | $+1.44 |
| XAUUSD VA | 0.444R | 11 | 3 | 3.74% | 4.00% | $+11.13 |

## Monthly net USD (closed trades, including fees)

| Month | US500 POC | US500 VA | USTEC POC | USTEC VA | XAUUSD POC | XAUUSD VA |
|---|---:|---:|---:|---:|---:|---:|
| 2025-09 | +252.85 (7 trades) | +13.56 (7 trades) | +36.64 (7 trades) | +45.21 (6 trades) | +376.83 (8 trades) | +153.18 (5 trades) |
| 2025-10 | -718.50 (21 trades) | -275.25 (16 trades) | +325.19 (18 trades) | -45.41 (13 trades) | -450.35 (22 trades) | -105.33 (17 trades) |
| 2025-11 | +229.51 (16 trades) | -186.57 (15 trades) | -58.72 (13 trades) | -21.22 (12 trades) | -153.12 (19 trades) | -183.89 (14 trades) |
| 2025-12 | -606.50 (20 trades) | -137.50 (17 trades) | -470.15 (16 trades) | -60.51 (16 trades) | +106.41 (20 trades) | +325.28 (16 trades) |
| 2026-01 | -204.11 (19 trades) | -25.72 (14 trades) | -464.18 (20 trades) | -136.77 (18 trades) | +649.21 (19 trades) | +310.80 (20 trades) |
| 2026-02 | -393.94 (16 trades) | -392.38 (15 trades) | -534.98 (17 trades) | -371.35 (17 trades) | -245.62 (18 trades) | +364.36 (16 trades) |
| 2026-03 | -258.88 (20 trades) | -54.05 (20 trades) | +66.42 (16 trades) | -89.00 (14 trades) | -358.52 (22 trades) | +268.24 (18 trades) |
| 2026-04 | +62.78 (17 trades) | +121.32 (16 trades) | +332.87 (17 trades) | +572.01 (16 trades) | +183.80 (20 trades) | +218.26 (18 trades) |
| 2026-05 | +640.20 (18 trades) | +155.05 (13 trades) | +4.11 (18 trades) | -172.93 (14 trades) | +691.07 (16 trades) | +482.02 (14 trades) |
| 2026-06 | +1433.21 (19 trades) | -74.13 (16 trades) | -87.14 (20 trades) | -124.88 (16 trades) | -315.76 (21 trades) | +353.38 (15 trades) |
| 2026-07 | -328.58 (19 trades) | +92.55 (15 trades) | -160.42 (18 trades) | +181.92 (15 trades) | +133.59 (21 trades) | +184.80 (20 trades) |
| 2026-08 | +98.58 (16 trades) | +97.12 (15 trades) | -258.79 (15 trades) | -234.00 (13 trades) | -362.37 (18 trades) | -153.57 (16 trades) |
| 2026-09 | -51.84 (13 trades) | +83.78 (12 trades) | +112.02 (14 trades) | -187.34 (13 trades) | +85.07 (12 trades) | +8.22 (11 trades) |
