# Dynamic Trailing SL + Session Filter Audit

The live BAT and website were not changed. All variants were compiled as isolated per-EA research copies.

Dynamic rule: after a completed M15 candle reaches 50% of the original entry-to-target distance (or 0.5R when no TP exists), move SL to lock 20% of that distance. Sessions are UTC: Asia 00:00–08:00, London 07:00–12:00, New York 13:00–21:00, overlap 13:00–16:00.

## Combined arithmetic overlay

| Variant | Return | PF | Win rate | Realized DD | Trades | Commission | Swap |
|---|---:|---:|---:|---:|---:|---:|---:|
| current | +408.91% | 1.42 | 43.01% | 9.09% | 1516 | $-1,114.20 | $-1,049.39 |
| dynamic-only | +376.79% | 1.44 | 51.14% | 7.44% | 1584 | $-1,121.90 | $-779.03 |
| best-session | +238.16% | 1.38 | 42.90% | 8.46% | 1112 | $-881.59 | $-657.87 |
| best-session-dynamic | +228.46% | 1.41 | 50.57% | 10.04% | 1133 | $-884.35 | $-500.43 |

> Combined figures are a chronological arithmetic cash-flow overlay of separate EA tests, not a simultaneous shared-margin MT5 portfolio simulation.

## Per-EA locked results

| EA | Symbol | Best screened session | Variant | Return | PF | Win rate | Max equity DD | Trades |
|---|---|---|---|---:|---:|---:|---:|---:|
| AAA Final Asia Breakout | XAUUSD | overlap | current | +25.76% | 1.65 | 42.42% | 5.87% | 66 |
| AAA Final Asia Breakout | XAUUSD | overlap | dynamic-only | +31.38% | 1.74 | 46.58% | 5.75% | 73 |
| AAA Final Asia Breakout | XAUUSD | overlap | best-session | +32.83% | 2.00 | 47.27% | 7.17% | 55 |
| AAA Final Asia Breakout | XAUUSD | overlap | best-session-dynamic | +30.73% | 1.90 | 49.18% | 6.77% | 61 |
| AAA Final DmC | XAUUSD | london | current | +62.71% | 1.62 | 50.00% | 9.21% | 160 |
| AAA Final DmC | XAUUSD | london | dynamic-only | +48.15% | 1.60 | 57.58% | 5.42% | 165 |
| AAA Final DmC | XAUUSD | london | best-session | +10.43% | 1.50 | 48.72% | 6.15% | 39 |
| AAA Final DmC | XAUUSD | london | best-session-dynamic | +8.22% | 1.52 | 57.50% | 4.69% | 40 |
| AAA Final EMA3 | XAUUSD | london | current | +17.22% | 2.36 | 64.86% | 2.83% | 37 |
| AAA Final EMA3 | XAUUSD | london | dynamic-only | +20.71% | 2.91 | 72.73% | 2.87% | 44 |
| AAA Final EMA3 | XAUUSD | london | best-session | +10.03% | 13.01 | 90.91% | 1.74% | 11 |
| AAA Final EMA3 | XAUUSD | london | best-session-dynamic | +6.39% | 5.20 | 85.71% | 1.79% | 14 |
| Engineered Liquidity BTC | BTCUSD | all | current | +18.80% | 1.19 | 29.13% | 19.62% | 127 |
| Engineered Liquidity BTC | BTCUSD | all | dynamic-only | +12.63% | 1.14 | 35.94% | 16.99% | 128 |
| Engineered Liquidity BTC | BTCUSD | all | best-session | +18.80% | 1.19 | 29.13% | 19.62% | 127 |
| Engineered Liquidity BTC | BTCUSD | all | best-session-dynamic | +12.63% | 1.14 | 35.94% | 16.99% | 128 |
| Engineered Liquidity XAU | XAUUSD | all | current | +21.77% | 1.35 | 33.75% | 13.30% | 80 |
| Engineered Liquidity XAU | XAUUSD | all | dynamic-only | +29.13% | 1.51 | 42.50% | 9.87% | 80 |
| Engineered Liquidity XAU | XAUUSD | all | best-session | +21.77% | 1.35 | 33.75% | 13.30% | 80 |
| Engineered Liquidity XAU | XAUUSD | all | best-session-dynamic | +29.13% | 1.51 | 42.50% | 9.87% | 80 |
| US100 Fabio ORB 1R | USTEC | all | current | +6.35% | 1.14 | 58.13% | 9.07% | 160 |
| US100 Fabio ORB 1R | USTEC | all | dynamic-only | +4.59% | 1.10 | 60.00% | 8.84% | 160 |
| US100 Fabio ORB 1R | USTEC | all | best-session | +6.35% | 1.14 | 58.13% | 9.07% | 160 |
| US100 Fabio ORB 1R | USTEC | all | best-session-dynamic | +4.59% | 1.10 | 60.00% | 8.84% | 160 |
| LTA Volume Profile | XAUUSD | overlap | current | +104.67% | 1.42 | 33.20% | 14.61% | 247 |
| LTA Volume Profile | XAUUSD | overlap | dynamic-only | +72.31% | 1.34 | 40.79% | 16.20% | 277 |
| LTA Volume Profile | XAUUSD | overlap | best-session | +13.15% | 1.15 | 28.32% | 14.31% | 113 |
| LTA Volume Profile | XAUUSD | overlap | best-session-dynamic | +9.08% | 1.12 | 33.62% | 14.01% | 116 |
| XAU Markov Regime | XAUUSD | all | current | +0.00% | 0.00 | 0.00% | 0.00% | 0 |
| XAU Markov Regime | XAUUSD | all | dynamic-only | +0.00% | 0.00 | 0.00% | 0.00% | 0 |
| XAU Markov Regime | XAUUSD | all | best-session | +0.00% | 0.00 | 0.00% | 0.00% | 0 |
| XAU Markov Regime | XAUUSD | all | best-session-dynamic | +0.00% | 0.00 | 0.00% | 0.00% | 0 |
| Nasdaq 5M Candle Momentum | USTEC | all | current | +28.91% | 1.17 | 40.62% | 13.38% | 256 |
| Nasdaq 5M Candle Momentum | USTEC | all | dynamic-only | +28.01% | 1.20 | 54.47% | 12.29% | 257 |
| Nasdaq 5M Candle Momentum | USTEC | all | best-session | +28.91% | 1.17 | 40.62% | 13.38% | 256 |
| Nasdaq 5M Candle Momentum | USTEC | all | best-session-dynamic | +28.01% | 1.20 | 54.47% | 12.29% | 257 |
| News Pulse LONG ONLY | XAUUSD | all | current | +60.58% | 20.61 | 78.95% | 2.47% | 19 |
| News Pulse LONG ONLY | XAUUSD | all | dynamic-only | +62.39% | 40.78 | 84.21% | 1.46% | 19 |
| News Pulse LONG ONLY | XAUUSD | all | best-session | +60.58% | 20.61 | 78.95% | 2.47% | 19 |
| News Pulse LONG ONLY | XAUUSD | all | best-session-dynamic | +62.39% | 40.78 | 84.21% | 1.46% | 19 |
| ORB Volume Profile | XAUUSD | all | current | +12.74% | 1.86 | 44.90% | 6.22% | 49 |
| ORB Volume Profile | XAUUSD | all | dynamic-only | +13.46% | 1.91 | 48.98% | 5.98% | 49 |
| ORB Volume Profile | XAUUSD | all | best-session | +12.74% | 1.86 | 44.90% | 6.22% | 49 |
| ORB Volume Profile | XAUUSD | all | best-session-dynamic | +13.46% | 1.91 | 48.98% | 5.98% | 49 |
| Nasdaq Overnight | USTEC | all | current | +8.44% | 1.80 | 63.89% | 2.36% | 72 |
| Nasdaq Overnight | USTEC | all | dynamic-only | +6.97% | 1.66 | 63.89% | 2.40% | 72 |
| Nasdaq Overnight | USTEC | all | best-session | +8.44% | 1.80 | 63.89% | 2.36% | 72 |
| Nasdaq Overnight | USTEC | all | best-session-dynamic | +6.97% | 1.66 | 63.89% | 2.40% | 72 |
| BTC Top Down FVG Liquidity | BTCUSD | asia | current | +12.74% | 1.92 | 50.00% | 3.84% | 26 |
| BTC Top Down FVG Liquidity | BTCUSD | asia | dynamic-only | +8.95% | 1.70 | 53.85% | 3.60% | 26 |
| BTC Top Down FVG Liquidity | BTCUSD | asia | best-session | +8.83% | 2.65 | 58.33% | 2.46% | 12 |
| BTC Top Down FVG Liquidity | BTCUSD | asia | best-session-dynamic | +5.43% | 2.02 | 58.33% | 3.85% | 12 |
| ETH Top Down FVG Liquidity | ETHUSD | all | current | +10.30% | 1.57 | 38.46% | 6.68% | 26 |
| ETH Top Down FVG Liquidity | ETHUSD | all | dynamic-only | +10.35% | 1.67 | 50.00% | 6.68% | 26 |
| ETH Top Down FVG Liquidity | ETHUSD | all | best-session | +10.30% | 1.57 | 38.46% | 6.68% | 26 |
| ETH Top Down FVG Liquidity | ETHUSD | all | best-session-dynamic | +10.35% | 1.67 | 50.00% | 6.68% | 26 |
| AAA Final XAU Weakness | XAUUSD | asia | current | +17.92% | 1.14 | 37.17% | 11.54% | 191 |
| AAA Final XAU Weakness | XAUUSD | asia | dynamic-only | +27.76% | 1.23 | 51.44% | 9.29% | 208 |
| AAA Final XAU Weakness | XAUUSD | asia | best-session | -5.02% | 0.91 | 31.18% | 12.37% | 93 |
| AAA Final XAU Weakness | XAUUSD | asia | best-session-dynamic | +1.10% | 1.02 | 47.47% | 8.83% | 99 |

## Methodology

- Session choice used 2024-09-01 through 2025-08-31 with M1 OHLC modelling.
- Locked comparison used 2025-09-01 through 2026-08-31 with MT5 Every Tick, random execution delay, broker spread, commission and swap.
- A session needed at least five trades and at least 35% of the all-session trade count to qualify, limiting tiny-sample winners.
- Dynamic trailing only acts on completed M15 candles; short-lived News Pulse positions therefore may be unaffected by design.

## Sharpe, recovery and Monte Carlo

Monte Carlo uses 10,000 five-calendar-day block-bootstrap paths from the locked daily return sequence. This preserves short clusters better than randomly shuffling individual trades, but it still assumes the locked year is representative of the future.

| Variant | Sharpe | Recovery | Profit probability | Return P5 / median / P95 | Median / P95 max DD | P(DD >= 10%) |
|---|---:|---:|---:|---:|---:|---:|
| current | 5.19 | 18.26 | 100.00% | +183.26% / +392.84% / +792.24% | 8.43% / 13.73% | 27.71% |
| dynamic-only | 5.40 | 15.07 | 100.00% | +173.41% / +356.53% / +706.81% | 7.44% / 11.92% | 14.22% |
| best-session | 4.19 | 10.47 | 100.00% | +106.70% / +232.29% / +450.18% | 9.16% / 14.75% | 37.25% |
| best-session-dynamic | 4.26 | 8.88 | 100.00% | +103.15% / +223.69% / +426.15% | 8.61% / 13.81% | 29.69% |

### Per-EA risk metrics

| EA | Variant | Sharpe | Recovery | Profit probability | Return P5 | P95 max DD |
|---|---|---:|---:|---:|---:|---:|
| AAA Final Asia Breakout | current | 1.84 | 3.32 | 96.84% | +2.29% | 11.54% |
| AAA Final Asia Breakout | dynamic-only | 2.25 | 4.30 | 98.49% | +6.50% | 10.73% |
| AAA Final Asia Breakout | best-session | 2.45 | 3.23 | 99.12% | +8.20% | 9.25% |
| AAA Final Asia Breakout | best-session-dynamic | 2.39 | 3.28 | 99.20% | +7.55% | 9.08% |
| AAA Final DmC | current | 3.15 | 3.97 | 99.94% | +28.40% | 11.86% |
| AAA Final DmC | dynamic-only | 2.96 | 5.86 | 99.94% | +20.81% | 10.20% |
| AAA Final DmC | best-session | 1.28 | 1.44 | 93.42% | -0.89% | 8.27% |
| AAA Final DmC | best-session-dynamic | 1.21 | 1.54 | 92.42% | -1.19% | 6.96% |
| AAA Final EMA3 | current | 2.50 | 5.24 | 99.75% | +6.59% | 4.74% |
| AAA Final EMA3 | dynamic-only | 3.09 | 5.96 | 99.95% | +9.18% | 4.05% |
| AAA Final EMA3 | best-session | 2.86 | 5.50 | 99.95% | +3.85% | 1.59% |
| AAA Final EMA3 | best-session-dynamic | 2.30 | 3.44 | 99.35% | +1.70% | 1.76% |
| Engineered Liquidity BTC | current | 0.91 | 0.79 | 80.80% | -12.57% | 24.02% |
| Engineered Liquidity BTC | dynamic-only | 0.69 | 0.61 | 73.77% | -14.61% | 23.37% |
| Engineered Liquidity BTC | best-session | 0.91 | 0.79 | 80.19% | -13.45% | 24.48% |
| Engineered Liquidity BTC | best-session-dynamic | 0.69 | 0.61 | 74.43% | -14.65% | 23.51% |
| Engineered Liquidity XAU | current | 1.11 | 1.23 | 86.55% | -8.33% | 19.95% |
| Engineered Liquidity XAU | dynamic-only | 1.45 | 2.27 | 93.42% | -2.08% | 17.03% |
| Engineered Liquidity XAU | best-session | 1.11 | 1.23 | 86.13% | -8.48% | 20.14% |
| Engineered Liquidity XAU | best-session-dynamic | 1.45 | 2.27 | 92.92% | -2.58% | 16.97% |
| US100 Fabio ORB 1R | current | 0.75 | 0.60 | 75.09% | -9.31% | 15.67% |
| US100 Fabio ORB 1R | dynamic-only | 0.57 | 0.45 | 70.70% | -10.21% | 16.10% |
| US100 Fabio ORB 1R | best-session | 0.75 | 0.60 | 76.12% | -8.98% | 15.42% |
| US100 Fabio ORB 1R | best-session-dynamic | 0.57 | 0.45 | 70.11% | -10.29% | 16.13% |
| LTA Volume Profile | current | 2.74 | 4.80 | 99.63% | +30.33% | 20.06% |
| LTA Volume Profile | dynamic-only | 2.31 | 3.24 | 98.55% | +12.75% | 20.89% |
| LTA Volume Profile | best-session | 0.79 | 0.72 | 74.09% | -14.68% | 23.33% |
| LTA Volume Profile | best-session-dynamic | 0.62 | 0.57 | 68.62% | -15.28% | 22.28% |
| XAU Markov Regime | current | 0.00 | 0.00 | 0.00% | +0.00% | 0.00% |
| XAU Markov Regime | dynamic-only | 0.00 | 0.00 | 0.00% | +0.00% | 0.00% |
| XAU Markov Regime | best-session | 0.00 | 0.00 | 0.00% | +0.00% | 0.00% |
| XAU Markov Regime | best-session-dynamic | 0.00 | 0.00 | 0.00% | +0.00% | 0.00% |
| Nasdaq 5M Candle Momentum | current | 1.17 | 1.49 | 88.45% | -10.13% | 28.75% |
| Nasdaq 5M Candle Momentum | dynamic-only | 1.23 | 1.62 | 90.40% | -7.07% | 24.95% |
| Nasdaq 5M Candle Momentum | best-session | 1.17 | 1.49 | 88.26% | -11.15% | 28.69% |
| Nasdaq 5M Candle Momentum | best-session-dynamic | 1.23 | 1.62 | 90.36% | -7.95% | 24.99% |
| News Pulse LONG ONLY | current | 3.04 | 14.89 | 100.00% | +28.51% | 2.03% |
| News Pulse LONG ONLY | dynamic-only | 3.11 | 27.64 | 100.00% | +29.58% | 2.03% |
| News Pulse LONG ONLY | best-session | 3.04 | 14.89 | 100.00% | +28.40% | 2.03% |
| News Pulse LONG ONLY | best-session-dynamic | 3.11 | 27.64 | 100.00% | +29.45% | 2.03% |
| ORB Volume Profile | current | 1.52 | 1.98 | 91.82% | -2.15% | 8.46% |
| ORB Volume Profile | dynamic-only | 1.60 | 2.18 | 93.40% | -1.02% | 7.73% |
| ORB Volume Profile | best-session | 1.52 | 1.98 | 92.03% | -1.64% | 8.26% |
| ORB Volume Profile | best-session-dynamic | 1.60 | 2.18 | 93.45% | -0.88% | 7.68% |
| Nasdaq Overnight | current | 2.06 | 3.28 | 99.23% | +2.60% | 3.56% |
| Nasdaq Overnight | dynamic-only | 1.78 | 2.67 | 97.86% | +1.40% | 3.76% |
| Nasdaq Overnight | best-session | 2.06 | 3.28 | 98.95% | +2.53% | 3.53% |
| Nasdaq Overnight | best-session-dynamic | 1.78 | 2.67 | 98.15% | +1.43% | 3.75% |
| BTC Top Down FVG Liquidity | current | 1.60 | 3.15 | 92.13% | -1.97% | 8.73% |
| BTC Top Down FVG Liquidity | dynamic-only | 1.27 | 2.37 | 84.63% | -4.00% | 8.77% |
| BTC Top Down FVG Liquidity | best-session | 1.58 | 3.41 | 90.30% | -1.34% | 5.00% |
| BTC Top Down FVG Liquidity | best-session-dynamic | 1.13 | 1.34 | 78.73% | -3.39% | 5.90% |
| ETH Top Down FVG Liquidity | current | 1.09 | 1.50 | 89.13% | -3.31% | 9.54% |
| ETH Top Down FVG Liquidity | dynamic-only | 1.19 | 1.47 | 91.40% | -2.12% | 8.30% |
| ETH Top Down FVG Liquidity | best-session | 1.09 | 1.50 | 89.19% | -3.05% | 9.56% |
| ETH Top Down FVG Liquidity | best-session-dynamic | 1.19 | 1.47 | 91.59% | -1.99% | 8.15% |
| AAA Final XAU Weakness | current | 0.93 | 1.16 | 85.24% | -10.43% | 23.87% |
| AAA Final XAU Weakness | dynamic-only | 1.50 | 2.15 | 95.36% | +0.55% | 17.55% |
| AAA Final XAU Weakness | best-session | -0.37 | -0.39 | 33.27% | -21.09% | 24.73% |
| AAA Final XAU Weakness | best-session-dynamic | 0.15 | 0.12 | 53.11% | -14.07% | 18.25% |

The current portfolio has the stronger absolute return and recovery factor. Dynamic-only has a slightly higher Sharpe ratio, a lower observed drawdown and a better simulated drawdown tail, but gives up headline return. Session filtering is not recommended portfolio-wide because it materially reduces return and does not improve the Monte Carlo tail enough to compensate. The evidence supports applying dynamic trailing selectively per EA rather than forcing it on every EA.
