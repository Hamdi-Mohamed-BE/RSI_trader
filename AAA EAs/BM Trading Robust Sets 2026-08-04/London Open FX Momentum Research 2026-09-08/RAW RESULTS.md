# London Open FX Momentum - raw paper reproduction

## Rule implemented

- Observe the first 30 minutes after the 08:00 Europe/London open.
- Enter at 08:30 in the sign of that return.
- Reverse the direction for GBPUSD, as reported by the paper.
- Exit at the stated Europe/London time. No profit target, trailing stop, breakeven, or indicator filter.
- Risk is 1% of current equity at a 10x M15 ATR catastrophic stop. This stop is operational protection because the paper uses a time exit and publishes no stop.
- MT5 1-minute OHLC screening includes the recorded Exness spread, commission, swap, and random execution delay.

## Reproducibility limitation

The paper states that the intraday exit was selected on 2012-2018 data but does not publish the selected exit time or its candidate grid. Therefore 16:00, 16:30, and 17:00 London are reported side-by-side and none is silently presented as the author's undisclosed choice.

## Results

| Period | Symbol | Direction | Exit London | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 3y | USDJPY | momentum | 16.0 | +12.70% | 1.08 | 49.16% | 10.70% | 771 | 0.82 | 0.96 |
| 3y | USDJPY | momentum | 16.5 | +3.31% | 1.02 | 49.03% | 12.08% | 771 | 0.21 | 0.24 |
| 3y | USDJPY | momentum | 17.0 | +3.44% | 1.02 | 47.99% | 12.92% | 771 | 0.21 | 0.23 |
| 3y | GBPJPY | momentum | 16.0 | -19.87% | 0.85 | 47.54% | 24.66% | 772 | -1.79 | -0.78 |
| 3y | GBPJPY | momentum | 16.5 | -24.18% | 0.82 | 48.06% | 28.78% | 772 | -2.11 | -0.82 |
| 3y | GBPJPY | momentum | 17.0 | -23.13% | 0.83 | 47.41% | 27.95% | 772 | -1.92 | -0.80 |
| 3y | GBPUSD | reverse | 16.0 | -8.23% | 0.95 | 48.05% | 19.23% | 768 | -0.58 | -0.41 |
| 3y | GBPUSD | reverse | 16.5 | -0.44% | 1.00 | 48.96% | 15.80% | 768 | -0.03 | -0.03 |
| 3y | GBPUSD | reverse | 17.0 | -2.23% | 0.99 | 48.31% | 17.53% | 768 | -0.14 | -0.12 |
| 3y | EURUSD | momentum | 16.0 | +8.78% | 1.05 | 52.60% | 11.74% | 770 | 0.54 | 0.70 |
| 3y | EURUSD | momentum | 16.5 | +0.78% | 1.00 | 51.43% | 15.82% | 770 | 0.05 | 0.05 |
| 3y | EURUSD | momentum | 17.0 | -1.57% | 0.99 | 51.04% | 17.75% | 770 | -0.09 | -0.08 |
| 1y | USDJPY | momentum | 16.0 | +2.95% | 1.06 | 51.94% | 10.72% | 258 | 0.69 | 0.24 |
| 1y | USDJPY | momentum | 16.5 | +0.37% | 1.01 | 50.78% | 12.18% | 258 | 0.08 | 0.03 |
| 1y | USDJPY | momentum | 17.0 | -1.18% | 0.98 | 48.06% | 13.02% | 258 | -0.26 | -0.08 |
| 1y | GBPJPY | momentum | 16.0 | -7.76% | 0.83 | 45.74% | 12.16% | 258 | -1.96 | -0.63 |
| 1y | GBPJPY | momentum | 16.5 | -8.64% | 0.82 | 48.84% | 13.12% | 258 | -2.07 | -0.65 |
| 1y | GBPJPY | momentum | 17.0 | -8.90% | 0.82 | 46.90% | 13.33% | 258 | -2.04 | -0.66 |
| 1y | GBPUSD | reverse | 16.0 | +1.15% | 1.02 | 49.61% | 11.24% | 256 | 0.25 | 0.09 |
| 1y | GBPUSD | reverse | 16.5 | +5.20% | 1.10 | 51.56% | 10.56% | 256 | 1.04 | 0.45 |
| 1y | GBPUSD | reverse | 17.0 | +4.63% | 1.09 | 50.78% | 10.68% | 256 | 0.89 | 0.39 |
| 1y | EURUSD | momentum | 16.0 | +9.39% | 1.19 | 56.47% | 6.07% | 255 | 1.88 | 1.41 |
| 1y | EURUSD | momentum | 16.5 | +8.06% | 1.16 | 56.08% | 6.99% | 255 | 1.52 | 1.06 |
| 1y | EURUSD | momentum | 17.0 | +8.91% | 1.17 | 54.12% | 6.39% | 255 | 1.60 | 1.29 |

## Scope

Raw research only. The active portfolio, website, recommended installer, and BAT files are unchanged pending user review.
