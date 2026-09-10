# Gold News V8 - Frozen Parameters, One-Year Replay

> The three-month winner is applied unchanged: 0.08 lot, market entry at T-5 seconds, $4 gold-price stop, no take profit, no trailing stop, and exit at T+15 minutes. MT5 bid/ask ticks include spread and crossing slippage.

## Summary

| Measure | Result |
|---|---:|
| Prediction events | 29 |
| Direction accuracy | 68.97% |
| Magnitude-range coverage | 58.62% |
| Signed-range coverage | 34.48% |
| Starting balance | $100.00 |
| Ending balance | $3034.33 |
| Net P/L | $+2934.33 |
| Executed trades | 29 |
| Wins / losses | 12 / 17 |
| Win rate | 41.38% |
| Profit factor | 5.52 |
| Maximum realized drawdown | $152.76 (80.81%) |
| Maximum tick-equity drawdown | $275.30 (96.00%) |
| Minimum tick equity | $4.07 |
| Fully tick-exact executions | 16 |
| Tick + M1 continuation executions | 13 |

## Event Breakdown

| Event | Releases | Direction accuracy | Trade win rate | Net P/L | Profit factor |
|---|---:|---:|---:|---:|---:|
| CPI | 11 | 8/11 (72.73%) | 7/11 (63.64%) | $+1163.23 | 9.14 |
| NFP | 10 | 7/10 (70.00%) | 4/10 (40.00%) | $+1267.65 | 6.00 |
| FOMC | 8 | 5/8 (62.50%) | 1/8 (12.50%) | $+503.45 | 2.99 |

## Predictions and $100 Simulation

| Date | Event | Call | Predicted release move | Actual release move | Direction | Range | Captured | Exit | P/L | Balance | Source |
|---|---|---|---:|---:|---|---|---:|---|---:|---:|---|
| 2025-09-11 | CPI | POSITIVE | +2.30 to +13.13 USD | +7.87 | WIN | HIT | -4.69 | STOP_LOSS | $-37.52 | $62.48 | archive ticks + M1 continuation |
| 2025-09-17 | FOMC | NEGATIVE | -13.13 to -2.30 USD | -4.59 | WIN | HIT | -5.41 | STOP_LOSS | $-43.29 | $19.19 | archive ticks + M1 continuation |
| 2025-10-24 | CPI | POSITIVE | +2.82 to +13.13 USD | +29.29 | WIN | MISS | +20.94 | TIME_EXIT_T_PLUS_900s | $+167.52 | $186.71 | archive ticks + M1 continuation |
| 2025-10-29 | FOMC | NEGATIVE | -18.72 to -4.17 USD | -6.45 | WIN | HIT | -4.05 | STOP_LOSS | $-32.40 | $154.31 | archive ticks + M1 continuation |
| 2025-11-20 | NFP | NEGATIVE | -18.72 to -4.17 USD | -3.96 | WIN | MISS | -7.23 | STOP_LOSS | $-57.84 | $96.47 | archive ticks + M1 continuation |
| 2025-12-10 | FOMC | POSITIVE | +3.69 to +18.72 USD | +16.72 | WIN | HIT | -5.44 | STOP_LOSS | $-43.55 | $52.92 | archive ticks + M1 continuation |
| 2025-12-16 | NFP | POSITIVE | +4.43 to +19.05 USD | +4.42 | WIN | MISS | +1.77 | TIME_EXIT_T_PLUS_900s | $+14.16 | $67.08 | archive ticks + M1 continuation |
| 2025-12-18 | CPI | POSITIVE | +4.30 to +19.05 USD | +9.76 | WIN | HIT | +13.68 | TIME_EXIT_T_PLUS_900s | $+109.44 | $176.52 | archive ticks + M1 continuation |
| 2026-01-09 | NFP | NEGATIVE | -19.05 to -4.55 USD | -2.25 | WIN | MISS | -4.19 | STOP_LOSS | $-33.52 | $143.00 | archive ticks + M1 continuation |
| 2026-01-13 | CPI | POSITIVE | +4.55 to +19.05 USD | +9.94 | WIN | HIT | +15.79 | TIME_EXIT_T_PLUS_900s | $+126.35 | $269.35 | archive ticks + M1 continuation |
| 2026-01-28 | FOMC | NEGATIVE | -19.05 to -4.55 USD | +7.31 | LOSS | HIT | -4.25 | STOP_LOSS | $-34.00 | $235.35 | archive ticks + M1 continuation |
| 2026-02-11 | NFP | POSITIVE | +4.55 to +19.05 USD | -60.00 | LOSS | MISS | -4.61 | STOP_LOSS | $-36.86 | $198.49 | archive ticks + M1 continuation |
| 2026-02-13 | CPI | POSITIVE | +4.55 to +28.03 USD | +27.57 | WIN | HIT | +15.87 | TIME_EXIT_T_PLUS_900s | $+126.98 | $325.47 | archive ticks + M1 continuation |
| 2026-03-06 | NFP | POSITIVE | +4.55 to +29.11 USD | +35.54 | WIN | MISS | +38.45 | TIME_EXIT_T_PLUS_900s | $+307.58 | $633.05 | MT5 ticks |
| 2026-03-11 | CPI | POSITIVE | +5.94 to +34.91 USD | -3.49 | LOSS | MISS | -4.36 | STOP_LOSS | $-34.87 | $598.18 | MT5 ticks |
| 2026-03-18 | FOMC | NEGATIVE | -34.74 to -4.30 USD | +5.77 | LOSS | HIT | -4.11 | STOP_LOSS | $-32.91 | $565.27 | MT5 ticks |
| 2026-04-10 | CPI | POSITIVE | +4.30 to +34.74 USD | +13.60 | WIN | HIT | +10.69 | TIME_EXIT_T_PLUS_900s | $+85.51 | $650.78 | MT5 ticks |
| 2026-04-29 | FOMC | NEGATIVE | -34.74 to -5.43 USD | -3.54 | WIN | MISS | -4.22 | STOP_LOSS | $-33.77 | $617.01 | MT5 ticks |
| 2026-05-08 | NFP | NEGATIVE | -34.74 to -4.20 USD | -2.24 | WIN | MISS | -4.61 | STOP_LOSS | $-36.85 | $580.16 | MT5 ticks |
| 2026-05-12 | CPI | POSITIVE | +3.53 to +34.74 USD | -4.05 | LOSS | HIT | -4.18 | STOP_LOSS | $-33.44 | $546.72 | MT5 ticks |
| 2026-06-05 | NFP | POSITIVE | +3.53 to +34.74 USD | -14.76 | LOSS | HIT | -6.09 | STOP_LOSS | $-48.70 | $498.02 | MT5 ticks |
| 2026-06-10 | CPI | POSITIVE | +3.93 to +34.74 USD | +27.82 | WIN | HIT | +22.93 | TIME_EXIT_T_PLUS_900s | $+183.44 | $681.46 | MT5 ticks |
| 2026-06-17 | FOMC | NEGATIVE | -34.77 to -3.93 USD | -31.93 | WIN | HIT | +94.53 | TIME_EXIT_T_PLUS_900s | $+756.27 | $1437.73 | MT5 ticks |
| 2026-07-02 | NFP | POSITIVE | +3.93 to +35.18 USD | +52.13 | WIN | MISS | +68.29 | TIME_EXIT_T_PLUS_900s | $+546.34 | $1984.07 | MT5 ticks |
| 2026-07-14 | CPI | POSITIVE | +3.93 to +35.18 USD | +60.54 | WIN | MISS | +63.36 | TIME_EXIT_T_PLUS_900s | $+506.88 | $2490.95 | MT5 ticks |
| 2026-07-29 | FOMC | NEGATIVE | -50.47 to -3.93 USD | +32.42 | LOSS | HIT | -4.11 | STOP_LOSS | $-32.90 | $2458.05 | MT5 ticks |
| 2026-08-07 | NFP | NEGATIVE | -50.16 to -3.93 USD | +46.95 | LOSS | HIT | -4.97 | STOP_LOSS | $-39.77 | $2418.28 | MT5 ticks |
| 2026-08-12 | CPI | POSITIVE | +5.34 to +51.61 USD | -33.19 | LOSS | HIT | -4.63 | STOP_LOSS | $-37.06 | $2381.22 | MT5 ticks |
| 2026-09-04 | NFP | NEGATIVE | -51.61 to -11.21 USD | -69.73 | WIN | MISS | +81.64 | TIME_EXIT_T_PLUS_900s | $+653.11 | $3034.33 | MT5 ticks |

## Interpretation

- The execution parameters were discovered inside the final three months of this one-year table. The full-year replay is retrospective and is not a clean prospective validation.
- The magnitude range is walk-forward: every row uses only earlier event outcomes.
- Commission, execution rejection, and network latency are unavailable historically. They are excluded; spread and tick-gap slippage are included where ticks exist.
- Hybrid rows use archived bid/ask ticks where available and M1 OHLC to bridge missing seconds through T+15. A fixed-stop crossing in an M1 segment is detected, but its exact sub-minute slippage cannot be reconstructed.
- Fixed 0.08 lot is used throughout; lot size is not compounded as the balance changes.
