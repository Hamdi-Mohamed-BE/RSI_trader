# Trend Progression final native-MT5 audit

The two-year development sample selected every parameter. The last year was then run once, untouched.

## Untouched last-year comparison

| Symbol | Config | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| USTEC | Baseline | +7.73% | 1.27 | 47.06% | 8.09% | 51 | 1.43 | 0.89 |
| USTEC | Optimized | +6.04% | 1.29 | 33.33% | 10.03% | 27 | 1.10 | 0.55 |
| BTCUSD | Baseline | -14.90% | 0.72 | 32.56% | 21.31% | 86 | -2.12 | -0.65 |
| BTCUSD | Optimized | -9.04% | 0.56 | 38.46% | 14.10% | 39 | -2.11 | -0.61 |
| XAUUSD | Baseline | +16.94% | 1.93 | 57.14% | 3.05% | 49 | 4.24 | 4.64 |
| XAUUSD | Optimized | +16.10% | 2.74 | 48.00% | 3.07% | 25 | 5.35 | 4.43 |

## Selected mechanical configuration

| Symbol | TF | Structure | Stop / RR | Exit management | Session |
|---|---:|---|---|---|---|
| USTEC | H4 | longonly | swing-rr300 | none | all |
| BTCUSD | H4 | longonly | swing-rr400 | be100 | all |
| XAUUSD | H4 | longonly | swing-rr300 | be100 | all |

## Three-year and Monte Carlo context

| Symbol | 3Y return | 3Y PF | 3Y DD | 3Y trades | MC profitable | MC return P5 | MC median | MC DD P95 | Ruin |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| USTEC | +37.07% | 1.58 | 10.06% | 77 | 73.3% | -10.39% | +6.06% | 14.97% | 0.00% |
| BTCUSD | +17.77% | 1.35 | 14.30% | 99 | 12.6% | -20.75% | -9.50% | 21.47% | 0.00% |
| XAUUSD | +63.85% | 2.47 | 6.11% | 91 | 98.1% | +3.05% | +15.96% | 6.07% | 0.00% |

Costs shown by MT5 include broker spread in tick execution, commission, swap and random execution delay. Session hours are broker-server hours.
