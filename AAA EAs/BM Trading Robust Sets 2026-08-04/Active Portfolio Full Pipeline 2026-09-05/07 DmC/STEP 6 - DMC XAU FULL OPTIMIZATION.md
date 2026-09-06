# Step 6 — DmC XAUUSD full optimization

## Decision

Promote **XAUUSD H1, Asia-only, fixed $22.50 price-distance stop, 3R target, Dynamic 50/20, Safe gate off, fixed 1% risk** as the recommended DmC configuration.

The current Safe 1.7R all-day version had the better recent win rate and PF, but it lost money in the two-year development window. Asia 3R was profitable in both independent segments and produced the best three-year balance between return, drawdown and recovery. Asia 4R returned slightly more over three years, but its locked-year drawdown and Monte Carlo downside were worse.

## Development window — 2023-09-01 to 2025-08-31

| Configuration | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| Current Safe 1.7R all day | -1.52% | 0.96 | 50.54% | 8.95% | 93 | -0.27 | -0.16 |
| Asia 1.7R | +13.17% | 1.16 | 53.51% | 14.21% | 185 | 1.00 | 0.76 |
| Recommended Asia 3R | +35.43% | 1.42 | 41.04% | 10.80% | 134 | 1.88 | 2.41 |
| Asia 4R | +44.43% | 1.54 | 36.21% | 17.08% | 116 | 2.04 | 1.72 |
| Asia 5R | +32.05% | 1.44 | 29.70% | 17.52% | 101 | 1.39 | 1.32 |

## Untouched locked year — 2025-09-01 to 2026-09-01

| Configuration | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| Current Safe 1.7R all day | +48.75% | 1.61 | 57.83% | 5.52% | 166 | 6.97 | 5.65 |
| Asia 1.7R | +5.48% | 1.10 | 49.59% | 7.48% | 123 | 1.25 | 0.69 |
| Recommended Asia 3R | +12.04% | 1.18 | 40.52% | 10.14% | 116 | 1.79 | 0.99 |
| Asia 4R | +9.55% | 1.12 | 32.41% | 14.87% | 108 | 1.08 | 0.50 |
| Asia 5R | +15.39% | 1.18 | 25.96% | 18.94% | 104 | 1.50 | 0.58 |

## Exact three years — 2023-09-01 to 2026-09-01

| Configuration | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| Current Safe 1.7R all day | +38.36% | 1.36 | 55.22% | 9.29% | 230 | 2.81 | 3.82 |
| Asia 1.7R | +15.62% | 1.11 | 51.95% | 14.36% | 308 | 0.82 | 0.90 |
| Recommended Asia 3R | +53.60% | 1.30 | 40.80% | 11.55% | 250 | 1.74 | 3.41 |
| Asia 4R | +58.70% | 1.30 | 34.38% | 14.99% | 224 | 1.59 | 2.10 |
| Asia 5R | +53.33% | 1.28 | 27.80% | 19.13% | 205 | 1.32 | 1.49 |

## Monte Carlo — 10,000 five-day block-bootstrap paths

| Configuration | P(profit) | Return P5 / median / P95 | Median / P95 DD | P(DD >= 20%) | Ruin |
|---|---:|---:|---:|---:|---:|
| Current Safe 1.7R all day | 98.36% | +8.14% / +38.37% / +79.32% | 8.62% / 15.52% | 0.65% | 0.00% |
| Asia 1.7R | 79.04% | -13.06% / +15.21% / +53.76% | 13.45% / 24.70% | 14.67% | 0.00% |
| Recommended Asia 3R | 97.39% | +6.71% / +55.13% / +127.18% | 12.71% / 22.58% | 9.10% | 0.00% |
| Asia 4R | 96.77% | +4.84% / +59.87% / +148.15% | 14.61% / 25.44% | 17.12% | 0.00% |
| Asia 5R | 93.83% | -2.49% / +53.03% / +150.41% | 16.38% / 28.52% | 27.94% | 0.00% |

## Cross-market conclusion

The portable ATR-stop form did not transfer robustly. Development results were XAU -4.64%, XAG -78.09%, US30 -31.57%, US100 -38.76%, BTC -28.56%, and GBPJPY +19.28%; GBPJPY then failed the locked year (-22.58%). Keep DmC confined to XAUUSD.

## Implementation notes

- Risk remains 1%.
- The selected setup uses Dynamic 50/20. DmC does not call the shared native R-trailing routine, so the generic native trailing input is explicitly disabled to avoid implying otherwise.
- The session wrapper is Asia only, interpreted in UTC using the broker offset input.
- Full Safe preserves the same validated Asia 3R inputs for DmC. The exact Asia 3R + Markov combination is not promoted until a dedicated tester run completes successfully.
- New portable stop/timeframe inputs remain in the EA code for future research, but the installed preset uses the original fixed stop and H1 signal.
- Results are historical and do not guarantee future performance.

## Artifacts

- Final chart: `DMC XAU - FINAL DECISION AND MONTE CARLO.png`
- Development comparison: `DMC - DEVELOPMENT CONFIG COMPARISON.png`
- Locked comparison: `DMC - LOCKED CONFIG COMPARISON.png`
- Three-year comparison: `DMC - THREEYEAR CONFIG COMPARISON.png`
- Monte Carlo data: `monte-carlo-results.csv` and `monte-carlo-results.json`
