# ATR Touch — results

Isolated MT5 tester, Exness-MT5Trial16, $10,000, 1% risk to a catastrophe stop (lots rounded up), long only. Screen = Model 1 (1-minute OHLC); windows 3y (2023-09-01) and 5y (2021-09-01) to 2026-09-01. No optimization.
Cell = trades (per month, per trading day) · return · PF · win rate · max equity DD · avg win/loss streak (longest win/loss).

## M5R1 — ATR touch M5, 1:1
Evidence: IQ Capital reel (@iqcapitalofficial), trader 'MNQ' - 3.1 x ATR lower-band limit, long only. Control: random longs, same exits.

| Symbol | 3y signal | 3y control | 5y signal | 5y control | Gate |
|---|---|---|---|---|---|
| USTEC | 839 (23.3/mo, 1.07/day) · -90.0% · PF 0.50 · win 39% · DD 91.7% · 1.6/2.5 (6/11) | 1721 (47.8/mo, 2.20/day) · -93.9% · PF 0.63 · win 45% · DD 94.8% | 1408 (23.5/mo, 1.08/day) · -99.2% · PF 0.41 · win 36% · DD 99.4% · 1.6/2.7 (7/15) | 2628 (43.8/mo, 2.02/day) · -99.5% · PF 0.64 · win 44% · DD 99.6% | FAIL: 3y not positive; 3y PF 0.50; 5y not positive; 5y PF 0.41 |
| US500 | 794 (22.1/mo, 1.01/day) · -89.1% · PF 0.56 · win 41% · DD 90.9% · 1.6/2.3 (6/12) | 1471 (40.9/mo, 1.88/day) · -95.6% · PF 0.58 · win 44% · DD 95.6% | 1266 (21.1/mo, 0.97/day) · -98.8% · PF 0.45 · win 37% · DD 99.0% · 1.6/2.7 (6/14) | 2157 (36.0/mo, 1.65/day) · -99.2% · PF 0.59 · win 43% · DD 99.2% | FAIL: 3y not positive; 3y PF 0.56; 5y not positive; 5y PF 0.45 |
| XAUUSD | 663 (18.4/mo, 0.85/day) · -43.3% · PF 0.84 · win 48% · DD 51.7% · 1.8/2.0 (9/8) | 2081 (57.8/mo, 2.65/day) · -91.9% · PF 0.78 · win 47% · DD 93.5% | 1145 (19.1/mo, 0.88/day) · -72.1% · PF 0.78 · win 47% · DD 76.7% · 1.8/2.1 (9/10) | 2406 (40.1/mo, 1.85/day) · -100.0% · PF 0.68 · win 44% · DD 100.0% | FAIL: 3y not positive; 3y PF 0.84; 5y not positive; 5y PF 0.78 |
| BTCUSD | 1050 (29.2/mo, 1.34/day) · +31.8% · PF 1.07 · win 54% · DD 41.3% · 2.2/1.9 (16/8) | 2988 (83.0/mo, 3.81/day) · -99.6% · PF 0.65 · win 45% · DD 99.7% | 2110 (35.2/mo, 1.62/day) · -96.1% · PF 0.54 · win 46% · DD 98.8% · 1.9/2.2 (16/15) | 1725 (28.8/mo, 1.32/day) · -100.0% · PF 0.48 · win 38% · DD 100.0% | FAIL: 3y PF 1.07; 5y not positive; 5y PF 0.54 |

Breadth: 0/4 symbols positive over 5y.

## M5R2 — ATR touch M5, 2:1
Evidence: IQ Capital reel (@iqcapitalofficial), trader 'MNQ' - 3.1 x ATR lower-band limit, long only. Control: random longs, same exits.

| Symbol | 3y signal | 3y control | 5y signal | 5y control | Gate |
|---|---|---|---|---|---|
| USTEC | 836 (23.2/mo, 1.07/day) · -89.7% · PF 0.58 · win 27% · DD 92.5% · 1.3/3.7 (4/26) | 1721 (47.8/mo, 2.20/day) · -93.2% · PF 0.73 · win 31% · DD 95.2% | 1405 (23.4/mo, 1.08/day) · -98.8% · PF 0.52 · win 25% · DD 99.2% · 1.3/4.0 (6/26) | 2628 (43.8/mo, 2.02/day) · -99.7% · PF 0.64 · win 29% · DD 99.9% | FAIL: 3y not positive; 3y PF 0.58; 5y not positive; 5y PF 0.52 |
| US500 | 783 (21.7/mo, 1.00/day) · -82.8% · PF 0.71 · win 30% · DD 85.9% · 1.4/3.3 (5/17) | 1471 (40.9/mo, 1.88/day) · -97.0% · PF 0.64 · win 29% · DD 97.1% | 1253 (20.9/mo, 0.96/day) · -97.7% · PF 0.58 · win 27% · DD 98.1% · 1.4/3.7 (5/17) | 2157 (36.0/mo, 1.65/day) · -99.6% · PF 0.67 · win 29% · DD 99.6% | FAIL: 3y not positive; 3y PF 0.71; 5y not positive; 5y PF 0.58 |
| XAUUSD | 656 (18.2/mo, 0.84/day) · -22.1% · PF 0.94 · win 33% · DD 47.8% · 1.4/2.8 (4/11) | 2081 (57.8/mo, 2.65/day) · -92.5% · PF 0.82 · win 31% · DD 95.4% | 1134 (18.9/mo, 0.87/day) · -51.6% · PF 0.89 · win 33% · DD 68.1% · 1.4/2.9 (4/18) | 2406 (40.1/mo, 1.85/day) · -100.0% · PF 0.74 · win 30% · DD 100.0% | FAIL: 3y not positive; 3y PF 0.94; 5y not positive; 5y PF 0.89 |
| BTCUSD | 1039 (28.9/mo, 1.33/day) · -26.9% · PF 0.95 · win 34% · DD 45.3% · 1.6/3.1 (6/13) | 2902 (80.6/mo, 3.70/day) · -100.0% · PF 0.73 · win 30% · DD 100.0% | 2090 (34.8/mo, 1.60/day) · -96.2% · PF 0.65 · win 31% · DD 97.3% · 1.5/3.3 (6/21) | 1761 (29.4/mo, 1.35/day) · -100.0% · PF 0.59 · win 26% · DD 100.0% | FAIL: 3y not positive; 3y PF 0.95; 5y not positive; 5y PF 0.65 |

Breadth: 0/4 symbols positive over 5y.

## M15R1 — ATR touch M15, 1:1
Evidence: IQ Capital reel (@iqcapitalofficial), trader 'MNQ' - 3.1 x ATR lower-band limit, long only. Control: random longs, same exits.

| Symbol | 3y signal | 3y control | 5y signal | 5y control | Gate |
|---|---|---|---|---|---|
| USTEC | 525 (14.6/mo, 0.67/day) · -68.1% · PF 0.63 · win 41% · DD 70.1% · 1.7/2.4 (6/14) | 648 (18.0/mo, 0.83/day) · -45.9% · PF 0.80 · win 48% · DD 51.0% | 838 (14.0/mo, 0.64/day) · -91.2% · PF 0.48 · win 38% · DD 91.8% · 1.6/2.6 (6/15) | 1065 (17.8/mo, 0.82/day) · -75.7% · PF 0.74 · win 46% · DD 78.4% | FAIL: 3y not positive; 3y PF 0.63; 3y not above control; 5y not positive; 5y PF 0.48; 5y not above control |
| US500 | 432 (12.0/mo, 0.55/day) · -69.1% · PF 0.54 · win 40% · DD 71.6% · 1.7/2.6 (7/12) | 597 (16.6/mo, 0.76/day) · -67.7% · PF 0.68 · win 44% · DD 68.1% | 706 (11.8/mo, 0.54/day) · -87.4% · PF 0.53 · win 39% · DD 88.6% · 1.7/2.7 (7/14) | 955 (15.9/mo, 0.73/day) · -80.5% · PF 0.75 · win 45% · DD 82.3% | FAIL: 3y not positive; 3y PF 0.54; 3y not above control; 5y not positive; 5y PF 0.53; 5y not above control |
| XAUUSD | 382 (10.6/mo, 0.49/day) · -34.0% · PF 0.81 · win 46% · DD 39.1% · 2.0/2.3 (7/9) | 699 (19.4/mo, 0.89/day) · -13.7% · PF 0.96 · win 51% · DD 26.5% | 616 (10.3/mo, 0.47/day) · -45.8% · PF 0.83 · win 46% · DD 50.5% · 2.0/2.3 (9/9) | 1162 (19.4/mo, 0.89/day) · -55.7% · PF 0.87 · win 49% · DD 57.1% | FAIL: 3y not positive; 3y PF 0.81; 3y not above control; 5y not positive; 5y PF 0.83 |
| BTCUSD | 443 (12.3/mo, 0.57/day) · -30.0% · PF 0.85 · win 48% · DD 38.8% · 1.8/2.0 (8/7) | 1046 (29.0/mo, 1.33/day) · -76.8% · PF 0.75 · win 45% · DD 77.4% | 862 (14.4/mo, 0.66/day) · -84.3% · PF 0.57 · win 42% · DD 85.9% · 1.7/2.3 (8/11) | 1710 (28.5/mo, 1.31/day) · -96.8% · PF 0.63 · win 43% · DD 97.0% | FAIL: 3y not positive; 3y PF 0.85; 5y not positive; 5y PF 0.57 |

Breadth: 0/4 symbols positive over 5y.

## M15R2 — ATR touch M15, 2:1
Evidence: IQ Capital reel (@iqcapitalofficial), trader 'MNQ' - 3.1 x ATR lower-band limit, long only. Control: random longs, same exits.

| Symbol | 3y signal | 3y control | 5y signal | 5y control | Gate |
|---|---|---|---|---|---|
| USTEC | 519 (14.4/mo, 0.66/day) · -68.6% · PF 0.72 · win 27% · DD 70.8% · 1.3/3.5 (4/14) | 648 (18.0/mo, 0.83/day) · -13.9% · PF 0.96 · win 35% · DD 42.6% | 832 (13.9/mo, 0.64/day) · -90.8% · PF 0.57 · win 25% · DD 91.5% · 1.3/3.8 (4/17) | 1065 (17.8/mo, 0.82/day) · -53.2% · PF 0.88 · win 34% · DD 74.5% | FAIL: 3y not positive; 3y PF 0.72; 3y not above control; 5y not positive; 5y PF 0.57; 5y not above control |
| US500 | 431 (12.0/mo, 0.55/day) · -70.3% · PF 0.62 · win 26% · DD 74.0% · 1.4/4.0 (4/21) | 597 (16.6/mo, 0.76/day) · -56.9% · PF 0.79 · win 32% · DD 63.8% | 705 (11.8/mo, 0.54/day) · -85.7% · PF 0.64 · win 27% · DD 87.7% · 1.4/3.8 (4/22) | 955 (15.9/mo, 0.73/day) · -68.8% · PF 0.85 · win 33% · DD 79.7% | FAIL: 3y not positive; 3y PF 0.62; 3y not above control; 5y not positive; 5y PF 0.64; 5y not above control |
| XAUUSD | 378 (10.5/mo, 0.48/day) · -24.6% · PF 0.91 · win 32% · DD 42.8% · 1.7/3.7 (6/10) | 699 (19.4/mo, 0.89/day) · -23.3% · PF 0.95 · win 34% · DD 35.9% | 610 (10.2/mo, 0.47/day) · -10.5% · PF 0.98 · win 34% · DD 43.3% · 1.6/3.2 (6/10) | 1162 (19.4/mo, 0.89/day) · -58.9% · PF 0.89 · win 34% · DD 65.7% | FAIL: 3y not positive; 3y PF 0.91; 3y not above control; 5y not positive; 5y PF 0.98 |
| BTCUSD | 436 (12.1/mo, 0.56/day) · -54.5% · PF 0.75 · win 29% · DD 57.4% · 1.4/3.4 (4/17) | 1046 (29.0/mo, 1.33/day) · -72.1% · PF 0.82 · win 31% · DD 74.3% | 851 (14.2/mo, 0.65/day) · -88.6% · PF 0.60 · win 27% · DD 89.3% · 1.4/3.7 (4/17) | 1710 (28.5/mo, 1.31/day) · -97.2% · PF 0.65 · win 29% · DD 97.5% | FAIL: 3y not positive; 3y PF 0.75; 5y not positive; 5y PF 0.60 |

Breadth: 0/4 symbols positive over 5y.

## H1R1 — ATR touch H1, 1:1
Evidence: IQ Capital reel (@iqcapitalofficial), trader 'MNQ' - 3.1 x ATR lower-band limit, long only. Control: random longs, same exits.

| Symbol | 3y signal | 3y control | 5y signal | 5y control | Gate |
|---|---|---|---|---|---|
| USTEC | 285 (7.9/mo, 0.36/day) · -36.5% · PF 0.71 · win 43% · DD 37.4% · 1.7/2.2 (6/10) | 176 (4.9/mo, 0.22/day) · -4.5% · PF 0.95 · win 51% · DD 20.0% | 455 (7.6/mo, 0.35/day) · -61.3% · PF 0.63 · win 41% · DD 62.1% · 1.6/2.3 (6/11) | 291 (4.9/mo, 0.22/day) · -1.1% · PF 0.99 · win 52% · DD 19.9% | FAIL: 3y not positive; 3y PF 0.71; 3y not above control; 5y not positive; 5y PF 0.63; 5y not above control |
| US500 | 247 (6.9/mo, 0.32/day) · -49.9% · PF 0.57 · win 38% · DD 50.7% · 1.6/2.5 (8/7) | 173 (4.8/mo, 0.22/day) · -13.3% · PF 0.84 · win 49% · DD 21.8% | 377 (6.3/mo, 0.29/day) · -64.2% · PF 0.59 · win 38% · DD 64.9% · 1.6/2.6 (8/7) | 287 (4.8/mo, 0.22/day) · -11.5% · PF 0.92 · win 51% · DD 26.7% | FAIL: 3y not positive; 3y PF 0.57; 3y not above control; 5y not positive; 5y PF 0.59; 5y not above control |
| XAUUSD | 128 (3.6/mo, 0.16/day) · +16.2% · PF 1.25 · win 56% · DD 9.8% · 2.5/1.9 (7/7) | 178 (4.9/mo, 0.23/day) · -6.7% · PF 0.93 · win 50% · DD 14.2% | 224 (3.7/mo, 0.17/day) · +8.2% · PF 1.07 · win 53% · DD 15.5% · 2.2/2.0 (7/7) | 295 (4.9/mo, 0.23/day) · -11.9% · PF 0.92 · win 50% · DD 21.3% | FAIL: 5y PF 1.07 |
| BTCUSD | 165 (4.6/mo, 0.21/day) · +0.1% · PF 1.00 · win 51% · DD 14.1% · 2.2/2.1 (6/6) | 263 (7.3/mo, 0.34/day) · -19.5% · PF 0.86 · win 47% · DD 22.7% | 309 (5.2/mo, 0.24/day) · -16.7% · PF 0.89 · win 49% · DD 31.8% · 2.0/2.2 (6/7) | 437 (7.3/mo, 0.34/day) · -35.5% · PF 0.82 · win 47% · DD 36.2% | FAIL: 3y PF 1.00; 5y not positive; 5y PF 0.89 |

Breadth: 1/4 symbols positive over 5y.

## H1R2 — ATR touch H1, 2:1
Evidence: IQ Capital reel (@iqcapitalofficial), trader 'MNQ' - 3.1 x ATR lower-band limit, long only. Control: random longs, same exits.

| Symbol | 3y signal | 3y control | 5y signal | 5y control | Gate |
|---|---|---|---|---|---|
| USTEC | 276 (7.7/mo, 0.35/day) · -27.5% · PF 0.83 · win 30% · DD 36.0% · 1.4/3.3 (4/15) | 176 (4.9/mo, 0.22/day) · -7.7% · PF 0.93 · win 34% · DD 19.2% | 443 (7.4/mo, 0.34/day) · -56.3% · PF 0.72 · win 28% · DD 58.9% · 1.4/3.5 (4/15) | 291 (4.9/mo, 0.22/day) · -2.1% · PF 0.99 · win 35% · DD 19.2% | FAIL: 3y not positive; 3y PF 0.83; 3y not above control; 5y not positive; 5y PF 0.72; 5y not above control |
| US500 | 244 (6.8/mo, 0.31/day) · -50.3% · PF 0.64 · win 25% · DD 51.3% · 1.3/3.6 (4/15) | 173 (4.8/mo, 0.22/day) · -13.2% · PF 0.89 · win 33% · DD 17.1% | 371 (6.2/mo, 0.28/day) · -62.5% · PF 0.67 · win 26% · DD 63.8% · 1.3/3.7 (4/15) | 287 (4.8/mo, 0.22/day) · -5.1% · PF 0.98 · win 35% · DD 22.3% | FAIL: 3y not positive; 3y PF 0.64; 3y not above control; 5y not positive; 5y PF 0.67; 5y not above control |
| XAUUSD | 127 (3.5/mo, 0.16/day) · +29.7% · PF 1.31 · win 41% · DD 12.1% · 1.8/2.5 (6/7) | 178 (4.9/mo, 0.23/day) · +13.0% · PF 1.10 · win 37% · DD 13.2% | 220 (3.7/mo, 0.17/day) · +31.6% · PF 1.19 · win 39% · DD 12.5% · 1.6/2.5 (6/7) | 294 (4.9/mo, 0.23/day) · -2.9% · PF 0.99 · win 35% · DD 26.4% | PASS |
| BTCUSD | 164 (4.6/mo, 0.21/day) · +7.2% · PF 1.07 · win 35% · DD 19.8% · 1.7/3.1 (5/9) | 263 (7.3/mo, 0.34/day) · -17.0% · PF 0.90 · win 32% · DD 21.0% | 306 (5.1/mo, 0.23/day) · -24.2% · PF 0.86 · win 32% · DD 44.5% · 1.5/3.3 (5/10) | 437 (7.3/mo, 0.34/day) · -49.3% · PF 0.77 · win 30% · DD 50.3% | FAIL: 3y PF 1.07; 5y not positive; 5y PF 0.86 |

Breadth: 1/4 symbols positive over 5y.

## Advancing to the Model 4 real-tick test

H1R2 XAUUSD

## Model 4 real-tick confirmation (all periods)

| Edge | Symbol | 6m | 1y | 3y | 5y | Control 3y | Control 5y |
|---|---|---|---|---|---|---|---|
| H1R2 | XAUUSD | 21 (3.5/mo, 0.16/day) · -7.8% · PF 0.53 · win 19% · DD 8.7% · 1.0/3.4 (1/6) | 49 (4.1/mo, 0.19/day) · -3.3% · PF 0.91 · win 31% · DD 10.3% · 1.4/2.8 (3/6) | 127 (3.5/mo, 0.16/day) · +27.1% · PF 1.29 · win 39% · DD 9.7% · 1.7/2.5 (6/7) | 220 (3.7/mo, 0.17/day) · +22.3% · PF 1.14 · win 37% · DD 14.9% · 1.5/2.6 (6/7) | 178 (4.9/mo, 0.23/day) · +12.8% · PF 1.10 · win 37% · DD 13.2% | 294 (4.9/mo, 0.23/day) · -4.1% · PF 0.98 · win 35% · DD 26.6% |
