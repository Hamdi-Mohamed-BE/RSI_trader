# Step 9.6 — Asia Breakout XAU Re-audit

## Goal and controls

Re-test the active XAUUSD Asia-session breakout at fixed 1% risk using its actual MT5 logic, broker costs and random execution delay. Development used 2023-09-01 through 2025-08-31. The untouched locked year used 2025-09-01 through 2026-09-01. Final validation used exact three-year Every Tick history. Monte Carlo uses 10,000 five-calendar-day block-bootstrap paths.

## Decision

**Keep the currently deployed optimized Safe configuration unchanged:** XAUUSD H1, 3R, Asia range 00:00–08:00 UTC, entries 08:00–13:00 UTC, 3% breakout buffer, midpoint stop, native 2R/0.5R trail plus Dynamic 50/20, all-day wrapper, completed-D1 no-lookahead Markov Safe gate, and fixed 1% risk.

It led the untouched year (+32.07%, PF 1.76, 5.67% DD, 73 trades) and the full three years (+44.57%, PF 1.56, 6.27% DD, 130 trades). The alternative opposite-edge stops improved development and slightly improved full-period PF, but failed to beat the current setup on the locked year. Signal-candle stops were clearly harmful. H1 remained preferable to M30/M15. The London wrapper produced only 35 development trades and is not adopted.

No BAT, selected preset, live EA binary, or website record was changed. The existing installed selection already matches the recommendation.

## Untouched locked-year MT5 results

| Configuration | Return | PF | Win | DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| Current: midpoint, 3R, native + Dynamic 50/20, Safe | +32.07% | 1.76 | 46.58% | 5.67% | 73 | 6.45 | 4.45 |
| Current rules, Safe off | +18.51% | 1.21 | 40.00% | 15.85% | 130 | 2.15 | 0.85 |
| Opposite edge + 3% buffer, Safe | +18.97% | 1.73 | 49.12% | 5.92% | 57 | 3.90 | 2.67 |
| Opposite edge + 10%, zero breakout buffer, Safe | +16.95% | 1.64 | 48.21% | 6.25% | 56 | 3.37 | 2.25 |
| Opposite edge + 10%, 08:00–12:00, Safe | +18.61% | 1.79 | 49.02% | 5.40% | 51 | 4.72 | 2.87 |

## Exact three-year Every Tick results

| Configuration | Return | PF | Win | DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| Current: midpoint, 3R, native + Dynamic 50/20, Safe | +44.57% | 1.56 | 46.92% | 6.27% | 130 | 4.79 | 5.12 |
| Current rules, Safe off | +21.24% | 1.08 | 39.23% | 16.65% | 413 | 0.71 | 0.90 |
| Opposite edge + 3% buffer, Safe | +38.22% | 1.65 | 47.75% | 5.87% | 111 | 3.69 | 5.23 |
| Opposite edge + 10%, zero breakout buffer, Safe | +37.52% | 1.65 | 47.66% | 6.75% | 107 | 3.61 | 4.74 |
| Opposite edge + 10%, 08:00–12:00, Safe | +36.67% | 1.72 | 47.92% | 6.12% | 96 | 3.96 | 4.97 |

## Monte Carlo

| Configuration | P(profit) | Return P5 / median / P95 | Median / P95 DD | P(DD ≥10%) | P(DD ≥20%) | Ruin |
|---|---:|---:|---:|---:|---:|---:|
| Current: midpoint, 3R, native + Dynamic 50/20, Safe | 99.21% | +11.67% / +44.62% / +89.26% | 7.77% / 13.85% | 22.61% | 0.37% | 0.00% |
| Current rules, Safe off | 77.90% | -18.87% / +21.51% / +85.46% | 19.13% / 33.94% | 97.96% | 44.91% | 0.00% |
| Opposite edge + 3% buffer, Safe | 99.30% | +10.59% / +37.85% / +73.76% | 6.32% / 11.08% | 8.96% | 0.02% | 0.00% |
| Opposite edge + 10%, zero breakout buffer, Safe | 99.34% | +11.35% / +37.47% / +71.42% | 5.98% / 10.66% | 7.25% | 0.02% | 0.00% |
| Opposite edge + 10%, 08:00–12:00, Safe | 99.30% | +11.31% / +36.55% / +68.90% | 5.84% / 10.50% | 6.37% | 0.02% | 0.00% |

## Development — Reward-risk sweep

| Configuration | Return | PF | Win | DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| rr-050 | -13.82% | 0.86 | 68.53% | 15.67% | 375 | -2.54 | -0.88 |
| rr-075 | -7.24% | 0.94 | 63.32% | 10.98% | 368 | -1.01 | -0.66 |
| rr-100 | -0.36% | 1.00 | 60.16% | 12.15% | 364 | -0.04 | -0.03 |
| rr-150 | +6.71% | 1.04 | 52.92% | 14.88% | 342 | 0.53 | 0.43 |
| rr-200 | +3.89% | 1.02 | 46.27% | 15.25% | 322 | 0.25 | 0.24 |
| rr-250 | +2.22% | 1.01 | 42.16% | 19.56% | 306 | 0.12 | 0.11 |
| rr-300 | +3.28% | 1.02 | 38.87% | 20.14% | 283 | 0.17 | 0.15 |
| rr-400 | +3.34% | 1.02 | 34.96% | 26.41% | 266 | 0.15 | 0.11 |
| rr-500 | +5.07% | 1.03 | 35.09% | 27.09% | 265 | 0.22 | 0.17 |
## Development — Stop placement

| Configuration | Return | PF | Win | DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| stop-midpoint | +3.28% | 1.02 | 38.87% | 20.14% | 283 | 0.17 | 0.15 |
| stop-opposite-b000 | +25.61% | 1.26 | 43.33% | 10.33% | 180 | 1.22 | 2.21 |
| stop-opposite-b003 | +26.90% | 1.28 | 43.68% | 9.77% | 174 | 1.32 | 2.43 |
| stop-opposite-b010 | +36.13% | 1.38 | 44.10% | 10.80% | 161 | 1.66 | 2.71 |
| stop-signal-b000 | -16.31% | 0.91 | 35.03% | 24.73% | 314 | -0.98 | -0.62 |
| stop-signal-b003 | -11.21% | 0.94 | 36.75% | 22.09% | 302 | -0.64 | -0.47 |
| stop-signal-b010 | -7.87% | 0.95 | 36.64% | 22.15% | 292 | -0.43 | -0.33 |
## Development — Trade management

| Configuration | Return | PF | Win | DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| manage-none | +30.23% | 1.17 | 28.45% | 22.26% | 232 | 1.01 | 1.17 |
| manage-native-200-050 | +9.53% | 1.06 | 35.07% | 21.66% | 268 | 0.42 | 0.39 |
| manage-native-150-075 | +5.87% | 1.04 | 41.61% | 19.35% | 286 | 0.29 | 0.28 |
| manage-native-100-050 | +3.82% | 1.02 | 50.31% | 13.70% | 322 | 0.26 | 0.25 |
| manage-dynamic5020-only | +14.04% | 1.09 | 39.02% | 24.46% | 264 | 0.60 | 0.50 |
| manage-dynamic6020-only | +13.00% | 1.08 | 34.77% | 24.71% | 256 | 0.52 | 0.47 |
| manage-dynamic7525-only | +20.33% | 1.12 | 30.29% | 23.35% | 241 | 0.74 | 0.75 |
| manage-dynamic5020-native | +3.28% | 1.02 | 38.87% | 20.14% | 283 | 0.17 | 0.15 |
| manage-dynamic6020-native | +4.85% | 1.03 | 35.79% | 21.60% | 271 | 0.22 | 0.21 |
## Development — Session filter

| Configuration | Return | PF | Win | DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| session-all | +3.28% | 1.02 | 38.87% | 20.14% | 283 | 0.17 | 0.15 |
| session-asia | +0.00% | 0.00 | 0.00% | 0.00% | 0 | 0.00 | 0.00 |
| session-london | +18.90% | 2.22 | 57.14% | 7.18% | 35 | 8.61 | 2.48 |
| session-new-york | -0.98% | 0.99 | 37.15% | 19.87% | 253 | -0.05 | -0.05 |
| session-overlap | +8.86% | 1.06 | 38.62% | 15.98% | 246 | 0.48 | 0.53 |
## Development — Signal timeframe

| Configuration | Return | PF | Win | DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| timeframe-h1 | +3.28% | 1.02 | 38.87% | 20.14% | 283 | 0.17 | 0.15 |
| timeframe-m30 | +6.62% | 1.04 | 37.69% | 22.94% | 321 | 0.30 | 0.27 |
| timeframe-m15 | +6.00% | 1.03 | 37.14% | 25.58% | 350 | 0.26 | 0.20 |
## Development — Entry window

| Configuration | Return | PF | Win | DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| window-0800-1000 | +1.84% | 1.02 | 38.85% | 17.52% | 157 | 0.18 | 0.10 |
| window-0800-1200 | +18.73% | 1.12 | 40.31% | 16.22% | 258 | 0.97 | 1.06 |
| window-0800-1300 | +3.28% | 1.02 | 38.87% | 20.14% | 283 | 0.17 | 0.15 |
| window-0800-1500 | +9.45% | 1.05 | 39.47% | 16.26% | 304 | 0.44 | 0.55 |
## Development — Safe filter

| Configuration | Return | PF | Win | DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| safe-off | +3.28% | 1.02 | 38.87% | 20.14% | 283 | 0.17 | 0.15 |
| safe-on | +12.17% | 1.33 | 46.15% | 5.99% | 65 | 3.07 | 1.80 |
## Development — Focused combinations

| Configuration | Return | PF | Win | DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| Current rules, Safe off | +3.28% | 1.02 | 38.87% | 20.14% | 283 | 0.17 | 0.15 |
| Current: midpoint, 3R, native + Dynamic 50/20, Safe | +12.17% | 1.33 | 46.15% | 5.99% | 65 | 3.07 | 1.80 |
| final-rr3-dynamic5020-only | +14.04% | 1.09 | 39.02% | 24.46% | 264 | 0.60 | 0.50 |
| final-rr3-native-only | +9.53% | 1.06 | 35.07% | 21.66% | 268 | 0.42 | 0.39 |
| final-rr25-dynamic5020-only | -2.30% | 0.99 | 41.24% | 25.73% | 291 | -0.11 | -0.08 |
| combo-opposite010-rr200 | +29.57% | 1.31 | 52.94% | 11.81% | 204 | 1.62 | 2.14 |
| combo-opposite010-rr250 | +14.30% | 1.16 | 46.96% | 9.54% | 181 | 0.82 | 1.39 |
| combo-opposite010-rr300 | +36.13% | 1.38 | 44.10% | 10.80% | 161 | 1.66 | 2.71 |
| combo-opposite010-rr400 | +10.50% | 1.15 | 34.96% | 14.97% | 123 | 0.57 | 0.65 |
| combo-opposite010-rr300-safe | +15.11% | 1.51 | 45.45% | 6.38% | 55 | 2.80 | 2.08 |
| combo-opposite010-native-only | +6.07% | 1.08 | 33.83% | 16.27% | 133 | 0.33 | 0.35 |
| combo-opposite010-dynamic-only | +25.76% | 1.32 | 43.45% | 12.23% | 145 | 1.19 | 1.92 |
| combo-opposite010-no-management | +23.59% | 1.35 | 31.73% | 12.90% | 104 | 1.12 | 1.72 |
| combo-opposite010-buffer000 | +44.57% | 1.44 | 44.71% | 9.30% | 170 | 1.96 | 3.80 |
| Opposite edge + 10%, zero breakout buffer, Safe | +20.50% | 1.74 | 50.00% | 6.74% | 54 | 3.90 | 2.59 |
| combo-opposite010-window0812 | +29.64% | 1.34 | 44.52% | 10.43% | 155 | 1.48 | 2.41 |
| Opposite edge + 10%, 08:00–12:00, Safe | +15.43% | 1.57 | 45.10% | 5.53% | 51 | 3.08 | 2.48 |
| combo-opposite003-standard | +26.90% | 1.28 | 43.68% | 9.77% | 174 | 1.32 | 2.43 |
| Opposite edge + 3% buffer, Safe | +18.04% | 1.63 | 50.00% | 5.96% | 56 | 3.35 | 2.61 |

## Interpretation

- Safe mode is essential for this EA in the tested history; disabling it raised trade count but sharply degraded PF and drawdown.
- The apparent development gain from moving the stop to the opposite Asia edge did not persist in the locked year.
- Dynamic 50/20 should remain combined with the EA's native 2R/0.5R trailing behavior because that exact installed combination won the independent validation.
- Results are historical and do not guarantee future performance. The Safe filter is a completed-D1 gate and does not use future bars.

## Artifacts

- Final chart: `ASIA BREAKOUT XAU - FINAL DECISION AND MONTE CARLO.png`
- Development comparison: `ASIA BREAKOUT XAU - DEVELOPMENT CONFIG COMPARISON.png`
- Locked comparison: `ASIA BREAKOUT XAU - LOCKED CONFIG COMPARISON.png`
- Three-year comparison: `ASIA BREAKOUT XAU - THREEYEAR CONFIG COMPARISON.png`
- Monte Carlo data: `monte-carlo-results.csv` and `monte-carlo-results.json`
