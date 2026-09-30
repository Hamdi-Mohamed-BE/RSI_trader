# 3 Way Volume Profile: qualification results

Native MT5; M15, $10,000, target risk 1% (lots round up), 2R, 150 ms configured delay.

Model 1 is an OHLC screen; Model 4 can mix real and generated ticks. See journals for coverage.

| Asset / setup | Window | Model | Type | Return | PF | Trades | Win | Equity DD | Absolute gate |
|---|---|---|---|---:|---:|---:|---:|---:|---|
| BTCUSD REV | 3y | 1 | raw | +34.73% | 1.09 | 592 | 35.98% | 29.12% | FAIL |
| BTCUSD REV | 3y | 4 | raw | +34.31% | 1.09 | 592 | 35.98% | 29.28% | FAIL |
| BTCUSD REV | 5y | 1 | raw | +26.22% | 1.05 | 911 | 35.46% | 38.20% | FAIL |
| BTCUSD REV | 5y | 4 | raw | +25.95% | 1.04 | 911 | 35.46% | 38.35% | FAIL |
| USDJPY ALL | 3y | 1 | raw | +111.90% | 1.22 | 562 | 39.15% | 17.71% | PASS |
| USDJPY ALL | 3y | 4 | raw | +84.44% | 1.18 | 554 | 39.17% | 16.53% | PASS |
| USDJPY ALL | 5y | 1 | raw | +130.54% | 1.16 | 921 | 37.68% | 17.73% | PASS |
| USDJPY ALL | 5y | 4 | raw | +99.12% | 1.13 | 913 | 37.68% | 16.47% | FAIL |
| USDJPY BRK | 3y | 1 | raw | +53.53% | 1.24 | 272 | 39.71% | 15.23% | PASS |
| USDJPY BRK | 3y | 4 | raw | +56.12% | 1.24 | 272 | 39.71% | 15.39% | PASS |
| USDJPY BRK | 5y | 1 | raw | +32.44% | 1.10 | 451 | 36.59% | 25.35% | FAIL |
| USDJPY BRK | 5y | 4 | raw | +34.70% | 1.11 | 451 | 36.59% | 25.44% | FAIL |
| XAUUSD BRK | 1y | 4 | raw | +19.82% | 1.30 | 78 | 41.03% | 13.43% | PASS |
| XAUUSD BRK | 3y | 1 | raw | +99.17% | 1.39 | 270 | 42.59% | 11.98% | PASS |
| XAUUSD BRK | 3y | 4 | 101 | -24.50% | 0.87 | 244 | 31.97% | 36.57% | FAIL |
| XAUUSD BRK | 3y | 4 | 202 | -23.93% | 0.87 | 272 | 32.72% | 32.74% | FAIL |
| XAUUSD BRK | 3y | 4 | 303 | +1.10% | 1.01 | 252 | 34.13% | 20.91% | FAIL |
| XAUUSD BRK | 3y | 4 | raw | +93.10% | 1.37 | 270 | 42.59% | 12.02% | PASS |
| XAUUSD BRK | 5y | 1 | raw | +93.96% | 1.26 | 446 | 39.24% | 11.53% | PASS |
| XAUUSD BRK | 5y | 4 | 101 | -31.41% | 0.89 | 411 | 32.36% | 40.62% | FAIL |
| XAUUSD BRK | 5y | 4 | 202 | -42.02% | 0.83 | 437 | 31.58% | 48.46% | FAIL |
| XAUUSD BRK | 5y | 4 | 303 | -20.71% | 0.91 | 401 | 32.92% | 37.32% | FAIL |
| XAUUSD BRK | 5y | 4 | raw | +80.22% | 1.22 | 446 | 39.24% | 12.22% | PASS |

Absolute gate: return > 0, PF >= 1.15, >= 30 trades, no detected history-start shift. Both 3y AND 5y required; a control comparison is also required before qualification.

Optimization has NOT started. No production files or settings changed.
