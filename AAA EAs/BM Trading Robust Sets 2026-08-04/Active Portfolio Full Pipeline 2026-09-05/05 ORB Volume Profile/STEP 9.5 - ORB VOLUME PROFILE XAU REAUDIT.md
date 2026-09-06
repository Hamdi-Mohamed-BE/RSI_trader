# Step 9.5 - ORB Volume Profile XAU Re-audit

## Goal and controls

Complete the active XAUUSD M5 ORB Volume Profile pipeline at a fixed 1% risk. Development used 2023-09-01 through 2025-08-31, the untouched locked year used 2025-09-01 through 2026-09-01, and final validation used exact three-year MT5 Every Tick history. Monte Carlo uses 10,000 five-calendar-day block-bootstrap paths.

## Recommendation

**Keep the currently deployed 09:30 New York, 15-minute opening range, M5 direct-breakout configuration with 2.5R, opposite-range stop capped at 2 ATR, Dynamic 50/20, no profile gate, no Safe/Markov gate, and fixed 1% risk. Also deploy the validated 0.75R Dynamic 50/20 configuration as a separate high-win instance with a unique magic number.**

The 2.5R instance delivered the strongest broad three-year return with 169 trades and a 5.85% drawdown. The 0.75R instance used the same 169 signals and raised the historical win rate to 69.82%, while reducing three-year return to 22.41%. The two instances can therefore coexist as return-focused and win-rate-focused sleeves, but their simultaneous planned risks add together because their signals are strongly correlated.

## Untouched locked-year MT5 results

| Configuration | Return | PF | Win | DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| Current: 2.5R, Dynamic 50/20 | +13.46% | 1.91 | 48.98% | 5.98% | 49 | 11.24 | 2.18 |
| High-win: 0.75R, Dynamic 50/20 | +6.31% | 1.56 | 69.39% | 3.10% | 49 | 11.80 | 1.98 |
| Volume confirmed: 2.5R, Dynamic 50/20 | +12.57% | 2.88 | 52.17% | 2.92% | 23 | 19.17 | 4.17 |
| Strict volume + EMA/VWAP: 2.5R, Dynamic 50/20 | +8.46% | 3.04 | 53.85% | 2.96% | 13 | 9.33 | 2.77 |

## Exact three-year Every Tick results

| Configuration | Return | PF | Win | DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| Current: 2.5R, Dynamic 50/20 | +49.38% | 1.68 | 46.75% | 5.85% | 169 | 9.86 | 6.18 |
| High-win: 0.75R, Dynamic 50/20 | +22.41% | 1.46 | 69.82% | 5.32% | 169 | 11.36 | 4.11 |
| Volume confirmed: 2.5R, Dynamic 50/20 | +25.92% | 2.01 | 45.59% | 5.64% | 68 | 14.94 | 4.36 |
| Strict volume + EMA/VWAP: 2.5R, Dynamic 50/20 | +21.70% | 2.72 | 52.78% | 3.29% | 36 | 25.86 | 6.16 |

## Monte Carlo

| Configuration | P(profit) | Return P5 / median / P95 | Median / P95 DD | P(DD >=10%) | P(DD >=20%) | Ruin |
|---|---:|---:|---:|---:|---:|---:|
| Current: 2.5R, Dynamic 50/20 | 99.69% | +16.23% / +49.30% / +93.09% | 6.84% / 11.99% | 12.97% | 0.04% | 0.00% |
| High-win: 0.75R, Dynamic 50/20 | 98.98% | +6.08% / +22.69% / +41.64% | 5.06% / 9.19% | 2.96% | 0.00% | 0.00% |
| Volume confirmed: 2.5R, Dynamic 50/20 | 98.88% | +6.41% / +25.74% / +50.93% | 4.80% / 9.02% | 2.67% | 0.00% | 0.00% |
| Strict volume + EMA/VWAP: 2.5R, Dynamic 50/20 | 99.32% | +6.54% / +21.83% / +41.14% | 2.96% / 5.75% | 0.17% | 0.00% | 0.00% |

## Development results for the same finalists

| Configuration | Return | PF | Win | DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| Current: 2.5R, Dynamic 50/20 | +32.09% | 1.61 | 55.83% | 5.56% | 120 | 9.47 | 4.55 |
| High-win: 0.75R, Dynamic 50/20 | +15.36% | 1.43 | 70.00% | 5.30% | 120 | 11.50 | 2.82 |
| Volume confirmed: 2.5R, Dynamic 50/20 | +12.51% | 1.71 | 57.78% | 5.64% | 45 | 11.76 | 2.11 |
| Strict volume + EMA/VWAP: 2.5R, Dynamic 50/20 | +12.21% | 2.58 | 65.22% | 3.29% | 23 | 22.03 | 3.46 |

## Interpretation

- The current Dynamic 50/20 configuration returned +49.38% over the exact three years, with PF 1.68, 46.75% wins, 5.85% maximum drawdown and 169 trades.
- The volume-confirmed option improved PF to 2.01, but return fell to +25.92% and trades fell to 68.
- The strict confirmation option produced PF 2.72 and 3.29% drawdown, but only 36 trades; it is too selective to replace the core version yet.
- The 0.75R option raised win rate to 69.82%, but reduced return to +22.41%; a high win rate alone did not produce the best system.
- Profile value-area, POC and LVN gates generated zero trades in this implementation and are disabled. The Safe/Markov gate was negative in development and remains disabled.
- Historical and simulated results are not a promise of future profit.
