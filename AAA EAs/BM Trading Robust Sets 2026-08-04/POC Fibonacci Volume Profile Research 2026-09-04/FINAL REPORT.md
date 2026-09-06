# Step 3 — POC + Fibonacci Volume Profile final native-MT5 audit

The two-year development period selected each parameter in sequence. The last year was then tested once without changing the selection.

## Final decision

**Do not add this strategy to the active portfolio or website.** BTC is the only positive locked-year result, but it has just 26 trades and its 10,000-path Monte Carlo P5 return is negative. It is suitable only for an isolated forward-demo watch after user approval. The other five markets are rejected.

## Mechanical reconstruction

1. Build a volume profile from a closed rolling M15 range; broker tick activity is used where centralized volume is unavailable.
2. Calculate the profile POC and the Fibonacci retracement levels from the same completed range.
3. Require POC/Fibonacci proximity, H1 EMA trend agreement, a prior departure from POC, and a completed M15 rejection/reclaim candle.
4. Enter on the next bar with the selected structural/ATR stop, fixed RR or tested trailing method, and exactly 1% balance risk.

The audit contains 216 native MT5 tests. All 540 selected input values in the locked and full reports match their saved set files.

## Untouched last-year comparison

| Symbol | Config | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery | Decision |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| XAUUSD | Baseline | -2.66% | 0.95 | 39.81% | 15.78% | 103 | -1.04 | -0.17 |  |
| XAUUSD | Optimized | -9.09% | 0.46 | 47.06% | 11.87% | 34 | -5.00 | -0.76 | REJECT |
| XAGUSD | Baseline | -16.88% | 0.67 | 33.73% | 18.28% | 83 | -5.00 | -0.91 |  |
| XAGUSD | Optimized | -0.89% | 0.94 | 39.29% | 10.98% | 28 | -1.75 | -0.08 | REJECT |
| BTCUSD | Baseline | -7.87% | 0.91 | 39.01% | 12.02% | 141 | -2.83 | -0.63 |  |
| BTCUSD | Optimized | +8.37% | 1.40 | 26.92% | 9.32% | 26 | 4.86 | 0.76 | WATCH / insufficient robustness |
| US30 | Baseline | -18.80% | 0.69 | 34.07% | 24.16% | 91 | -5.00 | -0.73 |  |
| US30 | Optimized | -13.97% | 0.50 | 26.83% | 15.12% | 41 | -5.00 | -0.92 | REJECT |
| USTEC | Baseline | +1.34% | 1.01 | 43.07% | 12.96% | 137 | 0.43 | 0.09 |  |
| USTEC | Optimized | -1.48% | 0.86 | 58.33% | 7.21% | 24 | -3.76 | -0.20 | REJECT |
| GBPJPY | Baseline | -14.54% | 0.73 | 35.71% | 19.14% | 84 | -5.00 | -0.75 |  |
| GBPJPY | Optimized | -13.58% | 0.40 | 31.43% | 17.62% | 35 | -5.00 | -0.76 | REJECT |

## Selected configuration

| Symbol | Profile/Fibonacci screen | Stop | RR | Trailing | Session |
|---|---|---|---|---|---|
| XAUUSD | r96-f618 | signal | rr150 | dynamic5020 | asia |
| XAGUSD | r192-f618 | atr100 | rr150 | atr100-200 | all |
| BTCUSD | r192-f618 | atr150 | rr500 | none | newyork |
| US30 | r192-f618 | atr200 | rr150 | none | all |
| USTEC | r96-f500 | atr200 | rr075 | dynamic5020 | london |
| GBPJPY | r192-f618 | atr200 | rr300 | be100 | all |

## Three-year and Monte Carlo context

| Symbol | 3Y return | 3Y PF | 3Y DD | 3Y trades | MC profitable | MC return P5 | MC median | MC DD P95 | DD ≥20% | Ruin |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| XAUUSD | +0.87% | 1.02 | 13.10% | 92 | 4.7% | -18.05% | -9.05% | 18.82% | 2.9% | 0.00% |
| XAGUSD | +4.16% | 1.16 | 13.65% | 47 | 43.6% | -12.51% | -1.20% | 14.26% | 0.2% | 0.00% |
| BTCUSD | +28.54% | 1.52 | 9.32% | 71 | 70.0% | -14.32% | +8.11% | 19.63% | 4.5% | 0.00% |
| US30 | -8.29% | 0.87 | 17.54% | 102 | 2.6% | -24.98% | -14.04% | 25.98% | 26.1% | 0.00% |
| USTEC | -1.35% | 0.94 | 7.21% | 56 | 37.7% | -8.62% | -1.51% | 10.43% | 0.0% | 0.00% |
| GBPJPY | +14.98% | 1.23 | 17.83% | 104 | 0.7% | -22.81% | -13.58% | 23.49% | 17.4% | 0.00% |

## Method and limitations

- The POC profile uses only completed rolling M15 broker tick activity because spot CFDs have no centralized exchange volume.
- The profile is rebuilt after each completed M15 bar. Fibonacci levels use the high and low of that same closed rolling window, avoiding future leakage.
- Development used MT5 one-minute OHLC for search speed. Both untouched last-year and three-year final audits used MT5 Every Tick with broker costs and random execution delay.
- Risk was held at the agreed 1% per trade. A negative XAG result remains visible and satisfies the mandatory validation requirement.
- No result is permission for live deployment; only a passing locked result can become a demo candidate after user approval.
