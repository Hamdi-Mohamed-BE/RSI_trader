# News Pulse — deployed hard 1.50% total-risk audit

The EA watches NFP, CPI, and FOMC statements/rate decisions. Both pending directions are enabled. The compiled v2.12 source hard-locks 0.75% risk per stop, for at most 1.50% planned event exposure.

| Market | Entry / stop | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery | Random-delay return / PF | MC P5 return | MC P95 DD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| XAUUSD | 6 / 6 | +55.04% | 9.00 | 63.64% | 1.79% | 33 | 389.89 | 20.69 | +57.53% / 9.43 | +30.35% | 3.14% |
| XAGUSD | 0.08 / 0.08 | +221.04% | 13.46 | 62.16% | 2.52% | 37 | 431.23 | 30.11 | +216.93% / 11.35 | +127.73% | 4.81% |
| EURUSD | 0.0006 / 0.0006 | +50.46% | 7.81 | 67.65% | 2.85% | 34 | 455.24 | 13.93 | +50.71% / 7.59 | +28.86% | 3.11% |

MT5 Sharpe is shown for completeness but is mechanically inflated by sparse positions held for roughly one minute. News gaps, spread expansion, slippage and order rejection can exceed the planned 1.50% exposure.
