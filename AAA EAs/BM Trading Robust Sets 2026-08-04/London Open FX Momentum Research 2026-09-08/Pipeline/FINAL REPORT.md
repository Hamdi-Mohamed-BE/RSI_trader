# London Open FX Momentum - full pipeline report

## Test design

- Development: 2021.09.01 to 2024.09.01, MT5 1-minute OHLC.
- Validation: 2024.09.01 to 2025.09.01, MT5 Every Tick.
- Latest: 2025.09.01 to 2026.09.01, MT5 Every Tick.
- Full reference: 2021.09.01 to 2026.09.01, MT5 Every Tick.
- Starting balance: $10,000; dynamic-equity risk: 1% per filled trade.
- The original 08:00/30-minute paper rule remains the raw comparator.
- The research run itself did not change deployment files. After review, the user approved the optimized USDJPY configuration for Calyx; it is now included in the website, shared installer, all portfolio BAT paths, Best Recommended, and the precomputed evidence caches. EURUSD remains rejected and was not deployed.

## USDJPY

**Research decision: WATCH ONLY - positive validation, but not strong enough on its own to claim a proven live edge. Deployment status: user-approved for the Calyx recommended demo/watch portfolio.**

| Window/version | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| raw-validation | +3.12% | 1.07 | 49.80% | 7.21% | 255 | 0.77 | 0.41 |
| selected-validation | +3.84% | 1.09 | 51.43% | 11.94% | 140 | 1.01 | 0.30 |
| raw-latest | +2.76% | 1.06 | 52.33% | 10.82% | 258 | 0.64 | 0.22 |
| selected-latest | +12.72% | 1.33 | 51.85% | 10.13% | 135 | 3.35 | 1.04 |
| raw-full | +15.56% | 1.06 | 49.30% | 10.83% | 1290 | 0.60 | 1.13 |
| selected-full | +178.41% | 1.46 | 53.97% | 12.12% | 693 | 4.41 | 5.71 |

Selected development choices:

- formation: `60m`
- exit: `16-0`
- direction: `both`
- dynamic-stop: `atr-5.0`
- fixed-rr: `time-exit`
- adaptive-rr: `keep-current`
- signal-strength: `min-0.2`
- volume: `median-25`
- spread: `off`
- management: `be-0-75`
- weekdays: `wed-fri`
- london-anchor: `8-0`

Monte Carlo latest-year P(profit): 84.31%; return P5/median/P95: -7.24% / +12.47% / +34.17%; DD median/P95: 7.37% / 15.21%.

## EURUSD

**Decision: REJECT - the development-selected configuration did not survive both later windows.**

| Window/version | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| raw-validation | -3.58% | 0.93 | 50.00% | 9.61% | 256 | -0.74 | -0.36 |
| selected-validation | +7.71% | 1.48 | 56.06% | 2.85% | 66 | 4.44 | 2.44 |
| raw-latest | +9.16% | 1.18 | 56.08% | 6.15% | 255 | 1.84 | 1.36 |
| selected-latest | -4.35% | 0.84 | 47.67% | 9.72% | 86 | -2.38 | -0.43 |
| raw-full | -16.20% | 0.93 | 50.58% | 28.57% | 1287 | -0.67 | -0.56 |
| selected-full | +48.95% | 1.39 | 56.42% | 9.79% | 358 | 4.33 | 3.08 |

Selected development choices:

- formation: `45m`
- exit: `15-0`
- direction: `short-only`
- dynamic-stop: `atr-5.0`
- fixed-rr: `time-exit`
- adaptive-rr: `keep-current`
- signal-strength: `min-0.0`
- volume: `median-0`
- spread: `off`
- management: `be-0-5`
- weekdays: `tue-thu`
- london-anchor: `8-0`

Monte Carlo latest-year P(profit): 27.16%; return P5/median/P95: -15.86% / -4.27% / +7.46%; DD median/P95: 9.24% / 18.18%.

