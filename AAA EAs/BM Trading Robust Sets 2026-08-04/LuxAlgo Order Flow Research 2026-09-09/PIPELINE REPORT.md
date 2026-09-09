# Value Area Reversion — full Calyx pipeline

Source: LuxAlgo's *Stupid Simple Order Flow Strategy* video and official Value Area Reversion Signals specification.

All configurations risk 1% of current equity. Development-only sequential selection was followed by an untouched Every-Tick locked window. Broker costs and random execution delay are included.

## Final native MT5 results

| Asset | Version | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| XAU | baseline-raw-locked | +14.03% | 1.22 | 54.89% | 9.59% | 133 | 3.58 | 1.28 |
| XAU | optimized-locked | +6.90% | 1.54 | 63.16% | 4.28% | 38 | 8.89 | 1.47 |
| XAU | optimized-latest-1y | -0.42% | 0.80 | 62.50% | 2.84% | 8 | -0.54 | -0.15 |
| XAU | optimized-full-5y | +25.50% | 1.84 | 63.16% | 4.30% | 76 | 13.08 | 4.60 |
| XAG | baseline-raw-locked | -13.64% | 0.67 | 51.69% | 14.45% | 89 | -5.00 | -0.94 |
| XAG | optimized-locked | -5.60% | 0.68 | 67.24% | 7.68% | 58 | -5.00 | -0.72 |
| XAG | optimized-latest-1y | -1.20% | 0.81 | 72.00% | 4.04% | 25 | -3.76 | -0.29 |
| XAG | optimized-full-5y | -3.02% | 0.89 | 70.00% | 9.69% | 90 | -1.99 | -0.29 |
| BTC | baseline-raw-locked | -9.99% | 0.92 | 49.82% | 25.78% | 271 | -1.29 | -0.38 |
| BTC | optimized-locked | +3.30% | 1.34 | 56.67% | 5.71% | 30 | 3.47 | 0.56 |
| BTC | optimized-latest-1y | +1.30% | 1.66 | 71.43% | 1.83% | 7 | 0.93 | 0.70 |
| BTC | optimized-full-5y | +18.46% | 1.78 | 58.33% | 7.49% | 60 | 7.27 | 2.40 |
| US100 | baseline-raw-locked | -23.28% | 0.65 | 49.64% | 35.29% | 137 | -5.00 | -0.59 |
| US100 | optimized-locked | -5.29% | 0.46 | 65.85% | 6.97% | 41 | -5.00 | -0.75 |
| US100 | optimized-latest-1y | -3.94% | 0.26 | 61.11% | 5.42% | 18 | -5.00 | -0.72 |
| US100 | optimized-full-5y | -0.08% | 0.99 | 77.03% | 6.99% | 74 | -0.12 | -0.01 |

## Decisions

- **XAU:** WATCH ONLY — some locked-window edge remains, but robustness gates failed.
- **XAG:** REJECT — the untouched post-selection window failed.
- **BTC:** WATCH ONLY — some locked-window edge remains, but robustness gates failed.
- **US100:** REJECT — the untouched post-selection window failed.

## Evidence boundary

The source itself warns that this TradingView-style reconstruction is not Fabio Valentini's real order flow. The MT5 implementation is one step further removed because CFD/spot symbols expose broker tick activity rather than centralized exchange volume. Results therefore test a reproducible value-area proxy, not a genuine order-book edge.

No website, BAT, installer, recommended-system or active-portfolio file was changed. All SET files are research-only pending user review.
