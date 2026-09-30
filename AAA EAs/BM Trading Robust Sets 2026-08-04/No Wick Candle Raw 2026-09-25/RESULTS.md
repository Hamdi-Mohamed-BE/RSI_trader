# No-wick candle entry model — raw native results

Isolated MT5 tester, Exness-MT5Trial16, $10,000, 1% risk (lots rounded up), M15/H1 signals, Model 4 (real ticks from 2026-01, bars-generated before), 150 ms delay; windows end 2026-09-25. No optimization.
Cell = trades (per month, per trading day Mon-Fri) · return · PF · win rate · max equity DD · avg win/loss streak (longest win/loss).

## XAUUSD

| Period | M15 — No-wick candle, M15, 1:1 | H1 — No-wick candle, H1, 1:1 |
|---|---|---|
| 6m | 161 (26.6/mo, 1.22/day) · -17.3% · PF 0.81 · win 45% · DD 17.9% · 2.0/2.4 (6/7) | 39 (6.5/mo, 0.30/day) · +0.2% · PF 1.01 · win 46% · DD 5.9% · 1.8/2.1 (5/5) |
| 1y | 355 (29.6/mo, 1.36/day) · -41.0% · PF 0.77 · win 44% · DD 42.0% · 1.8/2.3 (6/7) | 77 (6.4/mo, 0.30/day) · +6.4% · PF 1.14 · win 53% · DD 8.6% · 2.0/1.9 (5/5) |
| 3y | 1167 (32.4/mo, 1.49/day) · -61.0% · PF 0.88 · win 48% · DD 66.9% · 2.0/2.2 (6/9) | 265 (7.4/mo, 0.34/day) · -2.0% · PF 0.99 · win 51% · DD 22.2% · 2.1/2.1 (9/10) |
| 5y | 2063 (34.4/mo, 1.58/day) · -97.5% · PF 0.78 · win 46% · DD 97.8% · 1.9/2.2 (8/9) | 491 (8.2/mo, 0.38/day) · +9.0% · PF 1.03 · win 52% · DD 21.5% · 2.2/2.1 (9/10) |

Any-candle controls (3y, 5y):

| Period | CM15 (control for M15) | CH1 (control for H1) |
|---|---|---|
| 3y | 3452 (95.9/mo, 4.40/day) · -87.6% · PF 0.90 · win 48% · DD 89.9% · 2.0/2.1 (11/13) | 858 (23.8/mo, 1.09/day) · -15.8% · PF 0.96 · win 50% · DD 54.7% · 2.1/2.1 (10/11) |
| 5y | 3200 (53.3/mo, 2.45/day) · -100.0% · PF 0.78 · win 45% · DD 100.0% · 1.9/2.3 (11/17) | 1412 (23.5/mo, 1.08/day) · -42.1% · PF 0.92 · win 49% · DD 68.4% · 2.0/2.1 (10/11) |

## USTEC

| Period | M15 — No-wick candle, M15, 1:1 | H1 — No-wick candle, H1, 1:1 |
|---|---|---|
| 6m | 203 (33.6/mo, 1.54/day) · -0.1% · PF 1.00 · win 52% · DD 10.7% · 2.2/2.1 (8/6) | 49 (8.1/mo, 0.37/day) · +4.5% · PF 1.19 · win 55% · DD 6.0% · 1.9/1.7 (4/4) |
| 1y | 396 (33.0/mo, 1.52/day) · -6.9% · PF 0.97 · win 51% · DD 19.6% · 2.1/2.0 (8/7) | 97 (8.1/mo, 0.37/day) · +3.3% · PF 1.07 · win 52% · DD 8.3% · 1.8/1.7 (5/4) |
| 3y | 1165 (32.4/mo, 1.49/day) · -59.6% · PF 0.84 · win 48% · DD 64.4% · 2.0/2.2 (8/11) | 306 (8.5/mo, 0.39/day) · -26.4% · PF 0.81 · win 46% · DD 33.3% · 1.8/2.1 (5/6) |
| 5y | 1889 (31.5/mo, 1.45/day) · -78.7% · PF 0.84 · win 47% · DD 82.7% · 1.9/2.1 (8/11) | 497 (8.3/mo, 0.38/day) · -30.1% · PF 0.87 · win 48% · DD 39.9% · 1.9/2.1 (8/8) |

Any-candle controls (3y, 5y):

| Period | CM15 (control for M15) | CH1 (control for H1) |
|---|---|---|
| 3y | 3016 (83.8/mo, 3.85/day) · -99.9% · PF 0.71 · win 45% · DD 100.0% · 1.8/2.2 (8/14) | 861 (23.9/mo, 1.10/day) · -67.6% · PF 0.77 · win 45% · DD 70.3% · 1.7/2.1 (7/12) |
| 5y | 3145 (52.4/mo, 2.41/day) · -100.0% · PF 0.73 · win 43% · DD 100.0% · 1.8/2.4 (8/15) | 1426 (23.8/mo, 1.09/day) · -87.8% · PF 0.77 · win 44% · DD 89.2% · 1.7/2.2 (7/12) |

## BTCUSD

| Period | M15 — No-wick candle, M15, 1:1 | H1 — No-wick candle, H1, 1:1 |
|---|---|---|
| 6m | 315 (52.1/mo, 2.39/day) · -17.2% · PF 0.89 · win 48% · DD 19.1% · 1.9/2.0 (6/8) | 80 (13.2/mo, 0.61/day) · +3.8% · PF 1.09 · win 52% · DD 7.3% · 1.8/1.7 (5/4) |
| 1y | 680 (56.7/mo, 2.61/day) · -32.1% · PF 0.91 · win 48% · DD 47.2% · 1.9/2.0 (9/8) | 153 (12.8/mo, 0.59/day) · +4.9% · PF 1.06 · win 52% · DD 8.4% · 1.9/1.9 (5/5) |
| 3y | 1793 (49.8/mo, 2.29/day) · -75.7% · PF 0.85 · win 47% · DD 76.5% · 2.0/2.2 (11/10) | 423 (11.7/mo, 0.54/day) · -12.7% · PF 0.94 · win 49% · DD 24.1% · 1.8/1.9 (5/9) |
| 5y | 2787 (46.5/mo, 2.14/day) · -97.4% · PF 0.77 · win 46% · DD 97.7% · 1.9/2.2 (11/10) | 622 (10.4/mo, 0.48/day) · -24.1% · PF 0.92 · win 49% · DD 34.4% · 1.8/1.9 (7/9) |

Any-candle controls (3y, 5y):

| Period | CM15 (control for M15) | CH1 (control for H1) |
|---|---|---|
| 3y | 3161 (87.8/mo, 4.03/day) · -100.0% · PF 0.78 · win 45% · DD 100.0% · 1.9/2.2 (9/11) | 1328 (36.9/mo, 1.69/day) · -54.0% · PF 0.88 · win 48% · DD 62.7% · 1.9/2.1 (8/10) |
| 5y | 2948 (49.1/mo, 2.26/day) · -100.0% · PF 0.77 · win 43% · DD 100.0% · 1.8/2.3 (14/16) | 2202 (36.7/mo, 1.69/day) · -82.0% · PF 0.85 · win 48% · DD 84.8% · 1.9/2.1 (8/11) |

## EURUSD

| Period | M15 — No-wick candle, M15, 1:1 | H1 — No-wick candle, H1, 1:1 |
|---|---|---|
| 6m | 264 (43.7/mo, 2.00/day) · -0.6% · PF 1.00 · win 53% · DD 20.9% · 2.2/1.9 (8/6) | 45 (7.4/mo, 0.34/day) · -5.7% · PF 0.78 · win 47% · DD 10.7% · 1.5/1.8 (3/3) |
| 1y | 510 (42.5/mo, 1.95/day) · -13.5% · PF 0.95 · win 52% · DD 33.3% · 2.3/2.1 (8/8) | 97 (8.1/mo, 0.37/day) · -10.8% · PF 0.80 · win 46% · DD 13.9% · 1.6/1.9 (7/5) |
| 3y | 1376 (38.2/mo, 1.76/day) · -85.7% · PF 0.73 · win 46% · DD 88.2% · 1.9/2.2 (8/10) | 342 (9.5/mo, 0.44/day) · -28.4% · PF 0.83 · win 46% · DD 33.6% · 1.7/2.0 (7/7) |
| 5y | 2463 (41.1/mo, 1.89/day) · -96.8% · PF 0.74 · win 46% · DD 97.4% · 1.9/2.3 (8/11) | 600 (10.0/mo, 0.46/day) · -47.7% · PF 0.81 · win 46% · DD 51.7% · 1.7/2.0 (7/11) |

Any-candle controls (3y, 5y):

| Period | CM15 (control for M15) | CH1 (control for H1) |
|---|---|---|
| 3y | 3264 (90.6/mo, 4.16/day) · -100.0% · PF 0.73 · win 45% · DD 100.0% · 1.9/2.3 (10/11) | 943 (26.2/mo, 1.20/day) · -45.9% · PF 0.85 · win 48% · DD 58.7% · 2.0/2.2 (10/9) |
| 5y | 2871 (47.9/mo, 2.20/day) · -100.0% · PF 0.70 · win 42% · DD 100.0% · 1.7/2.4 (9/13) | 1524 (25.4/mo, 1.17/day) · -56.3% · PF 0.90 · win 49% · DD 69.0% · 2.0/2.1 (10/9) |

## Pre-registered gate (step 4)

Pass = positive on 3y and 5y, PF ≥ 1.15 on 3y and 5y, ≥ 30 trades per window, and higher return than its any-candle control on 3y and 5y.

| Symbol | Variant | 3y | 5y | Control 3y | Control 5y | Result |
|---|---|---|---|---|---|---|
| XAUUSD | M15 | -61.0% PF 0.88 | -97.5% PF 0.78 | -87.6% PF 0.90 | -100.0% PF 0.78 | FAIL: 3y not positive; 3y PF 0.88; 5y not positive; 5y PF 0.78 |
| XAUUSD | H1 | -2.0% PF 0.99 | +9.0% PF 1.03 | -15.8% PF 0.96 | -42.1% PF 0.92 | FAIL: 3y not positive; 3y PF 0.99; 5y PF 1.03 |
| USTEC | M15 | -59.6% PF 0.84 | -78.7% PF 0.84 | -99.9% PF 0.71 | -100.0% PF 0.73 | FAIL: 3y not positive; 3y PF 0.84; 5y not positive; 5y PF 0.84 |
| USTEC | H1 | -26.4% PF 0.81 | -30.1% PF 0.87 | -67.6% PF 0.77 | -87.8% PF 0.77 | FAIL: 3y not positive; 3y PF 0.81; 5y not positive; 5y PF 0.87 |
| BTCUSD | M15 | -75.7% PF 0.85 | -97.4% PF 0.77 | -100.0% PF 0.78 | -100.0% PF 0.77 | FAIL: 3y not positive; 3y PF 0.85; 5y not positive; 5y PF 0.77 |
| BTCUSD | H1 | -12.7% PF 0.94 | -24.1% PF 0.92 | -54.0% PF 0.88 | -82.0% PF 0.85 | FAIL: 3y not positive; 3y PF 0.94; 5y not positive; 5y PF 0.92 |
| EURUSD | M15 | -85.7% PF 0.73 | -96.8% PF 0.74 | -100.0% PF 0.73 | -100.0% PF 0.70 | FAIL: 3y not positive; 3y PF 0.73; 5y not positive; 5y PF 0.74 |
| EURUSD | H1 | -28.4% PF 0.83 | -47.7% PF 0.81 | -45.9% PF 0.85 | -56.3% PF 0.90 | FAIL: 3y not positive; 3y PF 0.83; 5y not positive; 5y PF 0.81 |

Passed: none
