# Trend Progression final native-MT5 audit

The two-year development sample selected every parameter. The last year was then run once, untouched.

## Untouched last-year comparison

| Symbol | Config | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| XAGUSD | Baseline | +14.42% | 1.91 | 58.14% | 3.81% | 43 | 5.40 | 3.48 |
| XAGUSD | Optimized | -1.06% | 0.76 | 12.50% | 5.02% | 8 | -0.11 | -0.21 |
| ETHUSD | Baseline | +3.04% | 1.07 | 42.65% | 11.67% | 68 | 0.42 | 0.23 |
| ETHUSD | Optimized | -2.97% | 0.87 | 31.25% | 10.69% | 32 | -0.94 | -0.26 |
| EURUSD | Baseline | -4.38% | 0.87 | 38.18% | 12.79% | 55 | -0.90 | -0.32 |
| EURUSD | Optimized | -2.64% | 0.86 | 34.38% | 8.76% | 32 | -1.27 | -0.29 |
| GBPUSD | Baseline | -18.15% | 0.52 | 26.32% | 19.33% | 57 | -3.55 | -0.94 |
| GBPUSD | Optimized | -5.20% | 0.60 | 17.65% | 11.45% | 17 | -0.65 | -0.44 |
| USDJPY | Baseline | -8.65% | 0.71 | 35.56% | 10.57% | 45 | -1.86 | -0.82 |
| USDJPY | Optimized | +1.66% | 1.24 | 72.00% | 3.29% | 25 | 1.52 | 0.50 |
| GBPJPY | Baseline | -20.21% | 0.45 | 24.07% | 23.70% | 54 | -4.37 | -0.84 |
| GBPJPY | Optimized | +0.52% | 1.02 | 28.12% | 8.22% | 32 | 0.09 | 0.06 |

## Selected mechanical configuration

| Symbol | TF | Structure | Stop / RR | Exit management | Session |
|---|---:|---|---|---|---|
| XAGUSD | H4 | longonly | atr-rr400 | be100 | overlap |
| ETHUSD | H4 | longonly | swing-rr200 | none | all |
| EURUSD | H4 | longonly | signal-rr300 | trail075-atr15 | all |
| GBPUSD | H4 | longonly | atr-rr400 | none | all |
| USDJPY | H4 | longonly | atr-rr050 | be075 | asia |
| GBPJPY | H4 | longonly | swing-rr300 | none | all |

## Three-year and Monte Carlo context

| Symbol | 3Y return | 3Y PF | 3Y DD | 3Y trades | MC profitable | MC return P5 | MC median | MC DD P95 | Ruin |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| XAGUSD | +1.61% | 1.11 | 10.02% | 30 | 29.8% | -6.04% | -1.27% | 6.06% | 0.00% |
| ETHUSD | -1.18% | 0.98 | 10.69% | 106 | 35.1% | -15.12% | -3.02% | 17.85% | 0.00% |
| EURUSD | +8.24% | 1.13 | 11.27% | 115 | 35.8% | -14.71% | -2.95% | 16.66% | 0.00% |
| GBPUSD | +8.02% | 1.19 | 14.98% | 52 | 18.5% | -14.30% | -5.36% | 14.46% | 0.00% |
| USDJPY | +10.44% | 1.60 | 6.11% | 66 | 75.2% | -4.15% | +1.70% | 5.93% | 0.00% |
| GBPJPY | +27.27% | 1.48 | 7.44% | 74 | 51.5% | -14.31% | +0.29% | 16.98% | 0.00% |

Costs shown by MT5 include broker spread in tick execution, commission, swap and random execution delay. Session hours are broker-server hours.
