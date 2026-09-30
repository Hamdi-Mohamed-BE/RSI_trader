# Strict no-wick retest — native results

Completed 72/72 planned runs. Smoke run reported separately, not in the screen.

Frozen raw rules; no optimization. Each asset/timeframe is tested separately: $10,000, 1% equity target risk, lots rounded UP, fixed 1:1. These are not combined-portfolio results. All P/L, win rates and PF below are NET of recorded commission and swap; native bid/ask spread is already in fill prices. Native return and max relative equity DD; broker: Exness-MT5Trial16. Cutoff 2026-09-30 exclusive.

US100 = USTEC CFD, not NQ futures. “No wick” and swing rules differ from the September-25 related test. Timeframes for gold/BTC were both declared before testing; do not treat the best retrospectively as validated.

No position time exit: some trades can last overnight/weekends. Pending expiry is 20 wall-clock timeframe durations. BTC frequency uses calendar days; others use weekdays. Overlapping windows are not independent tests.

## Conclusion

- 0/12 versions passed the frozen raw screen.
- One-year net win rates range from 40.2% to 51.9%, not approximately 90%.
- Highest one-year net PF: USTEC M5 at 0.99, return -2.94%. This is a retrospective comparison, not a validated selection.
- No optimization or live deployment was performed.

## 6m

| Asset / TF | Return | Net PF | Net win | Eq DD | Trades | /month | /day | Avg W/L streak | Max W/L streak |
|---|---|---|---|---|---|---|---|---|---|
| XAUUSD M5 | -38.82% | 0.78 | 47.0% | 50.11% | 364 | 60.21 | 2.76 | 1.8 / 2.1 | 8 / 8 |
| XAUUSD M15 | +0.37% | 1.01 | 51.4% | 6.94% | 74 | 12.24 | 0.56 | 2.4 / 2.2 | 6 / 6 |
| BTCUSD M5 | -49.52% | 0.88 | 49.6% | 52.49% | 1022 | 169.06 | 5.55 | 2.0 / 2.0 | 11 / 10 |
| BTCUSD M15 | +3.55% | 1.03 | 52.7% | 13.00% | 260 | 43.01 | 1.41 | 2.3 / 2.1 | 10 / 6 |
| USTEC M5 | +26.44% | 1.10 | 54.1% | 13.46% | 451 | 74.60 | 3.42 | 2.2 / 1.8 | 8 / 8 |
| EURUSD M15 | -24.38% | 0.79 | 50.9% | 32.38% | 234 | 38.71 | 1.77 | 2.0 / 1.9 | 8 / 7 |
| GBPUSD M15 | -22.29% | 0.76 | 47.0% | 23.95% | 185 | 30.60 | 1.40 | 1.9 / 2.1 | 7 / 7 |
| USDJPY M15 | -51.76% | 0.51 | 41.6% | 52.46% | 197 | 32.59 | 1.49 | 1.5 / 2.1 | 5 / 7 |
| USDCHF M15 | -60.36% | 0.52 | 42.1% | 63.36% | 280 | 46.32 | 2.12 | 1.7 / 2.3 | 4 / 7 |
| USDCAD M15 | -23.39% | 0.82 | 53.5% | 29.58% | 241 | 39.87 | 1.83 | 2.0 / 1.8 | 8 / 10 |
| AUDUSD M15 | -29.05% | 0.76 | 49.4% | 38.19% | 267 | 44.17 | 2.02 | 2.0 / 2.0 | 9 / 8 |
| NZDUSD M15 | -77.62% | 0.36 | 36.5% | 78.11% | 277 | 45.82 | 2.10 | 1.7 / 3.0 | 5 / 11 |

## 1y

| Asset / TF | Return | Net PF | Net win | Eq DD | Trades | /month | /day | Avg W/L streak | Max W/L streak |
|---|---|---|---|---|---|---|---|---|---|
| XAUUSD M5 | -62.36% | 0.80 | 46.7% | 68.43% | 792 | 66.05 | 3.03 | 2.0 / 2.3 | 8 / 8 |
| XAUUSD M15 | -31.94% | 0.69 | 43.3% | 34.05% | 187 | 15.59 | 0.72 | 1.8 / 2.4 | 6 / 6 |
| BTCUSD M5 | -81.73% | 0.86 | 48.6% | 83.19% | 2152 | 179.46 | 5.90 | 2.0 / 2.1 | 11 / 10 |
| BTCUSD M15 | -35.54% | 0.85 | 47.9% | 44.02% | 551 | 45.95 | 1.51 | 2.0 / 2.2 | 10 / 8 |
| USTEC M5 | -2.94% | 0.99 | 51.9% | 37.54% | 915 | 76.30 | 3.51 | 2.1 / 2.0 | 8 / 8 |
| EURUSD M15 | -51.79% | 0.72 | 48.6% | 58.01% | 436 | 36.36 | 1.67 | 2.0 / 2.1 | 8 / 7 |
| GBPUSD M15 | -47.23% | 0.70 | 45.4% | 48.02% | 357 | 29.77 | 1.37 | 1.8 / 2.1 | 7 / 7 |
| USDJPY M15 | -71.04% | 0.59 | 41.7% | 72.31% | 403 | 33.61 | 1.54 | 1.7 / 2.4 | 5 / 8 |
| USDCHF M15 | -82.77% | 0.53 | 43.2% | 84.03% | 539 | 44.95 | 2.07 | 1.8 / 2.4 | 8 / 10 |
| USDCAD M15 | -55.62% | 0.70 | 49.9% | 57.86% | 481 | 40.11 | 1.84 | 1.9 / 1.9 | 8 / 10 |
| AUDUSD M15 | -72.91% | 0.53 | 46.3% | 76.01% | 475 | 39.61 | 1.82 | 2.0 / 2.3 | 9 / 10 |
| NZDUSD M15 | -88.46% | 0.50 | 40.2% | 88.64% | 497 | 41.45 | 1.90 | 1.8 / 2.7 | 6 / 11 |

## 3y

| Asset / TF | Return | Net PF | Net win | Eq DD | Trades | /month | /day | Avg W/L streak | Max W/L streak |
|---|---|---|---|---|---|---|---|---|---|
| XAUUSD M5 | -100.00% | 0.55 | 40.4% | 100.00% | 1341 | 37.24 | 1.71 | 1.7 / 2.5 | 6 / 20 |
| XAUUSD M15 | -74.54% | 0.69 | 43.9% | 77.43% | 717 | 19.91 | 0.92 | 1.7 / 2.2 | 8 / 10 |
| BTCUSD M5 | -100.02% | 0.41 | 38.5% | 100.02% | 1517 | 42.13 | 1.38 | 1.6 / 2.6 | 8 / 19 |
| BTCUSD M15 | -59.50% | 0.85 | 48.8% | 64.17% | 1142 | 31.71 | 1.04 | 2.0 / 2.1 | 10 / 10 |
| USTEC M5 | -100.00% | 0.31 | 31.9% | 100.00% | 1073 | 29.80 | 1.37 | 1.5 / 3.2 | 7 / 26 |
| EURUSD M15 | -97.86% | 0.52 | 41.6% | 98.23% | 1174 | 32.60 | 1.50 | 1.7 / 2.4 | 8 / 13 |
| GBPUSD M15 | -96.15% | 0.46 | 41.4% | 96.29% | 1075 | 29.85 | 1.37 | 1.7 / 2.4 | 7 / 12 |
| USDJPY M15 | -98.74% | 0.48 | 41.0% | 98.77% | 1170 | 32.49 | 1.50 | 1.7 / 2.4 | 9 / 13 |
| USDCHF M15 | -100.00% | 0.52 | 41.4% | 100.00% | 1468 | 40.77 | 1.88 | 1.8 / 2.5 | 8 / 14 |
| USDCAD M15 | -99.61% | 0.41 | 41.3% | 99.67% | 1423 | 39.52 | 1.82 | 1.7 / 2.4 | 8 / 18 |
| AUDUSD M15 | -99.43% | 0.51 | 42.0% | 99.56% | 1394 | 38.71 | 1.78 | 1.7 / 2.4 | 9 / 11 |
| NZDUSD M15 | -100.01% | 0.36 | 31.0% | 100.01% | 812 | 22.55 | 1.04 | 1.5 / 3.3 | 6 / 15 |

## 5y

| Asset / TF | Return | Net PF | Net win | Eq DD | Trades | /month | /day | Avg W/L streak | Max W/L streak |
|---|---|---|---|---|---|---|---|---|---|
| XAUUSD M5 | -100.01% | 0.55 | 40.5% | 100.01% | 1609 | 26.82 | 1.23 | 1.7 / 2.5 | 6 / 12 |
| XAUUSD M15 | -96.16% | 0.70 | 43.8% | 98.15% | 1382 | 23.04 | 1.06 | 1.8 / 2.2 | 8 / 10 |
| BTCUSD M5 | -100.00% | 0.41 | 35.3% | 100.00% | 1235 | 20.59 | 0.68 | 1.5 / 2.8 | 5 / 14 |
| BTCUSD M15 | -98.37% | 0.53 | 44.4% | 98.74% | 1719 | 28.65 | 0.94 | 1.9 / 2.3 | 10 / 12 |
| USTEC M5 | -100.00% | 0.41 | 36.4% | 100.00% | 1553 | 25.89 | 1.19 | 1.6 / 2.8 | 7 / 17 |
| EURUSD M15 | -100.01% | 0.52 | 39.0% | 100.01% | 1470 | 24.50 | 1.13 | 1.7 / 2.7 | 11 / 13 |
| GBPUSD M15 | -99.99% | 0.62 | 42.2% | 99.99% | 1879 | 31.32 | 1.44 | 1.7 / 2.4 | 8 / 12 |
| USDJPY M15 | -100.00% | 0.59 | 41.3% | 100.00% | 1630 | 27.17 | 1.25 | 1.8 / 2.5 | 9 / 14 |
| USDCHF M15 | -100.01% | 0.36 | 37.7% | 100.01% | 1225 | 20.42 | 0.94 | 1.6 / 2.7 | 8 / 11 |
| USDCAD M15 | -100.00% | 0.56 | 38.1% | 100.00% | 1421 | 23.69 | 1.09 | 1.7 / 2.7 | 13 / 18 |
| AUDUSD M15 | -100.00% | 0.39 | 36.9% | 100.00% | 1178 | 19.64 | 0.90 | 1.5 / 2.6 | 5 / 12 |
| NZDUSD M15 | -102.99% | 0.37 | 37.1% | 102.84% | 607 | 10.12 | 0.47 | 1.6 / 2.7 | 5 / 14 |

## Frozen raw screen

| Asset / TF | Result | Reason |
|---|---|---|
| XAUUSD M5 | FAIL | 3y net loss; 3y net PF below 1.15; 3y not better than control return; 5y net loss; 5y net PF below 1.15; 5y not better than control return |
| XAUUSD M15 | FAIL | 3y net loss; 3y net PF below 1.15; 5y net loss; 5y net PF below 1.15 |
| BTCUSD M5 | FAIL | 3y net loss; 3y net PF below 1.15; 3y not better than control return; 5y net loss; 5y net PF below 1.15; 5y not better than control return |
| BTCUSD M15 | FAIL | 3y net loss; 3y net PF below 1.15; 5y net loss; 5y net PF below 1.15 |
| USTEC M5 | FAIL | 3y net loss; 3y net PF below 1.15; 3y not better than control return; 5y net loss; 5y net PF below 1.15; 5y not better than control return |
| EURUSD M15 | FAIL | 3y net loss; 3y net PF below 1.15; 5y net loss; 5y net PF below 1.15; 5y not better than control return |
| GBPUSD M15 | FAIL | 3y net loss; 3y net PF below 1.15; 5y net loss; 5y net PF below 1.15 |
| USDJPY M15 | FAIL | 3y net loss; 3y net PF below 1.15; 5y net loss; 5y net PF below 1.15; 5y not better than control return |
| USDCHF M15 | FAIL | 3y net loss; 3y net PF below 1.15; 5y net loss; 5y net PF below 1.15 |
| USDCAD M15 | FAIL | 3y net loss; 3y net PF below 1.15; 5y net loss; 5y net PF below 1.15; 5y not better than control return |
| AUDUSD M15 | FAIL | 3y net loss; 3y net PF below 1.15; 5y net loss; 5y net PF below 1.15 |
| NZDUSD M15 | FAIL | 3y net loss; 3y net PF below 1.15; 3y not better than control return; 5y net loss; 5y net PF below 1.15; 5y not better than control return |

## Any-candle controls

| Any-candle control | Period | Return | Net PF | Net win | Eq DD | Trades | /month | /day | Max W/L |
|---|---|---|---|---|---|---|---|---|---|
| XAUUSD M5 | 3y | -100.00% | 0.49 | 39.8% | 100.00% | 1130 | 31.38 | 1.45 | 8/9 |
| XAUUSD M5 | 5y | -100.00% | 0.33 | 36.5% | 100.00% | 863 | 14.39 | 0.66 | 7/14 |
| XAUUSD M15 | 3y | -100.02% | 0.68 | 44.6% | 100.01% | 1866 | 51.82 | 2.39 | 13/11 |
| XAUUSD M15 | 5y | -100.01% | 0.59 | 42.4% | 100.01% | 1565 | 26.09 | 1.20 | 7/10 |
| BTCUSD M5 | 3y | -99.99% | 0.33 | 34.6% | 99.99% | 959 | 26.63 | 0.88 | 5/13 |
| BTCUSD M5 | 5y | -100.00% | 0.32 | 30.4% | 100.00% | 777 | 12.95 | 0.43 | 4/16 |
| BTCUSD M15 | 3y | -99.99% | 0.54 | 39.9% | 99.99% | 1662 | 46.16 | 1.52 | 8/12 |
| BTCUSD M15 | 5y | -100.00% | 0.54 | 40.3% | 100.00% | 1679 | 27.99 | 0.92 | 9/13 |
| USTEC M5 | 3y | -99.99% | 0.25 | 28.3% | 99.99% | 769 | 21.36 | 0.98 | 8/16 |
| USTEC M5 | 5y | -99.99% | 0.37 | 36.4% | 99.99% | 1330 | 22.17 | 1.02 | 6/15 |
| EURUSD M15 | 3y | -100.00% | 0.35 | 32.7% | 100.00% | 895 | 24.86 | 1.14 | 7/11 |
| EURUSD M15 | 5y | -100.00% | 0.55 | 41.8% | 100.00% | 1882 | 31.37 | 1.44 | 12/16 |
| GBPUSD M15 | 3y | -100.00% | 0.43 | 38.2% | 100.00% | 1399 | 38.85 | 1.79 | 7/21 |
| GBPUSD M15 | 5y | -100.04% | 0.50 | 43.6% | 100.04% | 1559 | 25.99 | 1.20 | 8/11 |
| USDJPY M15 | 3y | -100.00% | 0.50 | 41.9% | 100.00% | 1631 | 45.30 | 2.09 | 8/12 |
| USDJPY M15 | 5y | -100.00% | 0.45 | 40.6% | 100.00% | 1528 | 25.47 | 1.17 | 6/15 |
| USDCHF M15 | 3y | -100.00% | 0.38 | 34.4% | 100.00% | 974 | 27.05 | 1.25 | 8/14 |
| USDCHF M15 | 5y | -100.01% | 0.23 | 33.4% | 100.02% | 817 | 13.62 | 0.63 | 8/18 |
| USDCAD M15 | 3y | -100.00% | 0.46 | 33.3% | 100.00% | 908 | 25.22 | 1.16 | 8/19 |
| USDCAD M15 | 5y | -100.00% | 0.43 | 41.1% | 100.00% | 1346 | 22.44 | 1.03 | 10/14 |
| AUDUSD M15 | 3y | -100.00% | 0.46 | 34.6% | 100.00% | 1077 | 29.91 | 1.38 | 8/26 |
| AUDUSD M15 | 5y | -100.00% | 0.34 | 36.6% | 100.00% | 931 | 15.52 | 0.71 | 8/12 |
| NZDUSD M15 | 3y | -100.00% | 0.34 | 30.2% | 100.00% | 699 | 19.41 | 0.89 | 9/33 |
| NZDUSD M15 | 5y | -100.00% | 0.29 | 37.8% | 100.00% | 982 | 16.37 | 0.75 | 10/12 |

## Data and execution diagnostics

| Run | Period | Reported quality | Real-tick start note | Commission $ | Swap $ | Max hold hours | Rejection log lines | Unique placement logs | Last closed trade | Balance exhausted |
|---|---|---|---|---|---|---|---|---|---|---|
| AUDUSD C15 | 3y | 24% real ticks | real ticks begin from 2026.01.01 00:00:00 | -2586.57 | -35.91 | 170.9 | 914 | 1319 | 2024-08-15T12:30:42 | YES |
| AUDUSD C15 | 5y | 14% real ticks | real ticks begin from 2026.01.01 00:00:00 | -2540.01 | -9.38 | 123.1 | 1656 | 1176 | 2022-07-15T02:00:00 | YES |
| AUDUSD S15 | 1y | 74% real ticks | real ticks begin from 2026.01.01 00:00:00 | -2320.20 | -53.23 | 265.9 | 1484 | 591 | 2026-09-29T23:59:58 | no |
| AUDUSD S15 | 3y | 24% real ticks | real ticks begin from 2026.01.01 00:00:00 | -2742.00 | -56.35 | 603.5 | 2094 | 1791 | 2026-09-29T23:59:58 | no |
| AUDUSD S15 | 5y | 14% real ticks | real ticks begin from 2026.01.01 00:00:00 | -2171.28 | -18.15 | 138.7 | 612 | 1544 | 2024-04-18T16:45:00 | YES |
| AUDUSD S15 | 6m | 100% real ticks | real ticks begin from 2026.01.01 00:00:00 | -2236.32 | -75.89 | 265.9 | 8 | 326 | 2026-09-29T23:59:58 | no |
| BTCUSD C15 | 3y | 24% real ticks | real ticks begin from 2026.01.01 00:00:00 | -2935.24 | -108.89 | 217.9 | 176 | 10182 | 2024-10-13T10:45:40 | no |
| BTCUSD C15 | 5y | 14% real ticks | real ticks begin from 2026.01.01 00:00:00 | -1163.91 | -37.23 | 233.3 | 176 | 18611 | 2022-09-16T11:39:19 | no |
| BTCUSD C5 | 3y | 24% real ticks | real ticks begin from 2026.01.01 00:00:00 | -4221.48 | -40.96 | 47.5 | 914 | 34491 | 2023-12-06T05:38:04 | no |
| BTCUSD C5 | 5y | 14% real ticks | real ticks begin from 2026.01.01 00:00:00 | -1164.48 | -32.34 | 33.2 | 2 | 952 | 2021-11-23T01:10:00 | YES |
| BTCUSD S15 | 1y | 74% real ticks | real ticks begin from 2026.01.01 00:00:00 | -1654.82 | -125.48 | 101.4 | 8 | 706 | 2026-09-29T21:16:45 | no |
| BTCUSD S15 | 3y | 24% real ticks | real ticks begin from 2026.01.01 00:00:00 | -2840.90 | -241.92 | 216.5 | 8 | 1454 | 2026-09-29T21:16:45 | no |
| BTCUSD S15 | 5y | 14% real ticks | real ticks begin from 2026.01.01 00:00:00 | -1832.76 | -155.25 | 243.7 | 8 | 2216 | 2026-09-29T21:16:45 | no |
| BTCUSD S15 | 6m | 100% real ticks | real ticks begin from 2026.01.01 00:00:00 | -1385.21 | -145.47 | 101.4 | 8 | 329 | 2026-09-29T21:16:45 | no |
| BTCUSD S5 | 1y | 74% real ticks | real ticks begin from 2026.01.01 00:00:00 | -6038.07 | -120.19 | 74.2 | 14 | 2717 | 2026-09-29T22:13:18 | no |
| BTCUSD S5 | 3y | 24% real ticks | real ticks begin from 2026.01.01 00:00:00 | -3062.85 | -97.80 | 219.9 | 2 | 1969 | 2024-11-12T20:00:00 | YES |
| BTCUSD S5 | 5y | 14% real ticks | real ticks begin from 2026.01.01 00:00:00 | -1124.91 | -25.09 | 814.1 | 2 | 1607 | 2022-09-30T19:52:39 | YES |
| BTCUSD S5 | 6m | 100% real ticks | real ticks begin from 2026.01.01 00:00:00 | -6037.72 | -116.85 | 44.5 | 8 | 1282 | 2026-09-29T22:13:18 | no |
| EURUSD C15 | 3y | 24% real ticks | real ticks begin from 2026.01.01 00:00:00 | -2305.43 | -75.29 | 899.6 | 2 | 1111 | 2024-08-23T12:12:38 | YES |
| EURUSD C15 | 5y | 14% real ticks | real ticks begin from 2026.01.01 00:00:00 | -3079.91 | -132.06 | 285.0 | 3656 | 3224 | 2023-10-03T08:15:00 | YES |
| EURUSD S15 | 1y | 74% real ticks | real ticks begin from 2026.01.01 00:00:00 | -2847.90 | -200.83 | 116.0 | 2 | 545 | 2026-09-29T23:59:58 | no |
| EURUSD S15 | 3y | 24% real ticks | real ticks begin from 2026.01.01 00:00:00 | -2648.10 | -248.90 | 1004.6 | 4 | 1516 | 2026-09-29T23:59:58 | no |
| EURUSD S15 | 5y | 14% real ticks | real ticks begin from 2026.01.01 00:00:00 | -2368.51 | -139.57 | 1004.6 | 3136 | 1873 | 2024-11-24T22:05:00 | YES |
| EURUSD S15 | 6m | 100% real ticks | real ticks begin from 2026.01.01 00:00:00 | -1839.82 | -213.58 | 83.3 | 2 | 280 | 2026-09-29T23:59:58 | no |
| GBPUSD C15 | 3y | 24% real ticks | real ticks begin from 2026.01.01 00:00:00 | -2129.51 | -32.77 | 277.4 | 17016 | 6450 | 2025-02-10T11:05:27 | no |
| GBPUSD C15 | 5y | 14% real ticks | real ticks begin from 2026.01.01 00:00:00 | -2896.40 | -33.56 | 379.4 | 900 | 1871 | 2023-01-06T13:30:42 | YES |
| GBPUSD S15 | 1y | 74% real ticks | real ticks begin from 2026.01.01 00:00:00 | -1979.01 | -50.96 | 137.9 | 10 | 448 | 2026-09-29T23:59:58 | no |
| GBPUSD S15 | 3y | 24% real ticks | real ticks begin from 2026.01.01 00:00:00 | -1755.11 | -65.60 | 253.1 | 16 | 1371 | 2026-09-29T23:59:58 | no |
| GBPUSD S15 | 5y | 14% real ticks | real ticks begin from 2026.01.01 00:00:00 | -2940.58 | -75.44 | 308.2 | 3174 | 2487 | 2026-07-29T03:21:22 | no |
| GBPUSD S15 | 6m | 100% real ticks | real ticks begin from 2026.01.01 00:00:00 | -1323.74 | -48.90 | 137.9 | 2 | 228 | 2026-09-29T23:59:58 | no |
| NZDUSD C15 | 3y | 24% real ticks | real ticks begin from 2026.01.01 00:00:00 | -2778.34 | -18.68 | 156.9 | 5460 | 7104 | 2024-05-24T01:40:00 | no |
| NZDUSD C15 | 5y | 14% real ticks | real ticks begin from 2026.01.01 00:00:00 | -2635.78 | -22.36 | 187.8 | 3060 | 1200 | 2022-07-13T23:15:00 | YES |
| NZDUSD S15 | 1y | 74% real ticks | real ticks begin from 2026.01.01 00:00:00 | -3409.05 | -121.24 | 154.5 | 1192 | 631 | 2026-09-29T23:59:53 | no |
| NZDUSD S15 | 3y | 24% real ticks | real ticks begin from 2026.01.01 00:00:00 | -2609.03 | -27.68 | 337.1 | 16 | 1097 | 2025-06-13T00:15:00 | YES |
| NZDUSD S15 | 5y | 14% real ticks | real ticks begin from 2026.01.01 00:00:00 | -2481.46 | -59.60 | 337.4 | 1124 | 750 | 2023-02-20T22:06:32 | YES |
| NZDUSD S15 | 6m | 100% real ticks | real ticks begin from 2026.01.01 00:00:00 | -2267.44 | -89.44 | 85.5 | 2 | 345 | 2026-09-29T23:59:53 | no |
| USDCAD C15 | 3y | 24% real ticks | real ticks begin from 2026.01.01 00:00:00 | -3556.50 | 0.00 | 570.4 | 2334 | 1153 | 2024-09-15T23:00:00 | YES |
| USDCAD C15 | 5y | 14% real ticks | real ticks begin from 2026.01.01 00:00:00 | -3479.12 | 0.00 | 454.7 | 1588 | 1633 | 2022-12-25T23:05:13 | YES |
| USDCAD S15 | 1y | 74% real ticks | real ticks begin from 2026.01.01 00:00:00 | -4877.34 | 0.00 | 154.6 | 1438 | 629 | 2026-09-29T18:23:08 | no |
| USDCAD S15 | 3y | 24% real ticks | real ticks begin from 2026.01.01 00:00:00 | -2367.18 | 0.00 | 570.4 | 1440 | 1851 | 2026-09-29T18:23:08 | no |
| USDCAD S15 | 5y | 14% real ticks | real ticks begin from 2026.01.01 00:00:00 | -3586.84 | 0.00 | 822.1 | 6 | 1797 | 2025-01-02T13:30:40 | YES |
| USDCAD S15 | 6m | 100% real ticks | real ticks begin from 2026.01.01 00:00:00 | -3931.60 | 0.00 | 154.6 | 2 | 318 | 2026-09-29T18:23:08 | no |
| USDCHF C15 | 3y | 24% real ticks | real ticks begin from 2026.01.01 00:00:00 | -3044.31 | -144.15 | 1051.5 | 4 | 1230 | 2024-10-07T17:00:00 | YES |
| USDCHF C15 | 5y | 14% real ticks | real ticks begin from 2026.01.01 00:00:00 | -2951.40 | -82.78 | 176.4 | 6 | 1010 | 2022-06-17T15:00:00 | YES |
| USDCHF S15 | 1y | 74% real ticks | real ticks begin from 2026.01.01 00:00:00 | -3768.33 | -317.21 | 145.8 | 890 | 688 | 2026-09-28T10:01:48 | no |
| USDCHF S15 | 3y | 24% real ticks | real ticks begin from 2026.01.01 00:00:00 | -4235.43 | -354.32 | 145.8 | 898 | 1907 | 2026-09-21T14:04:00 | YES |
| USDCHF S15 | 5y | 14% real ticks | real ticks begin from 2026.01.01 00:00:00 | -3028.77 | -155.85 | 474.7 | 18 | 1569 | 2024-04-21T21:05:00 | YES |
| USDCHF S15 | 6m | 100% real ticks | real ticks begin from 2026.01.01 00:00:00 | -2601.41 | -286.02 | 145.8 | 8 | 354 | 2026-09-28T10:01:48 | no |
| USDJPY C15 | 3y | 24% real ticks | real ticks begin from 2026.01.01 00:00:00 | -2038.00 | -78.27 | 350.8 | 3302 | 2021 | 2025-04-04T19:15:00 | YES |
| USDJPY C15 | 5y | 14% real ticks | real ticks begin from 2026.01.01 00:00:00 | -2441.16 | -193.34 | 330.6 | 1196 | 1926 | 2023-01-30T11:30:00 | YES |
| USDJPY S15 | 1y | 74% real ticks | real ticks begin from 2026.01.01 00:00:00 | -1782.02 | -116.97 | 160.4 | 12 | 494 | 2026-09-29T18:01:39 | no |
| USDJPY S15 | 3y | 24% real ticks | real ticks begin from 2026.01.01 00:00:00 | -1422.10 | -91.23 | 160.4 | 344 | 1492 | 2026-09-29T18:01:39 | no |
| USDJPY S15 | 5y | 14% real ticks | real ticks begin from 2026.01.01 00:00:00 | -2669.24 | -153.99 | 330.7 | 336 | 2117 | 2025-08-07T00:34:33 | YES |
| USDJPY S15 | 6m | 100% real ticks | real ticks begin from 2026.01.01 00:00:00 | -1316.89 | -56.39 | 160.4 | 2 | 240 | 2026-09-29T18:01:39 | no |
| USTEC C5 | 3y | 24% real ticks | real ticks begin from 2026.01.01 00:00:00 | -1589.14 | -91.89 | 138.5 | 123952 | 21619 | 2024-01-25T13:30:40 | no |
| USTEC C5 | 5y | 14% real ticks | real ticks begin from 2026.01.01 00:00:00 | -1701.71 | -104.25 | 108.6 | 137930 | 34478 | 2022-04-13T02:21:19 | no |
| USTEC S5 | 1y | 74% real ticks | real ticks begin from 2026.01.01 00:00:00 | -4096.94 | -504.72 | 97.3 | 6686 | 1194 | 2026-09-29T11:49:36 | no |
| USTEC S5 | 3y | 24% real ticks | real ticks begin from 2026.01.01 00:00:00 | -1474.38 | -135.88 | 105.2 | 52572 | 4745 | 2024-09-24T05:00:15 | no |
| USTEC S5 | 5y | 14% real ticks | real ticks begin from 2026.01.01 00:00:00 | -1673.29 | -212.78 | 112.7 | 4 | 2097 | 2023-03-15T13:28:14 | YES |
| USTEC S5 | 6m | 100% real ticks | real ticks begin from 2026.01.01 00:00:00 | -2526.58 | -279.23 | 97.3 | 14 | 582 | 2026-09-29T11:49:36 | no |
| XAUUSD C15 | 3y | 24% real ticks | real ticks begin from 2026.01.01 00:00:00 | -3125.80 | -550.15 | 330.2 | 26914 | 2307 | 2025-04-29T14:28:04 | YES |
| XAUUSD C15 | 5y | 14% real ticks | real ticks begin from 2026.01.01 00:00:00 | -2773.20 | -596.59 | 502.3 | 26110 | 1923 | 2023-03-16T17:00:00 | YES |
| XAUUSD C5 | 3y | 24% real ticks | real ticks begin from 2026.01.01 00:00:00 | -3131.52 | -307.89 | 86.3 | 207746 | 23033 | 2024-02-09T11:27:27 | no |
| XAUUSD C5 | 5y | 14% real ticks | real ticks begin from 2026.01.01 00:00:00 | -2190.76 | -229.07 | 622.9 | 277828 | 37652 | 2022-03-08T00:44:41 | no |
| XAUUSD S15 | 1y | 74% real ticks | real ticks begin from 2026.01.01 00:00:00 | -90.56 | -40.00 | 283.9 | 12 | 250 | 2026-09-28T12:05:28 | no |
| XAUUSD S15 | 3y | 24% real ticks | real ticks begin from 2026.01.01 00:00:00 | -1500.75 | -425.61 | 283.9 | 11170 | 966 | 2026-09-28T12:05:28 | no |
| XAUUSD S15 | 5y | 14% real ticks | real ticks begin from 2026.01.01 00:00:00 | -2368.18 | -1079.75 | 398.1 | 12808 | 1835 | 2026-09-28T12:05:28 | no |
| XAUUSD S15 | 6m | 100% real ticks | real ticks begin from 2026.01.01 00:00:00 | -46.77 | -10.95 | 54.7 | 2 | 102 | 2026-09-28T12:05:28 | no |
| XAUUSD S5 | 1y | 74% real ticks | real ticks begin from 2026.01.01 00:00:00 | -995.41 | -102.44 | 117.6 | 12698 | 1010 | 2026-09-29T23:59:58 | no |
| XAUUSD S5 | 3y | 24% real ticks | real ticks begin from 2026.01.01 00:00:00 | -2756.37 | -236.18 | 209.9 | 22460 | 1758 | 2024-12-27T02:10:00 | YES |
| XAUUSD S5 | 5y | 14% real ticks | real ticks begin from 2026.01.01 00:00:00 | -2677.29 | -443.19 | 130.6 | 21240 | 2143 | 2023-01-03T15:22:25 | YES |
| XAUUSD S5 | 6m | 100% real ticks | real ticks begin from 2026.01.01 00:00:00 | -697.45 | -30.68 | 97.1 | 2 | 476 | 2026-09-29T23:59:58 | no |

## Limitations

Older history may use generated ticks, even when Model 4 was requested. The quality/start notes below are per run. Rejection log lines can repeat between terminal and agent journals, including repeated cancellation attempts while a market is closed; expiry can be delayed until cancellation is accepted. Round-up sizing/minimum lots may exceed 1% and magnify drawdown. Some long-window accounts exhaust their balance before the end date: their trade frequencies use the entire requested window, and they do not represent continuous five-year trading. Positions may remain open overnight or over weekends; this is not a strictly flat-at-close day-trading system. These are historical simulations, not expected future returns or proof of a 90% win rate. A control comparison does not establish causality; markets, timeframes and overlapping samples create selection bias. No live deployment.

[MetaTrader tick-generation documentation](https://www.metatrader5.com/en/terminal/help/algotrading/tick_generation).

Detailed ledgers, cost-aware metrics, nominal Wilson intervals (independence assumption), holding times and build identities: ANALYSIS.json. Broker costs are specific to this account/history, not generic FTMO costs.
