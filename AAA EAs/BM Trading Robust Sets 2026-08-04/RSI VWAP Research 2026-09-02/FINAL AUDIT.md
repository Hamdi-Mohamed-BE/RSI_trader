# RSI+VWAP locked last-year audit

Period: 2025-09-01 to 2026-09-01. Native MT5 Every Tick with broker spread, commission, swap and random execution delay.

| Symbol | TF | Baseline return | Optimized return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BTCUSD | H4 | -4.66% | -6.55% | 0.28 | 37.50% | 6.97% | 16 | -5.00 | -0.94 |
| ETHUSD | H4 | -2.15% | -1.29% | 0.68 | 50.00% | 3.28% | 8 | -0.23 | -0.39 |
| XAUUSD | H1 | +0.21% | +4.58% | 1.48 | 72.73% | 3.53% | 44 | 3.47 | 1.25 |
| XAGUSD | H4 | +3.93% | +0.00% | 1.00 | 75.00% | 13.35% | 4 | 0.00 | 0.00 |
| GBPJPY | M30 | -1.33% | -10.97% | 0.64 | 40.38% | 11.90% | 52 | -5.00 | -0.92 |
| US30 | H4 | +1.90% | +0.97% | 440.14 | 100.00% | 0.20% | 2 | 0.06 | 4.71 |
| USTEC | H4 | +1.89% | +1.80% | 2.77 | 50.00% | 1.71% | 2 | 0.10 | 1.01 |

## Selected configuration

| Symbol | Stop / RR | Trailing | Session | Risk |
|---|---|---|---|---:|
| BTCUSD | vwap-rr05 | be075 | all | 1.00% |
| ETHUSD | atr30-rr07 | be075 | asia | 1.00% |
| XAUUSD | swing-rr05 | be075 | all | 1.00% |
| XAGUSD | atr30-rr15 | be075 | newyork | 1.00% |
| GBPJPY | atr20-rr10 | be100 | asia | 1.00% |
| US30 | atr15-rr05 | be075 | asia | 1.00% |
| USTEC | atr30-rr30 | trail10-atr20 | all | 1.00% |

## 10,000-path trade-bootstrap Monte Carlo

| Symbol | Trades | Profit probability | Return P5 | Median return | Return P95 | Median max DD | P95 max DD |
|---|---:|---:|---:|---:|---:|---:|---:|
| BTCUSD | 16 | 0.8% | -10.62% | -6.58% | -2.36% | 7.03% | 10.80% |
| ETHUSD | 8 | 36.9% | -4.71% | -1.29% | +2.12% | 2.69% | 5.40% |
| XAUUSD | 44 | 88.7% | -1.71% | +4.71% | +10.62% | 2.58% | 5.49% |
| XAGUSD | 4 | 56.1% | -4.67% | +0.00% | +4.57% | 2.30% | 4.67% |
| GBPJPY | 52 | 5.5% | -22.03% | -10.99% | +0.12% | 13.50% | 22.97% |
| US30 | 2 | 100.0% | +0.94% | +0.97% | +1.00% | 0.00% | 0.00% |
| USTEC | 2 | 75.0% | -2.04% | +1.80% | +5.64% | 1.02% | 2.04% |
