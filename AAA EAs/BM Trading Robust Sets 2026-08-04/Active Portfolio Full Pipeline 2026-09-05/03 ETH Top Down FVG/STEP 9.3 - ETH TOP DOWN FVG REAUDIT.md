# Step 9.3 — ETH Top Down FVG Re-audit

## Goal and test controls

Independently re-test the active ETHUSD M15 strategy at a fixed 1% risk per trade. The audit covers reward/risk from 0.5R to 5R, stop placement, exit management, sessions, the safe regime filter, an untouched locked year, an exact three-year Every Tick validation, and a 10,000-path five-calendar-day block-bootstrap Monte Carlo.

- Broker/tester: Exness MT5, ETHUSD M15.
- Costs: broker spread, commission/swap from the tester and random execution delay.
- Development window: 2023-09-01 through 2025-08-31. This is where alternatives were compared.
- Locked window: 2025-09-01 through 2026-09-01. No further selection was allowed after seeing this window.
- Exact full window: 2023-09-01 through 2026-09-01, MT5 Every Tick.
- Starting balance: $10,000; leverage 1:2000; risk fixed at 1%.

## Decision

**Recommended research upgrade: 4R target, dynamic 50/20 management, all-day entries, current stop (0.10 ATR buffer / 0.30 ATR minimum), safe filter off.**

The raw 4R native exit has the highest exact three-year return (+24.42%), but 4R dynamic is the better consistency choice. It returns +21.77% with PF 1.72, 43.18% wins, 6.68% max drawdown, Sharpe 7.28 and recovery 2.87. It also wins the untouched locked year (+11.41%, PF 1.65) and improves the Monte Carlo 5th-percentile return from -1.06% to -0.57%, while reducing P95 drawdown from 13.67% to 12.05%. The current 3R dynamic setup remains credible and has the highest exact Sharpe (7.44) and win rate (48.89%). The approved 4R upgrade is now deployed, but should still be treated as a demo-forward-test candidate because of the low sample.

The evidence is **cautious**, not strong: only 44–45 trades occur in three years. Tiny session subsets and the very high native Sharpe values must not be treated as precise forecasts.

## Main side-by-side — exact three-year Every Tick

| Configuration | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| Current: 3R + dynamic 50/20 | +16.50% | 1.61 | 48.89% | 6.68% | 45 | 7.44 | 2.21 |
| 3R + native exit | +18.53% | 1.61 | 40.91% | 6.68% | 44 | 6.72 | 2.50 |
| 4R + native exit | +24.42% | 1.73 | 38.64% | 6.38% | 44 | 6.84 | 2.88 |
| 4R + dynamic 50/20 | +21.77% | 1.72 | 43.18% | 6.68% | 44 | 7.28 | 2.87 |

## Monte Carlo — exact three-year daily return blocks

The simulation resamples 5-calendar-day blocks, including inactive days, 10,000 times. It estimates sequence risk from the available history; it cannot prove the strategy will persist.

| Configuration | P(profit) | Return P5 / median / P95 | Median / P95 max DD | P(DD >= 10%) | Ruin |
|---|---:|---:|---:|---:|---:|
| Current: 3R + dynamic 50/20 | 92.51% | -2.05% / +16.20% / +38.90% | 5.63% / 10.96% | 7.60% | 0.00% |
| 3R + native exit | 93.69% | -1.14% / +18.31% / +44.34% | 6.16% / 11.81% | 11.08% | 0.00% |
| 4R + native exit | 94.22% | -1.06% / +23.68% / +58.40% | 7.12% / 13.67% | 19.25% | 0.00% |
| 4R + dynamic 50/20 | 94.45% | -0.57% / +21.42% / +53.29% | 6.24% / 12.05% | 12.08% | 0.00% |
| 3R + dynamic, Asia only | 80.21% | -4.00% / +4.90% / +16.67% | 3.17% / 7.12% | 0.50% | 0.00% |
| 4R + dynamic 50/20, safe filter | 91.70% | -2.18% / +13.96% / +36.08% | 4.90% / 9.62% | 4.17% | 0.00% |

## Development: reward/risk sweep

| Test | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| 0.50R | +0.20% | 1.05 | 69.23% | 2.57% | 13 | 0.34 | 0.08 |
| 0.75R | +2.40% | 1.55 | 69.23% | 2.57% | 13 | 2.64 | 0.93 |
| 1.00R | +2.64% | 1.50 | 61.54% | 4.56% | 13 | 2.12 | 0.57 |
| 1.25R | +2.36% | 1.37 | 53.85% | 4.56% | 13 | 1.50 | 0.51 |
| 1.50R | +4.14% | 1.65 | 53.85% | 4.56% | 13 | 2.38 | 0.90 |
| 2.00R | +4.51% | 1.60 | 46.15% | 4.56% | 13 | 2.15 | 0.98 |
| 2.50R | +6.01% | 1.92 | 50.00% | 4.56% | 12 | 1.93 | 1.31 |
| 3.00R | +8.10% | 2.23 | 50.00% | 4.56% | 12 | 2.52 | 1.76 |
| 4.00R | +12.35% | 2.84 | 50.00% | 4.56% | 12 | 3.41 | 2.69 |
| 5.00R | +10.07% | 2.30 | 41.67% | 6.59% | 12 | 2.47 | 1.31 |

The development curve favored 4R. At 5R, return and PF weakened and drawdown rose, which is why the search stopped at 4R for the locked finalists.

## Development: stop placement

| Test | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| buffer 0.02 / min 0.20 ATR | +8.22% | 2.26 | 50.00% | 4.65% | 12 | 2.61 | 1.76 |
| buffer 0.05 / min 0.30 ATR | +8.13% | 2.23 | 50.00% | 4.61% | 12 | 2.46 | 1.75 |
| current: buffer 0.10 / min 0.30 ATR | +8.10% | 2.23 | 50.00% | 4.56% | 12 | 2.52 | 1.76 |
| buffer 0.10 / min 0.50 ATR | +8.10% | 2.23 | 50.00% | 4.56% | 12 | 2.52 | 1.76 |
| buffer 0.15 / min 0.50 ATR | +8.06% | 2.23 | 50.00% | 4.51% | 12 | 2.57 | 1.78 |
| buffer 0.25 / min 0.50 ATR | +12.35% | 3.16 | 58.33% | 3.62% | 12 | 3.77 | 2.96 |
| buffer 0.20 / min 0.75 ATR | +8.02% | 2.22 | 50.00% | 4.47% | 12 | 2.63 | 1.78 |

The 0.25/0.50 ATR stop appeared superior in development, but failed the locked test: it reduced returns and materially increased drawdown in the 4R native combination. Therefore the current 0.10/0.30 ATR stop is retained.

## Development: exit and trailing management

| Test | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| native exit, no dynamic/BE | +8.10% | 2.23 | 50.00% | 4.56% | 12 | 2.52 | 1.76 |
| current dynamic: 50% close -> 20% SL | +6.36% | 1.97 | 53.85% | 4.56% | 13 | 2.87 | 1.38 |
| break-even at 0.5R | -1.32% | 0.69 | 69.23% | 3.57% | 13 | -1.23 | -0.37 |
| break-even at 1.0R | +3.50% | 1.81 | 58.33% | 4.56% | 12 | 1.40 | 0.76 |
| break-even at 1.5R | +5.54% | 2.02 | 58.33% | 4.56% | 12 | 2.01 | 1.21 |
| 48-bar maximum hold | +5.53% | 1.70 | 38.46% | 4.31% | 13 | 2.51 | 1.17 |
| 192-bar maximum hold | +6.23% | 1.95 | 45.45% | 4.47% | 11 | 1.33 | 1.25 |
| dynamic 60% -> 20% SL | +4.67% | 1.62 | 46.15% | 4.56% | 13 | 2.04 | 1.02 |
| dynamic 75% -> 25% SL | +5.73% | 1.88 | 50.00% | 4.56% | 12 | 1.96 | 1.25 |

Dynamic 50/20 improves win rate but clips some payoff. Break-even at 0.5R destroys the edge. At the selected 4R target, dynamic 50/20 gives the best balance of locked-year stability and Monte Carlo downside protection.

## Development: sessions

| Test | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| all day | +6.36% | 1.97 | 53.85% | 4.56% | 13 | 2.87 | 1.38 |
| Asia 00:00–08:00 UTC | -1.04% | 0.00 | 0.00% | 1.75% | 1 | -0.24 | -0.59 |
| London 07:00–12:00 UTC | +3.57% | 76.88 | 100.00% | 1.61% | 2 | 0.90 | 2.20 |
| New York 13:00–21:00 UTC | +2.36% | 1.56 | 42.86% | 2.75% | 7 | 1.05 | 0.86 |
| London/NY overlap 13:00–16:00 UTC | +5.57% | 6.15 | 75.00% | 2.37% | 4 | 1.31 | 2.32 |

London and overlap look attractive only because they contain 2 and 4 trades respectively. Those samples are unusably small. All-day is the only defensible default.

## Locked-year finalists

| Test | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| Current: 3R + dynamic 50/20 | +10.34% | 1.67 | 50.00% | 6.68% | 26 | 7.93 | 1.47 |
| 3R + native exit | +10.30% | 1.57 | 38.46% | 6.68% | 26 | 6.69 | 1.50 |
| 4R + native exit | +10.31% | 1.52 | 34.62% | 6.38% | 26 | 4.81 | 1.37 |
| 4R + dynamic 50/20 | +11.41% | 1.65 | 42.31% | 6.68% | 26 | 6.40 | 1.65 |
| buffer 0.25 / min 0.50 ATR | +2.50% | 1.13 | 32.00% | 6.96% | 25 | 1.62 | 0.35 |
| combo-stop025-dynamic5020 | +5.34% | 1.34 | 44.00% | 6.96% | 25 | 4.25 | 0.74 |
| combo-rr4-stop025-native | +4.40% | 1.22 | 28.00% | 10.46% | 25 | 2.40 | 0.36 |
| combo-rr4-stop025-dynamic5020 | +6.80% | 1.35 | 32.00% | 8.63% | 25 | 4.10 | 0.68 |
| 4R + dynamic 50/20, safe filter | +6.27% | 1.51 | 38.89% | 5.80% | 18 | 3.89 | 1.07 |
| combo-rr4-stop025-safe | +1.85% | 1.13 | 23.53% | 9.44% | 17 | 1.16 | 0.17 |
| all day | +10.34% | 1.67 | 50.00% | 6.68% | 26 | 7.93 | 1.47 |
| Asia 00:00–08:00 UTC | +6.31% | 1.90 | 50.00% | 5.32% | 12 | 2.82 | 1.14 |
| London 07:00–12:00 UTC | +5.25% | 4.77 | 75.00% | 2.32% | 4 | 1.56 | 2.23 |
| New York 13:00–21:00 UTC | +1.39% | 1.21 | 45.45% | 3.95% | 11 | 0.69 | 0.34 |
| London/NY overlap 13:00–16:00 UTC | +0.53% | 1.17 | 40.00% | 2.15% | 5 | 0.14 | 0.24 |

The locked year rejects the wider stop and safe-filter combinations. The 4R dynamic finalist is strongest here at +11.41% with PF 1.65, while 4R native produces +10.31% with PF 1.52. This is why the final choice uses both the exact three-year result and the Monte Carlo downside view rather than selecting the highest historical return alone.

## Exact three-year finalist set

| Configuration | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| Current: 3R + dynamic 50/20 | +16.50% | 1.61 | 48.89% | 6.68% | 45 | 7.44 | 2.21 |
| 3R + native exit | +18.53% | 1.61 | 40.91% | 6.68% | 44 | 6.72 | 2.50 |
| 4R + native exit | +24.42% | 1.73 | 38.64% | 6.38% | 44 | 6.84 | 2.88 |
| 4R + dynamic 50/20 | +21.77% | 1.72 | 43.18% | 6.68% | 44 | 7.28 | 2.87 |
| 3R + dynamic, Asia only | +5.21% | 1.65 | 46.15% | 5.32% | 13 | 2.46 | 0.95 |
| 4R + dynamic 50/20, safe filter | +14.37% | 1.82 | 46.43% | 6.19% | 28 | 7.58 | 2.13 |

## Safe mode conclusion

Safe mode is kept as an optional user control but is **not recommended as the ETH default**. On the exact three-year run, adding the completed-D1 Markov gate reduces return from +21.77% to +14.37% and trades from 44 to 28, although PF improves from 1.72 to 1.82 and max drawdown falls from 6.68% to 6.19%. On the untouched locked year it reduces return from +11.41% to +6.27%, with PF 1.51 over only 18 trades. The comparison uses the same approved 4R Dynamic 50/20 base on both sides; no older 3R evidence is used.

## Deployment status

The user approved this recommendation. The shared selected preset used by Standard, Full Safe, Best Recommended, 100K, 900 and Dynamic Config BAT flows now uses 4R with Dynamic 50/20. The website default and locked evidence mapping were updated to the same configuration. Full Safe preserves the 4R/Dynamic 50/20 setup and independently enables the completed-D1 Markov gate.
