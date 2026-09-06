# Step 2 — LVN Volume Profile final native-MT5 audit

The two-year development period selected each parameter in sequence. The last year was then tested once without changing the selection.

## Untouched last-year comparison

| Symbol | Config | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery | Decision |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| XAUUSD | Baseline | -9.30% | 0.89 | 38.24% | 23.81% | 170 | -2.47 | -0.37 |  |
| XAUUSD | Optimized | -1.62% | 0.98 | 37.50% | 16.50% | 136 | -0.32 | -0.09 | REJECT |
| XAGUSD | Baseline | -10.49% | 0.91 | 39.09% | 22.41% | 197 | -2.40 | -0.41 |  |
| XAGUSD | Optimized | -4.99% | 0.82 | 30.43% | 11.94% | 46 | -3.81 | -0.39 | REJECT |
| BTCUSD | Baseline | -19.78% | 0.83 | 37.05% | 27.04% | 224 | -3.51 | -0.73 |  |
| BTCUSD | Optimized | +4.27% | 1.07 | 47.27% | 13.91% | 110 | 1.38 | 0.28 | WATCH / insufficient robustness |
| US30 | Baseline | +11.97% | 1.14 | 44.22% | 10.64% | 147 | 2.69 | 1.08 |  |
| US30 | Optimized | +4.15% | 1.11 | 54.02% | 10.39% | 87 | 2.31 | 0.38 | WATCH / insufficient robustness |
| USTEC | Baseline | -15.41% | 0.84 | 37.04% | 22.65% | 162 | -3.89 | -0.63 |  |
| USTEC | Optimized | -0.43% | 0.94 | 55.00% | 3.91% | 20 | -0.49 | -0.11 | REJECT |
| GBPJPY | Baseline | -18.89% | 0.80 | 36.81% | 23.15% | 144 | -5.00 | -0.77 |  |
| GBPJPY | Optimized | -17.01% | 0.50 | 34.55% | 19.19% | 55 | -5.00 | -0.88 | REJECT |

## Raw idea versus completed-M15 confirmation (development only)

| Symbol | Best raw touch | Raw return / PF / trades | Best confirmed approach | Confirmed return / PF / trades |
|---|---|---:|---|---:|
| XAUUSD | raw20 | -16.74% / 0.90 / 360 | auto10 | -6.60% / 0.97 / 380 |
| XAGUSD | raw20 | -32.31% / 0.58 / 143 | bounce10 | -12.67% / 0.53 / 39 |
| BTCUSD | raw20 | -10.21% / 0.96 / 511 | breakout10 | +5.54% / 1.02 / 433 |
| US30 | raw20 | -13.13% / 0.94 / 365 | bounce10 | -4.64% / 0.95 / 167 |
| USTEC | raw20 | -27.66% / 0.87 / 420 | retest10 | -18.53% / 0.75 / 114 |
| GBPJPY | raw20 | -51.75% / 0.74 / 417 | retest10 | +17.08% / 1.30 / 97 |

These figures are development comparisons, not final evidence. The untouched table above is the decision test.

## Selected configuration

| Symbol | Entry/profile | Stop | RR | Trailing | Session |
|---|---|---|---|---|---|
| XAUUSD | auto10 | swing5 | rr200 | none | all |
| XAGUSD | bounce10 | swing5 | rr200 | none | asia |
| BTCUSD | breakout10 | signal | rr150 | be100 | newyork |
| US30 | bounce10 | atr200 | rr150 | dynamic5020-atr | all |
| USTEC | retest10 | swing8 | rr300 | dynamic5020 | overlap |
| GBPJPY | retest10 | atr150 | rr100 | atr100-200 | all |

## Three-year and Monte Carlo context

| Symbol | 3Y return | 3Y PF | 3Y DD | 3Y trades | MC profitable | MC return P5 | MC median | MC DD P95 | DD ≥20% | Ruin |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| XAUUSD | +25.94% | 1.09 | 19.38% | 444 | 45.0% | -23.48% | -1.74% | 28.61% | 21.9% | 0.00% |
| XAGUSD | -0.83% | 0.97 | 12.03% | 55 | 25.6% | -17.14% | -5.33% | 19.08% | 3.8% | 0.00% |
| BTCUSD | +37.25% | 1.16 | 15.65% | 371 | 62.9% | -16.28% | +4.07% | 22.61% | 9.0% | 0.00% |
| US30 | +12.98% | 1.11 | 10.37% | 252 | 66.3% | -13.39% | +4.50% | 18.81% | 3.6% | 0.00% |
| USTEC | +1.19% | 1.03 | 10.25% | 82 | 43.9% | -6.31% | -0.62% | 7.00% | 0.0% | 0.00% |
| GBPJPY | +7.82% | 1.09 | 19.99% | 152 | 0.3% | -26.42% | -17.12% | 27.14% | 38.5% | 0.00% |

## Method and limitations

- The composite profile uses prior M15 broker tick activity because spot CFDs have no centralized exchange volume.
- The profile is rebuilt once per broker day and remains frozen during that day, avoiding look-ahead bias.
- Development used MT5 one-minute OHLC for search speed. Both untouched last-year and three-year final audits used MT5 Every Tick with broker costs and random execution delay.
- Risk was held at the agreed 1% per trade. A negative XAG result remains visible and satisfies the mandatory validation requirement.
- No result is permission for live deployment; only a passing locked result can become a demo candidate after user approval.
