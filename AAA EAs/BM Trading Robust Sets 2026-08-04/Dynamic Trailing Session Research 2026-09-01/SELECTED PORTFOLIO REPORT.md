# Applied 12-EA portfolio audit — 2026-09-01

The BAT portfolio now uses the individually selected exit mode for each retained EA. All new session filters are disabled. Engineered Liquidity BTC, US100 Fabio ORB 1R and the standalone XAU Markov Regime EA were removed.

## Locked one-year portfolio comparison

| Portfolio | Return | PF | Win rate | Max realized DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| Applied per-EA selections | +397.20% | 1.53 | 50.24% | 7.31% | 1266 | 5.45 | 15.50 |
| Same 12 EAs, all current exits | +383.77% | 1.46 | 42.47% | 7.93% | 1229 | 5.05 | 23.15 |

## Monte Carlo — applied selections

10,000 five-calendar-day block-bootstrap paths, using the locked portfolio daily return sequence from 2025-09-01 through 2026-08-31.

| Metric | Result |
|---|---:|
| Probability of profit | 100.00% |
| Probability of loss | 0.00% |
| Return P5 / median / P95 | +188.20% / +378.91% / +733.71% |
| Mean simulated return | +410.20% |
| Median / P95 maximum DD | 7.10% / 11.48% |
| Probability DD >= 10% | 11.55% |
| Probability DD >= 20% | 0.03% |
| Simulated ruin | 0.00% |

## Applied per-EA setups

| EA | Symbol / TF | Exit setup | Return | PF | Win rate | DD | Trades | Recovery | vs current return |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| AAA Final Asia Breakout | XAUUSD H1 | dynamic 50/20 | +31.38% | 1.74 | 46.58% | 5.75% | 73 | 4.30 | +5.62 pp |
| AAA Final DmC | XAUUSD H1 | dynamic 50/20 | +48.15% | 1.60 | 57.58% | 5.42% | 165 | 5.86 | -14.55 pp |
| AAA Final EMA3 | XAUUSD H4 | dynamic 50/20 | +20.71% | 2.91 | 72.73% | 2.87% | 44 | 5.96 | +3.50 pp |
| AAA Final XAU Weakness | XAUUSD M15 | dynamic 50/20 | +27.76% | 1.23 | 51.44% | 9.29% | 208 | 2.15 | +9.84 pp |
| BTC Top Down FVG Liquidity | BTCUSD M15 | current exit | +12.74% | 1.92 | 50.00% | 3.84% | 26 | 3.15 | +0.00 pp |
| ETH Top Down FVG Liquidity | ETHUSD M15 | dynamic 50/20 | +10.35% | 1.67 | 50.00% | 6.68% | 26 | 1.47 | +0.04 pp |
| Engineered Liquidity XAU | XAUUSD H1 | dynamic 50/20 | +29.13% | 1.51 | 42.50% | 9.87% | 80 | 2.27 | +7.35 pp |
| LTA Volume Profile | XAUUSD M15 | current exit | +104.67% | 1.42 | 33.20% | 14.61% | 247 | 4.80 | +0.00 pp |
| Nasdaq 5M Candle Momentum | USTEC M5 | dynamic 50/20 | +28.01% | 1.20 | 54.47% | 12.29% | 257 | 1.62 | -0.90 pp |
| Nasdaq Overnight | USTEC M1 | current exit | +8.44% | 1.80 | 63.89% | 2.36% | 72 | 3.28 | +0.00 pp |
| News Pulse LONG ONLY | XAUUSD M1 | dynamic 50/20 | +62.39% | 40.78 | 84.21% | 1.46% | 19 | 27.64 | +1.81 pp |
| ORB Volume Profile | XAUUSD M5 | dynamic 50/20 | +13.46% | 1.91 | 48.98% | 5.98% | 49 | 2.18 | +0.71 pp |

## Important limitation

This is a chronological arithmetic cash-flow overlay of separate, locked MT5 every-tick EA tests. It preserves the observed timing of closed-trade balance changes, costs and short return clusters, but it is not a simultaneous shared-margin MT5 portfolio test. Monte Carlo measures sequence uncertainty from this one locked year; it cannot prove future profitability or capture future spread, slippage, correlation or regime changes.
