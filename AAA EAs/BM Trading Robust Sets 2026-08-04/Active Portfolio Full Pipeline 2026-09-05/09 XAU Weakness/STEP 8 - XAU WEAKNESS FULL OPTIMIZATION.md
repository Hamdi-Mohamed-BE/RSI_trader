# Step 8 — XAU Weakness full optimization

## Decision

Promote **XAUUSD M30, structure stop beyond the detected weakness range, 4R target, Dynamic 50/20 only, native trailing off, all-day entries, fixed 1% test risk** as the Standard configuration.

Keep **the same exact setup plus the completed-D1 Markov gate** as Full Safe. Safe nearly halves three-year drawdown and raises PF, but it also reduces return and trade count, so it remains optional rather than the default.

The no-management and native-trailing variants are retained as research evidence. Their window-to-window behavior was less consistent, so they are not deployed.

## Development window — 2023-09-01 to 2025-08-31

| Configuration | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| Previous M15 / 2R Dynamic 50/20 | +25.40% | 1.06 | 44.43% | 25.58% | 691 | 0.98 | 0.92 |
| Recommended M30 / 4R Dynamic 50/20 | +87.59% | 1.40 | 37.22% | 17.87% | 266 | 2.61 | 3.87 |
| Full Safe M30 / 4R Dynamic 50/20 | +44.79% | 1.65 | 42.72% | 11.43% | 103 | 4.16 | 3.28 |
| M30 / 4R no management | +147.66% | 1.57 | 28.51% | 9.78% | 235 | 3.02 | 6.12 |
| M30 / 4R native trailing | +51.17% | 1.24 | 43.67% | 18.92% | 332 | 2.28 | 2.24 |

## Untouched locked year — 2025-09-01 to 2026-09-01

| Configuration | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| Previous M15 / 2R Dynamic 50/20 | +25.31% | 1.14 | 48.53% | 18.88% | 307 | 2.24 | 0.95 |
| Recommended M30 / 4R Dynamic 50/20 | +89.60% | 1.89 | 43.20% | 12.79% | 125 | 5.40 | 3.87 |
| Full Safe M30 / 4R Dynamic 50/20 | +69.41% | 2.09 | 43.68% | 5.47% | 87 | 5.95 | 7.38 |
| M30 / 4R no management | +59.91% | 1.54 | 29.06% | 18.73% | 117 | 3.25 | 1.83 |
| M30 / 4R native trailing | +95.65% | 2.00 | 55.63% | 8.32% | 151 | 7.48 | 6.75 |

## Exact three years — 2023-09-01 to 2026-09-01

| Configuration | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| Previous M15 / 2R Dynamic 50/20 | +48.48% | 1.08 | 45.44% | 19.44% | 997 | 1.18 | 1.48 |
| Recommended M30 / 4R Dynamic 50/20 | +235.67% | 1.58 | 38.97% | 13.25% | 390 | 3.33 | 5.51 |
| Full Safe M30 / 4R Dynamic 50/20 | +134.07% | 1.95 | 44.00% | 6.81% | 175 | 5.11 | 8.18 |
| M30 / 4R no management | +280.16% | 1.52 | 28.49% | 19.46% | 351 | 2.95 | 3.49 |
| M30 / 4R native trailing | +191.57% | 1.53 | 47.22% | 18.91% | 485 | 3.90 | 8.45 |

## Monte Carlo — 10,000 five-day block-bootstrap paths

| Configuration | P(profit) | Return P5 / median / P95 | Median / P95 DD | P(DD >= 20%) | Ruin |
|---|---:|---:|---:|---:|---:|
| Previous M15 / 2R Dynamic 50/20 | 82.11% | -25.27% / +43.25% / +176.06% | 27.63% / 46.64% | 85.08% | 0.00% |
| Recommended M30 / 4R Dynamic 50/20 | 99.99% | +89.28% / +233.42% / +501.90% | 14.19% / 23.08% | 12.01% | 0.00% |
| Full Safe M30 / 4R Dynamic 50/20 | 99.98% | +58.22% / +133.51% / +255.23% | 8.39% / 13.94% | 0.20% | 0.00% |
| M30 / 4R no management | 99.99% | +103.70% / +278.29% / +618.86% | 15.18% / 24.46% | 16.85% | 0.00% |
| M30 / 4R native trailing | 99.98% | +79.09% / +190.86% / +379.38% | 12.11% / 19.62% | 4.33% | 0.00% |

## Cross-market development screen — ATR-normalized research form

| Symbol | Return | PF | Win rate | Max DD | Trades |
|---|---:|---:|---:|---:|---:|
| XAUUSD | +87.59% | 1.40 | 37.22% | 17.87% | 266 |
| XAGUSD | -46.72% | 0.73 | 26.28% | 49.51% | 312 |
| US30 | +9.60% | 1.04 | 31.31% | 29.98% | 297 |
| USTEC | -16.85% | 0.92 | 28.53% | 25.25% | 312 |
| BTCUSD | +12.48% | 1.04 | 32.41% | 24.32% | 361 |
| GBPJPY | -49.28% | 0.69 | 23.97% | 52.02% | 267 |

XAU Weakness stays confined to XAUUSD. BTC and US30 were only marginal in development, while XAG, US100 and GBPJPY failed.

## Implementation notes

- Risk remains 1%.
- Dynamic 50/20 moves the stop after a newly completed M15 candle closes at least 50% of the original entry-to-target path; it locks 20% of that path.
- Native R-trailing is disabled. Running both mechanisms reduced robustness.
- The signal uses M30 equal-high/equal-low weakness structure, a 2 ATR impulse requirement, 0.20 ATR level tolerance, 0.05 ATR breakout buffer and an eight-bar pending-order expiry.
- The reward/risk input and native trailing are now connected to the XAU Weakness execution path; both were previously exposed but ignored.
- Standard has the Markov gate off. Full Safe applies the separately tested gate to the same selected configuration.
- Results are historical and do not guarantee future performance.

## Artifacts

- Final chart: `XAU Weakness - FINAL DECISION AND MONTE CARLO.png`
- Development comparison: `XAU Weakness - DEVELOPMENT CONFIG COMPARISON.png`
- Locked comparison: `XAU Weakness - LOCKED CONFIG COMPARISON.png`
- Three-year comparison: `XAU Weakness - THREEYEAR CONFIG COMPARISON.png`
- Monte Carlo data: `monte-carlo-results.csv` and `monte-carlo-results.json`
