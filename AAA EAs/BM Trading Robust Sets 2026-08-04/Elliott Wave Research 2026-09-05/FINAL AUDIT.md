# Elliott Wave 1-2-3 final native-MT5 audit

The two-year development sample selected every parameter. The last year was then run once, untouched.

## Untouched last-year comparison

| Symbol | Config | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| XAUUSD | Baseline | +9.59% | 13.24 | 88.89% | 1.85% | 9 | 0.88 | 4.73 |
| XAUUSD | Optimized | +23.82% | 3.15 | 54.17% | 3.77% | 24 | 5.86 | 4.91 |
| XAGUSD | Baseline | +4.80% | 1.20 | 44.23% | 4.21% | 52 | 1.50 | 1.14 |
| XAGUSD | Optimized | +3.18% | 1.11 | 27.66% | 6.51% | 47 | 0.62 | 0.48 |
| USTEC | Baseline | -1.09% | 0.88 | 37.50% | 4.28% | 16 | -0.18 | -0.25 |
| USTEC | Optimized | -4.55% | 0.64 | 51.85% | 4.68% | 27 | -2.90 | -0.97 |
| US30 | Baseline | -25.54% | 0.79 | 35.75% | 27.52% | 221 | -2.92 | -0.91 |
| US30 | Optimized | -28.14% | 0.73 | 15.75% | 32.42% | 127 | -2.76 | -0.82 |
| BTCUSD | Baseline | -9.13% | 0.82 | 36.26% | 11.74% | 91 | -1.23 | -0.78 |
| BTCUSD | Optimized | -16.82% | 0.62 | 52.83% | 24.28% | 106 | -4.32 | -0.68 |
| GBPJPY | Baseline | -3.63% | 0.70 | 33.33% | 8.40% | 18 | -0.64 | -0.41 |
| GBPJPY | Optimized | -3.81% | 0.74 | 16.67% | 9.83% | 18 | -0.55 | -0.38 |
| EURUSD | Baseline | -0.70% | 0.98 | 40.00% | 9.92% | 50 | -0.13 | -0.07 |
| EURUSD | Optimized | +3.36% | 1.36 | 70.97% | 5.62% | 31 | 1.20 | 0.55 |

## Selected mechanical configuration

| Symbol | TF | Structure | Stop / RR | Exit management | Session |
|---|---:|---|---|---|---|
| XAUUSD | H4 | ema50 | signal-rr300 | none | all |
| XAGUSD | H1 | wave-only | wave2-rr300 | none | all |
| USTEC | H4 | wave-only | atr-rr075 | dynamic5020 | all |
| US30 | M15 | h4-ema50 | wave2-rr400 | none | all |
| BTCUSD | H1 | ema-stack | signal-rr400 | dynamic5020 | all |
| GBPJPY | H4 | wave-only | atr-rr400 | none | all |
| EURUSD | H1 | ema-stack | wave2-rr300 | dynamic5020 | newyork |

## Three-year and Monte Carlo context

| Symbol | 3Y return | 3Y PF | 3Y DD | 3Y trades | MC profitable | MC return P5 | MC median | MC DD P95 | Ruin |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| XAUUSD | +69.85% | 2.47 | 6.83% | 70 | 99.6% | +8.47% | +23.84% | 6.03% | 0.00% |
| XAGUSD | +16.69% | 1.40 | 6.94% | 69 | 61.2% | -12.91% | +2.98% | 17.20% | 0.00% |
| USTEC | +2.05% | 1.07 | 5.23% | 77 | 14.0% | -11.34% | -4.52% | 12.18% | 0.00% |
| US30 | -4.15% | 0.98 | 36.08% | 251 | 7.3% | -58.96% | -28.62% | 61.86% | 0.00% |
| BTCUSD | +8.89% | 1.06 | 28.84% | 307 | 5.2% | -32.72% | -17.08% | 34.11% | 0.00% |
| GBPJPY | +21.44% | 1.87 | 9.98% | 32 | 35.8% | -13.45% | -3.85% | 15.97% | 0.00% |
| EURUSD | +20.97% | 1.81 | 7.12% | 83 | 69.4% | -6.02% | +3.15% | 8.38% | 0.00% |

Costs shown by MT5 include broker spread in tick execution, commission, swap and random execution delay. Session hours are broker-server hours.
