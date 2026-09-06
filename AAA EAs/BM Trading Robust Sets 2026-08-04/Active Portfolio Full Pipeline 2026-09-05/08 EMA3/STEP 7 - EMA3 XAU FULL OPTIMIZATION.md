# Step 7 — EMA3 XAUUSD full optimization

## Decision

Promote **XAUUSD H4, original five-bar pivot stop, 1.7R target, Dynamic 60/20 only, native trailing off, all-day entries, fixed 1% risk** as the Standard configuration.

Keep **the same exact setup plus the completed-D1 Markov gate** as Full Safe. Safe materially reduces three-year drawdown and increases PF, but it also reduces return and trade count, so it remains optional rather than the default.

The fixed-15 and ATR-1.5/2.5R variants made more historical money, but their PF and drawdown were worse. They are retained as research evidence, not deployed as the core preset.

## Development window — 2023-09-01 to 2025-08-31

| Configuration | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| Previous Dynamic 50/20 + native trail | +10.28% | 1.23 | 56.07% | 7.60% | 107 | 1.12 | 1.14 |
| Recommended Dynamic 60/20 only | +19.52% | 1.51 | 56.04% | 7.74% | 91 | 1.91 | 1.98 |
| Full Safe Dynamic 60/20 only | +12.91% | 1.83 | 57.50% | 3.96% | 40 | 2.68 | 2.77 |
| Higher-return ATR 1.5 / 2.5R | +44.99% | 1.56 | 52.90% | 9.58% | 138 | 3.14 | 2.97 |
| Highest-return fixed 15 stop | +42.02% | 1.39 | 57.35% | 9.08% | 211 | 3.26 | 3.03 |

## Untouched locked year — 2025-09-01 to 2026-09-01

| Configuration | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| Previous Dynamic 50/20 + native trail | +21.27% | 2.98 | 72.73% | 2.86% | 44 | 5.99 | 6.12 |
| Recommended Dynamic 60/20 only | +19.57% | 2.77 | 70.73% | 3.45% | 41 | 4.95 | 4.68 |
| Full Safe Dynamic 60/20 only | +18.74% | 2.97 | 71.79% | 3.26% | 39 | 5.24 | 4.78 |
| Higher-return ATR 1.5 / 2.5R | +29.77% | 1.85 | 54.43% | 5.18% | 79 | 4.95 | 4.56 |
| Highest-return fixed 15 stop | +51.40% | 1.46 | 54.74% | 8.81% | 190 | 9.01 | 3.89 |

## Exact three years — 2023-09-01 to 2026-09-01

| Configuration | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| Previous Dynamic 50/20 + native trail | +33.52% | 1.57 | 60.53% | 7.69% | 152 | 2.36 | 3.70 |
| Recommended Dynamic 60/20 only | +40.52% | 1.74 | 59.70% | 7.75% | 134 | 2.53 | 4.11 |
| Full Safe Dynamic 60/20 only | +33.56% | 2.30 | 64.94% | 3.95% | 77 | 3.79 | 6.31 |
| Higher-return ATR 1.5 / 2.5R | +79.44% | 1.59 | 52.94% | 9.67% | 221 | 3.33 | 5.55 |
| Highest-return fixed 15 stop | +120.18% | 1.44 | 56.00% | 9.05% | 400 | 4.64 | 6.10 |

## Monte Carlo — 10,000 five-day block-bootstrap paths

| Configuration | P(profit) | Return P5 / median / P95 | Median / P95 DD | P(DD >= 20%) | Ruin |
|---|---:|---:|---:|---:|---:|
| Previous Dynamic 50/20 + native trail | 99.37% | +10.11% / +33.33% / +62.10% | 5.96% / 10.66% | 0.01% | 0.00% |
| Recommended Dynamic 60/20 only | 99.80% | +15.89% / +40.44% / +70.63% | 5.44% / 9.66% | 0.00% | 0.00% |
| Full Safe Dynamic 60/20 only | 99.99% | +16.18% / +33.66% / +53.80% | 3.26% / 5.68% | 0.00% | 0.00% |
| Higher-return ATR 1.5 / 2.5R | 99.97% | +33.22% / +79.10% / +144.40% | 7.53% / 12.75% | 0.11% | 0.00% |
| Highest-return fixed 15 stop | 99.99% | +52.56% / +120.33% / +222.92% | 8.97% / 14.88% | 0.44% | 0.00% |

## Cross-market development screen — ATR-normalized research form

| Symbol | Return | PF | Win rate | Max DD | Trades |
|---|---:|---:|---:|---:|---:|
| XAUUSD | +34.88% | 1.40 | 57.14% | 7.44% | 182 |
| XAGUSD | -23.62% | 0.73 | 44.92% | 26.74% | 187 |
| US30 | +10.55% | 1.11 | 55.68% | 10.90% | 185 |
| USTEC | +12.32% | 1.13 | 55.43% | 8.57% | 184 |
| BTCUSD | +51.40% | 1.43 | 56.71% | 11.42% | 231 |
| GBPJPY | +0.10% | 1.00 | 51.63% | 16.17% | 184 |

EMA3 stays confined to XAUUSD. BTC was positive, but its untouched-year PF fell to 1.25 with 10.21% drawdown; XAG and GBPJPY failed, while US30 and US100 were weak.

## Implementation notes

- Risk remains 1%.
- Dynamic 60/20 moves the stop after a newly completed M15 candle closes at least 60% of the original entry-to-target path; it locks 20% of that path.
- Native R-trailing is disabled. Running both mechanisms reduced robustness.
- The signal remains H4 with the original EMA 20/50 alignment, EMA 200 six-bar slope, five-bar closing breakout and opposite five-bar extreme stop.
- Standard has the Markov gate off. Full Safe applies the separately tested gate to the same selected configuration.
- Results are historical and do not guarantee future performance.

## Artifacts

- Final chart: `EMA3 XAU - FINAL DECISION AND MONTE CARLO.png`
- Development comparison: `EMA3 - DEVELOPMENT CONFIG COMPARISON.png`
- Locked comparison: `EMA3 - LOCKED CONFIG COMPARISON.png`
- Three-year comparison: `EMA3 - THREEYEAR CONFIG COMPARISON.png`
- Monte Carlo data: `monte-carlo-results.csv` and `monte-carlo-results.json`
