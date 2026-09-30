# Order Block 30m — raw native results

Isolated MT5 tester, Exness-MT5Trial16, $10,000, 1% risk (lots rounded up), M30, Model 4 (real ticks from 2026-01, bars-generated before), 150 ms delay; windows end 2026-09-01. No optimization.
Cell = trades · return · PF · win rate · max equity DD · avg win/loss streak (longest win/loss).

## XAUUSD

| Period | R05 — Order block, 0.5R (highest win rate) | R1 — Order block, 1R | R2 — Order block, 2R |
|---|---|---|---|
| 6m | 122 · -0.8% · PF 0.98 · win 63% · DD 9.6% · 2.7/1.6 (9/5) | 112 · -10.0% · PF 0.85 · win 47% · DD 16.0% · 1.9/2.1 (5/7) | 97 · -9.0% · PF 0.88 · win 32% · DD 15.5% · 1.3/2.9 (3/10) |
| 1y | 249 · +11.3% · PF 1.12 · win 68% · DD 10.1% · 3.1/1.5 (14/5) | 236 · +16.0% · PF 1.11 · win 54% · DD 15.3% · 2.2/1.9 (8/7) | 208 · +14.2% · PF 1.09 · win 36% · DD 14.2% · 1.5/2.6 (4/10) |
| 3y | 842 · -48.4% · PF 0.79 · win 62% · DD 57.7% · 2.6/1.6 (14/9) | 799 · -47.3% · PF 0.85 · win 48% · DD 59.3% · 1.9/2.1 (8/9) | 753 · -48.6% · PF 0.87 · win 31% · DD 64.0% · 1.4/3.1 (6/12) |
| 5y | 1460 · -71.7% · PF 0.78 · win 62% · DD 77.9% · 2.5/1.5 (14/9) | 1383 · -69.9% · PF 0.85 · win 47% · DD 77.3% · 1.8/2.0 (8/9) | 1279 · -67.3% · PF 0.88 · win 32% · DD 77.6% · 1.4/3.0 (6/12) |

50%-pullback controls (3y, 5y):

| Period | C05 (control for R05) | C1 (control for R1) | C2 (control for R2) |
|---|---|---|---|
| 3y | 964 · -33.5% · PF 0.88 · win 64% · DD 40.8% · 2.7/1.5 (15/8) | 894 · -58.0% · PF 0.83 · win 46% · DD 60.4% · 1.9/2.2 (9/11) | 768 · -71.8% · PF 0.78 · win 29% · DD 72.4% · 1.4/3.4 (4/11) |
| 5y | 1671 · -49.1% · PF 0.89 · win 65% · DD 56.8% · 2.8/1.5 (15/8) | 1551 · -75.7% · PF 0.85 · win 47% · DD 77.3% · 1.9/2.2 (9/11) | 1319 · -80.0% · PF 0.86 · win 31% · DD 82.0% · 1.5/3.3 (6/11) |

## USTEC

| Period | R05 — Order block, 0.5R (highest win rate) | R1 — Order block, 1R | R2 — Order block, 2R |
|---|---|---|---|
| 6m | 139 · +2.6% · PF 1.05 · win 66% · DD 6.8% · 3.0/1.6 (9/4) | 138 · +8.3% · PF 1.12 · win 52% · DD 8.0% · 2.1/1.9 (6/6) | 128 · +11.3% · PF 1.13 · win 36% · DD 12.3% · 1.6/2.7 (3/13) |
| 1y | 278 · +0.7% · PF 1.01 · win 67% · DD 9.3% · 2.8/1.5 (10/4) | 269 · +10.6% · PF 1.08 · win 52% · DD 8.0% · 2.0/1.8 (6/6) | 250 · +9.2% · PF 1.05 · win 35% · DD 23.7% · 1.5/2.8 (3/15) |
| 3y | 839 · -54.6% · PF 0.72 · win 61% · DD 57.9% · 2.5/1.6 (13/7) | 815 · -65.8% · PF 0.69 · win 44% · DD 70.5% · 1.8/2.2 (7/8) | 752 · -63.0% · PF 0.74 · win 30% · DD 69.2% · 1.5/3.4 (5/15) |
| 5y | 1453 · -83.5% · PF 0.68 · win 59% · DD 84.7% · 2.4/1.7 (13/7) | 1397 · -88.0% · PF 0.71 · win 43% · DD 89.8% · 1.7/2.2 (7/10) | 1281 · -84.6% · PF 0.77 · win 30% · DD 87.3% · 1.4/3.4 (6/15) |

50%-pullback controls (3y, 5y):

| Period | C05 (control for R05) | C1 (control for R1) | C2 (control for R2) |
|---|---|---|---|
| 3y | 948 · -53.9% · PF 0.74 · win 62% · DD 60.3% · 2.7/1.7 (11/9) | 868 · -64.7% · PF 0.75 · win 45% · DD 67.4% · 1.8/2.2 (6/9) | 786 · -81.8% · PF 0.65 · win 27% · DD 82.6% · 1.4/3.7 (5/14) |
| 5y | 1609 · -77.1% · PF 0.76 · win 61% · DD 80.5% · 2.6/1.6 (11/9) | 1474 · -82.0% · PF 0.79 · win 45% · DD 83.9% · 1.8/2.2 (7/9) | 1325 · -91.8% · PF 0.76 · win 28% · DD 93.2% · 1.4/3.5 (5/16) |

## BTCUSD

| Period | R05 — Order block, 0.5R (highest win rate) | R1 — Order block, 1R | R2 — Order block, 2R |
|---|---|---|---|
| 6m | 207 · -6.7% · PF 0.91 · win 65% · DD 14.6% · 3.2/1.7 (12/5) | 197 · +3.6% · PF 1.03 · win 51% · DD 13.9% · 2.0/1.9 (8/6) | 175 · -5.5% · PF 0.95 · win 33% · DD 23.4% · 1.5/3.0 (5/7) |
| 1y | 419 · -25.3% · PF 0.82 · win 63% · DD 29.0% · 2.9/1.7 (12/5) | 398 · -9.3% · PF 0.95 · win 49% · DD 21.9% · 1.9/2.0 (8/6) | 346 · -8.7% · PF 0.96 · win 33% · DD 25.3% · 1.5/3.0 (5/13) |
| 3y | 1279 · -55.8% · PF 0.82 · win 64% · DD 57.5% · 2.9/1.7 (12/6) | 1183 · -51.2% · PF 0.87 · win 48% · DD 57.6% · 2.0/2.2 (8/20) | 1059 · -57.5% · PF 0.86 · win 32% · DD 65.3% · 1.5/3.3 (5/20) |
| 5y | 2181 · -92.8% · PF 0.68 · win 61% · DD 93.2% · 2.6/1.7 (12/9) | 2027 · -91.8% · PF 0.73 · win 46% · DD 93.5% · 1.9/2.3 (10/20) | 1809 · -91.7% · PF 0.76 · win 30% · DD 93.7% · 1.5/3.4 (5/21) |

50%-pullback controls (3y, 5y):

| Period | C05 (control for R05) | C1 (control for R1) | C2 (control for R2) |
|---|---|---|---|
| 3y | 1291 · -48.4% · PF 0.83 · win 64% · DD 58.6% · 2.9/1.6 (12/7) | 1171 · -70.4% · PF 0.79 · win 46% · DD 72.1% · 1.9/2.3 (7/14) | 987 · -27.2% · PF 0.95 · win 33% · DD 39.7% · 1.5/3.1 (7/16) |
| 5y | 2256 · -81.5% · PF 0.80 · win 63% · DD 86.0% · 2.8/1.6 (13/7) | 2027 · -94.0% · PF 0.78 · win 45% · DD 95.1% · 1.9/2.4 (8/14) | 1693 · -75.7% · PF 0.86 · win 32% · DD 81.6% · 1.5/3.3 (7/16) |

## Pre-registered gate (step 4)

Pass = positive on 3y and 5y, PF ≥ 1.15 on 3y and 5y, ≥ 30 trades per window, and higher return than its 50%-pullback control on 3y and 5y.

| Symbol | Variant | 3y | 5y | Control 3y | Control 5y | Result |
|---|---|---|---|---|---|---|
| XAUUSD | R05 | -48.4% PF 0.79 | -71.7% PF 0.78 | -33.5% PF 0.88 | -49.1% PF 0.89 | FAIL: 3y not positive; 3y PF 0.79; 3y not above control; 5y not positive; 5y PF 0.78; 5y not above control |
| XAUUSD | R1 | -47.3% PF 0.85 | -69.9% PF 0.85 | -58.0% PF 0.83 | -75.7% PF 0.85 | FAIL: 3y not positive; 3y PF 0.85; 5y not positive; 5y PF 0.85 |
| XAUUSD | R2 | -48.6% PF 0.87 | -67.3% PF 0.88 | -71.8% PF 0.78 | -80.0% PF 0.86 | FAIL: 3y not positive; 3y PF 0.87; 5y not positive; 5y PF 0.88 |
| USTEC | R05 | -54.6% PF 0.72 | -83.5% PF 0.68 | -53.9% PF 0.74 | -77.1% PF 0.76 | FAIL: 3y not positive; 3y PF 0.72; 3y not above control; 5y not positive; 5y PF 0.68; 5y not above control |
| USTEC | R1 | -65.8% PF 0.69 | -88.0% PF 0.71 | -64.7% PF 0.75 | -82.0% PF 0.79 | FAIL: 3y not positive; 3y PF 0.69; 3y not above control; 5y not positive; 5y PF 0.71; 5y not above control |
| USTEC | R2 | -63.0% PF 0.74 | -84.6% PF 0.77 | -81.8% PF 0.65 | -91.8% PF 0.76 | FAIL: 3y not positive; 3y PF 0.74; 5y not positive; 5y PF 0.77 |
| BTCUSD | R05 | -55.8% PF 0.82 | -92.8% PF 0.68 | -48.4% PF 0.83 | -81.5% PF 0.80 | FAIL: 3y not positive; 3y PF 0.82; 3y not above control; 5y not positive; 5y PF 0.68; 5y not above control |
| BTCUSD | R1 | -51.2% PF 0.87 | -91.8% PF 0.73 | -70.4% PF 0.79 | -94.0% PF 0.78 | FAIL: 3y not positive; 3y PF 0.87; 5y not positive; 5y PF 0.73 |
| BTCUSD | R2 | -57.5% PF 0.86 | -91.7% PF 0.76 | -27.2% PF 0.95 | -75.7% PF 0.86 | FAIL: 3y not positive; 3y PF 0.86; 3y not above control; 5y not positive; 5y PF 0.76; 5y not above control |

Passed: none
