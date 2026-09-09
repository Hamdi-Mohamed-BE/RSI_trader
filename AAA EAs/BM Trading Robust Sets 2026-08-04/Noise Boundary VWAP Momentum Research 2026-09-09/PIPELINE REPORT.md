# USTEC Noise Boundary VWAP Momentum - full Calyx pipeline

Decision: **REJECT — the untouched post-selection window failed.**

Every pipeline case uses a defined stop and dynamic 1% equity risk. Selection used only the development window; the locked Every-Tick window remained untouched until all settings were frozen.

## Selected development settings

| Phase | Winner | Return | PF | Win rate | Max DD | Trades |
|---|---|---:|---:|---:|---:|---:|
| stop | percent-025 | +116.17% | 1.19 | 30.41% | 18.30% | 651 |
| lookback | sessions-10 | +122.78% | 1.18 | 30.60% | 16.36% | 647 |
| band | mult-100-paper | +122.78% | 1.18 | 30.60% | 16.36% | 647 |
| decision | every-30m-paper | +122.78% | 1.18 | 30.60% | 16.36% | 647 |
| session | no-lunch-1200-1400 | +129.89% | 1.19 | 36.18% | 15.05% | 680 |
| direction | long-only | +81.15% | 1.34 | 40.43% | 9.58% | 329 |
| exit | vwap-only | +90.63% | 1.36 | 40.92% | 10.63% | 325 |
| target | dynamic-indicator-exit | +90.63% | 1.36 | 40.92% | 10.63% | 325 |
| management | be-075 | +86.32% | 1.42 | 57.14% | 8.51% | 371 |
| regime | none | +86.32% | 1.42 | 57.14% | 8.51% | 371 |
| adx | none | +86.32% | 1.42 | 57.14% | 8.51% | 371 |
| relative-volume | none | +86.32% | 1.42 | 57.14% | 8.51% | 371 |
| daily-volatility | atr-min-150 | +87.73% | 1.73 | 60.68% | 10.36% | 234 |

## Final native MT5 results

| Version | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| baseline-locked | -59.52% | 0.85 | 24.55% | 69.23% | 660 | -2.91 | -0.67 |
| optimized-locked | -3.87% | 0.93 | 30.57% | 17.82% | 157 | -1.95 | -0.21 |
| optimized-latest-1y | +5.68% | 1.19 | 34.67% | 10.89% | 75 | 5.38 | 0.50 |
| optimized-full-5y | +61.89% | 1.28 | 30.18% | 18.13% | 391 | 7.65 | 1.97 |

## Locked-window Monte Carlo — 10,000 resamples

- Probability profitable: 36.14%
- Return P5 / median / P95: -23.20% / -4.15% / +14.87%
- Max DD median / P95: 13.31% / 27.08%

The MT5 CFD VWAP uses Exness tick volume rather than consolidated exchange volume, so this remains an adapted transfer test.

No website, BAT, installer, recommended-system or active-portfolio file was changed. The selected SET is research-only pending user review.
