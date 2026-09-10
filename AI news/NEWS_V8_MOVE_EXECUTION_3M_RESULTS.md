# Gold News V8 - Move Range and Execution Study

> NFP, CPI, and FOMC only. Direction is the frozen V7 walk-forward call. Move intervals use only earlier releases. Execution uses MT5 bid/ask ticks, first available fill after the requested time, and gap slippage.

## Predicted Move Range - Last Three Months

| Date | Event | Call | Predicted gold move | Actual release move | Direction | Magnitude range |
|---|---|---|---:|---:|---|---|
| 2026-06-10 | CPI | POSITIVE | +3.93 to +34.74 USD | +27.82 USD | WIN | HIT |
| 2026-06-17 | FOMC | NEGATIVE | -34.77 to -3.93 USD | -31.93 USD | WIN | HIT |
| 2026-07-02 | NFP | POSITIVE | +3.93 to +35.18 USD | +52.13 USD | WIN | MISS |
| 2026-07-14 | CPI | POSITIVE | +3.93 to +35.18 USD | +60.54 USD | WIN | MISS |
| 2026-07-29 | FOMC | NEGATIVE | -50.47 to -3.93 USD | +32.42 USD | LOSS | HIT |
| 2026-08-07 | NFP | NEGATIVE | -50.16 to -3.93 USD | +46.95 USD | LOSS | HIT |
| 2026-08-12 | CPI | POSITIVE | +5.34 to +51.61 USD | -33.19 USD | LOSS | HIT |
| 2026-09-04 | NFP | NEGATIVE | -51.61 to -11.21 USD | -69.73 USD | WIN | MISS |

### Range Scores

| Measure | Result |
|---|---:|
| Direction accuracy | 62.50% |
| Magnitude interval coverage | 62.50% |
| Signed interval coverage | 25.00% |
| Median-estimate MAE | $28.47 |
| Nominal interval mass | 65.0% |

## Selected Execution

**entry T-5s; SL $4; TP none; trail none; time exit T+900s**

The configuration was selected on June 10 through July 29. August 7 through September 4 was not used to choose it.

| Window | Trades | Wins | Win rate | Net P/L | End balance | Profit factor | Max realized DD |
|---|---:|---:|---:|---:|---:|---:|---:|
| Selection window | 5 | 4 | 80.00% | $+1960.03 | $2060.03 | 60.58 | $32.90 |
| Untouched holdout | 3 | 1 | 33.33% | $+576.28 | $676.28 | 8.5 | $76.83 |
| Full three months | 8 | 5 | 62.50% | $+2536.31 | $2636.31 | 24.11 | $109.73 |

## Full $100 Replay

| Date | Event | Call | Entry time | Entry | Exit | Exit reason | Gold captured | P/L | Balance |
|---|---|---|---|---:|---:|---|---:|---:|---:|
| 2026-06-10 | CPI | POSITIVE | 12:29:55.145 UTC | 4137.743 | 4160.673 | TIME_EXIT_T_PLUS_900s | +22.930 USD | $+183.44 | $283.44 |
| 2026-06-17 | FOMC | NEGATIVE | 17:59:55.562 UTC | 4379.234 | 4284.700 | TIME_EXIT_T_PLUS_900s | +94.534 USD | $+756.27 | $1039.71 |
| 2026-07-02 | NFP | POSITIVE | 12:29:55.002 UTC | 4064.311 | 4132.604 | TIME_EXIT_T_PLUS_900s | +68.293 USD | $+546.34 | $1586.05 |
| 2026-07-14 | CPI | POSITIVE | 12:29:55.002 UTC | 4029.454 | 4092.814 | TIME_EXIT_T_PLUS_900s | +63.360 USD | $+506.88 | $2092.93 |
| 2026-07-29 | FOMC | NEGATIVE | 17:59:55.575 UTC | 4043.987 | 4048.099 | STOP_LOSS | -4.112 USD | $-32.90 | $2060.03 |
| 2026-08-07 | NFP | NEGATIVE | 12:29:55.046 UTC | 4307.239 | 4312.210 | STOP_LOSS | -4.971 USD | $-39.77 | $2020.26 |
| 2026-08-12 | CPI | POSITIVE | 12:29:55.000 UTC | 4423.644 | 4419.011 | STOP_LOSS | -4.633 USD | $-37.06 | $1983.20 |
| 2026-09-04 | NFP | NEGATIVE | 12:29:55.063 UTC | 4475.682 | 4394.043 | TIME_EXIT_T_PLUS_900s | +81.639 USD | $+653.11 | $2636.31 |

## Optimization Honesty

- Tested 14805 predefined configurations.
- The best-observed all-eight configuration ended at $2636.31. Its full-period profit remains an in-sample upper bound even when it matches the selection-window winner.
- Commission, latency, rejected orders, and server-side execution asymmetry are unavailable historically. Spread and tick-gap slippage are included.
- Eight releases are far too few to establish stability. The holdout result is the most important number in this report.
