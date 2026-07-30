# Backtest Comparison

Same 716-release archive, same chronological training period, and same final holdout.

| Lead | Version | Profile | Calls | Coverage | Accuracy | Brier |
|---:|---|---|---:|---:|---:|---:|
| 15m | Baseline | legacy | 27 | 44.26% | 55.56% | 0.50388 |
| 15m | Improved | enhanced | 16 | 26.23% | 62.50% | 0.49985 |
| 30m | Baseline | legacy | 26 | 42.62% | 65.38% | 0.50418 |
| 30m | Improved | legacy | 26 | 42.62% | 65.38% | 0.50418 |

Pooled called accuracy: **60.38% (32/53)** to **64.29% (27/42)**.

The T-15 gain comes with lower coverage. T-30 keeps the stable legacy feature profile. Official release text is analyzed only after publication and is not credited to the pre-release result.
