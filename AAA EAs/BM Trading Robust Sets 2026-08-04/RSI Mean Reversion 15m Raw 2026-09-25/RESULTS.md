# RSI Mean Reversion 15m — raw native results

Isolated MT5 tester, Exness-MT5Trial16, $10,000, 1% risk (lots rounded up), M15, Model 4 (real ticks from 2026-01, bars-generated before), 150 ms delay; windows end 2026-09-01. No optimization.
Cell = trades · return · PF · win rate · max equity DD · avg win/loss streak (longest win/loss).

## XAUUSD

| Period | TF3 — RSI(2) 10/90 + EMA200 trend filter, 3 ATR stop | NF3 — RSI(2) 10/90, no trend filter, 3 ATR stop | TF15 — RSI(2) 10/90 + EMA200 trend filter, 1.5 ATR stop |
|---|---|---|---|
| 6m | 543 · -8.2% · PF 0.92 · win 65% · DD 16.9% · 2.9/1.6 (10/5) | 1451 · -19.4% · PF 0.92 · win 65% · DD 31.8% · 2.8/1.6 (17/6) | 622 · -1.5% · PF 0.99 · win 63% · DD 23.2% · 2.8/1.7 (11/6) |
| 1y | 1032 · -14.7% · PF 0.92 · win 65% · DD 21.8% · 2.8/1.6 (10/5) | 2839 · -33.3% · PF 0.93 · win 65% · DD 48.5% · 2.8/1.6 (17/8) | 1185 · -9.3% · PF 0.97 · win 62% · DD 23.4% · 2.7/1.6 (11/6) |
| 3y | 3076 · -52.1% · PF 0.86 · win 64% · DD 54.8% · 2.7/1.6 (13/7) | 7552 · -100.0% · PF 0.83 · win 63% · DD 100.0% · 2.7/1.6 (17/8) | 3572 · -80.3% · PF 0.82 · win 60% · DD 84.3% · 2.5/1.7 (12/7) |
| 5y | 5185 · -78.3% · PF 0.84 · win 63% · DD 79.6% · 2.6/1.6 (14/10) | 9646 · -100.0% · PF 0.83 · win 62% · DD 100.0% · 2.5/1.6 (19/9) | 6053 · -94.0% · PF 0.84 · win 60% · DD 98.3% · 2.5/1.7 (15/8) |

Random-entry controls (3y, 5y):

| Period | CT (control for TF3, NF3, TF15) |
|---|---|
| 3y | 1631 · -40.9% · PF 0.84 · win 48% · DD 43.8% · 1.9/2.1 (11/10) |
| 5y | 2721 · -63.4% · PF 0.81 · win 47% · DD 66.0% · 1.8/2.1 (11/11) |

## USTEC

| Period | TF3 — RSI(2) 10/90 + EMA200 trend filter, 3 ATR stop | NF3 — RSI(2) 10/90, no trend filter, 3 ATR stop | TF15 — RSI(2) 10/90 + EMA200 trend filter, 1.5 ATR stop |
|---|---|---|---|
| 6m | 525 · +4.3% · PF 1.05 · win 66% · DD 6.7% · 2.8/1.5 (10/5) | 1430 · +14.0% · PF 1.06 · win 65% · DD 11.9% · 2.7/1.5 (13/7) | 608 · +11.3% · PF 1.06 · win 62% · DD 13.9% · 2.6/1.6 (10/8) |
| 1y | 1044 · -3.6% · PF 0.98 · win 65% · DD 15.3% · 2.9/1.6 (12/6) | 2821 · -21.1% · PF 0.94 · win 64% · DD 36.3% · 2.7/1.6 (13/7) | 1197 · -2.2% · PF 0.99 · win 61% · DD 25.7% · 2.7/1.7 (10/8) |
| 3y | 3127 · -64.0% · PF 0.78 · win 62% · DD 66.8% · 2.6/1.7 (14/8) | 8428 · -96.2% · PF 0.69 · win 60% · DD 98.0% · 2.5/1.7 (14/11) | 3573 · -90.1% · PF 0.70 · win 59% · DD 91.8% · 2.4/1.8 (12/10) |
| 5y | 5231 · -92.9% · PF 0.67 · win 61% · DD 93.2% · 2.5/1.7 (14/8) | 6341 · -100.0% · PF 0.64 · win 58% · DD 100.0% · 2.3/1.8 (12/11) | 3707 · -100.0% · PF 0.63 · win 54% · DD 100.0% · 2.1/1.9 (10/10) |

Random-entry controls (3y, 5y):

| Period | CT (control for TF3, NF3, TF15) |
|---|---|
| 3y | 1633 · -44.8% · PF 0.82 · win 47% · DD 46.4% · 2.0/2.3 (10/11) |
| 5y | 2679 · -72.5% · PF 0.76 · win 47% · DD 73.2% · 1.9/2.2 (10/11) |

## BTCUSD

| Period | TF3 — RSI(2) 10/90 + EMA200 trend filter, 3 ATR stop | NF3 — RSI(2) 10/90, no trend filter, 3 ATR stop | TF15 — RSI(2) 10/90 + EMA200 trend filter, 1.5 ATR stop |
|---|---|---|---|
| 6m | 792 · -2.1% · PF 0.98 · win 64% · DD 14.4% · 2.6/1.6 (11/5) | 2129 · -34.7% · PF 0.90 · win 65% · DD 40.0% · 2.7/1.5 (14/7) | 900 · -7.8% · PF 0.97 · win 63% · DD 25.4% · 2.5/1.6 (11/6) |
| 1y | 1526 · +20.5% · PF 1.08 · win 66% · DD 14.5% · 2.9/1.6 (12/6) | 4161 · -24.5% · PF 0.97 · win 66% · DD 42.2% · 2.9/1.6 (17/7) | 1721 · +50.2% · PF 1.07 · win 64% · DD 25.3% · 2.7/1.6 (12/6) |
| 3y | 4559 · -40.4% · PF 0.90 · win 64% · DD 61.0% · 2.7/1.6 (17/7) | 12434 · -97.8% · PF 0.76 · win 64% · DD 99.3% · 2.7/1.6 (19/9) | 5129 · -81.9% · PF 0.81 · win 62% · DD 89.7% · 2.6/1.6 (12/8) |
| 5y | 7544 · -89.8% · PF 0.76 · win 63% · DD 94.3% · 2.6/1.7 (17/9) | 7151 · -100.0% · PF 0.76 · win 62% · DD 100.0% · 2.4/1.7 (15/9) | 4360 · -100.0% · PF 0.76 · win 59% · DD 100.0% · 2.3/1.8 (13/12) |

Random-entry controls (3y, 5y):

| Period | CT (control for TF3, NF3, TF15) |
|---|---|
| 3y | 2415 · -54.7% · PF 0.81 · win 46% · DD 59.0% · 1.8/2.2 (8/15) |
| 5y | 4027 · -90.0% · PF 0.69 · win 44% · DD 91.3% · 1.7/2.3 (10/15) |

## Pre-registered gate (step 4)

Pass = positive on 3y and 5y, PF ≥ 1.15 on 3y and 5y, ≥ 30 trades per window, and higher return than the random-entry control on 3y and 5y.

| Symbol | Variant | 3y | 5y | Control 3y | Control 5y | Result |
|---|---|---|---|---|---|---|
| XAUUSD | TF3 | -52.1% PF 0.86 | -78.3% PF 0.84 | -40.9% PF 0.84 | -63.4% PF 0.81 | FAIL: 3y not positive; 3y PF 0.86; 3y not above control; 5y not positive; 5y PF 0.84; 5y not above control |
| XAUUSD | NF3 | -100.0% PF 0.83 | -100.0% PF 0.83 | -40.9% PF 0.84 | -63.4% PF 0.81 | FAIL: 3y not positive; 3y PF 0.83; 3y not above control; 5y not positive; 5y PF 0.83; 5y not above control |
| XAUUSD | TF15 | -80.3% PF 0.82 | -94.0% PF 0.84 | -40.9% PF 0.84 | -63.4% PF 0.81 | FAIL: 3y not positive; 3y PF 0.82; 3y not above control; 5y not positive; 5y PF 0.84; 5y not above control |
| USTEC | TF3 | -64.0% PF 0.78 | -92.9% PF 0.67 | -44.8% PF 0.82 | -72.5% PF 0.76 | FAIL: 3y not positive; 3y PF 0.78; 3y not above control; 5y not positive; 5y PF 0.67; 5y not above control |
| USTEC | NF3 | -96.2% PF 0.69 | -100.0% PF 0.64 | -44.8% PF 0.82 | -72.5% PF 0.76 | FAIL: 3y not positive; 3y PF 0.69; 3y not above control; 5y not positive; 5y PF 0.64; 5y not above control |
| USTEC | TF15 | -90.1% PF 0.70 | -100.0% PF 0.63 | -44.8% PF 0.82 | -72.5% PF 0.76 | FAIL: 3y not positive; 3y PF 0.70; 3y not above control; 5y not positive; 5y PF 0.63; 5y not above control |
| BTCUSD | TF3 | -40.4% PF 0.90 | -89.8% PF 0.76 | -54.7% PF 0.81 | -90.0% PF 0.69 | FAIL: 3y not positive; 3y PF 0.90; 5y not positive; 5y PF 0.76 |
| BTCUSD | NF3 | -97.8% PF 0.76 | -100.0% PF 0.76 | -54.7% PF 0.81 | -90.0% PF 0.69 | FAIL: 3y not positive; 3y PF 0.76; 3y not above control; 5y not positive; 5y PF 0.76; 5y not above control |
| BTCUSD | TF15 | -81.9% PF 0.81 | -100.0% PF 0.76 | -54.7% PF 0.81 | -90.0% PF 0.69 | FAIL: 3y not positive; 3y PF 0.81; 3y not above control; 5y not positive; 5y PF 0.76; 5y not above control |

Passed: none
