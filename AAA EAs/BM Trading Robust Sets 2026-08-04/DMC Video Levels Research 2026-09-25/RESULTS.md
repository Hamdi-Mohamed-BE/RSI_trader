# DMC video-levels study — side-by-side results

Native MT5 (isolated tester, Exness-MT5Trial16), $10,000, 1% risk, H1, Model 4 (real ticks from 2026-01, bars-generated before), 150 ms delay. Windows end 2026-09-01 (same as the website).
BASE = current production rules. VIDEO = first test of the level only + take profit at the first untested level in the trade direction (capped at the SET R, skip if < 0.25R). DD = max equity drawdown.
UNTESTED = first test of the level only (added after the 5y ablation; see REPORT.md on selection bias).
Off-native symbols for CUR/FRX use a 1.5×H1-ATR stop instead of the fixed XAU dollar stop.

## CUR — DMC Current XAU (Asia, fixed 22.5 stop, 3R, Dynamic 50-20)

### XAUUSD (native SET)

| Period | BASE (current) | VIDEO (untested + next-level target) | UNTESTED only | Δ VIDEO | Δ UNTESTED |
|---|---|---|---|---:|---:|
| 6m | +6.72% · PF 1.17 · n 58 · win 41% · DD 10.64% | +8.77% · PF 3.51 · n 11 · win 73% · DD 4.37% | +3.66% · PF 1.64 · n 11 · win 55% · DD 5.05% | +2.05 pp | -3.06 pp |
| 1y | +14.87% · PF 1.17 · n 116 · win 41% · DD 11.42% | +0.54% · PF 1.04 · n 21 · win 48% · DD 11.04% | -1.42% · PF 0.90 · n 21 · win 38% · DD 8.60% | -14.33 pp | -16.29 pp |
| 3y | +55.70% · PF 1.26 · n 250 · win 41% · DD 14.51% | +0.66% · PF 1.02 · n 62 · win 60% · DD 18.84% | +23.28% · PF 1.48 · n 66 · win 45% · DD 13.10% | -55.04 pp | -32.42 pp |
| 5y | +11.96% · PF 1.05 · n 345 · win 38% · DD 36.96% | -10.49% · PF 0.76 · n 96 · win 57% · DD 20.65% | +11.60% · PF 1.18 · n 97 · win 40% · DD 13.36% | -22.45 pp | -0.36 pp |

### USTEC (portable)

| Period | BASE (current) | VIDEO (untested + next-level target) | UNTESTED only | Δ VIDEO | Δ UNTESTED |
|---|---|---|---|---:|---:|
| 6m | -8.42% · PF 0.77 · n 56 · win 32% · DD 19.45% | -0.21% · PF 0.97 · n 12 · win 50% · DD 3.62% | +2.79% · PF 1.38 · n 12 · win 42% · DD 3.82% | +8.21 pp | +11.21 pp |
| 1y | -18.83% · PF 0.74 · n 116 · win 32% · DD 27.71% | -3.22% · PF 0.76 · n 24 · win 46% · DD 9.78% | -5.76% · PF 0.66 · n 25 · win 32% · DD 10.45% | +15.61 pp | +13.07 pp |
| 3y | -34.29% · PF 0.86 · n 403 · win 33% · DD 47.59% | -15.53% · PF 0.66 · n 85 · win 44% · DD 22.64% | -18.52% · PF 0.65 · n 87 · win 33% · DD 25.51% | +18.76 pp | +15.77 pp |
| 5y | -61.28% · PF 0.80 · n 681 · win 32% · DD 64.83% | -15.69% · PF 0.80 · n 141 · win 45% · DD 25.04% | -24.03% · PF 0.73 · n 145 · win 34% · DD 32.23% | +45.59 pp | +37.25 pp |

### BTCUSD (portable)

| Period | BASE (current) | VIDEO (untested + next-level target) | UNTESTED only | Δ VIDEO | Δ UNTESTED |
|---|---|---|---|---:|---:|
| 6m | -6.49% · PF 0.90 · n 97 · win 32% · DD 20.18% | -3.64% · PF 0.68 · n 20 · win 45% · DD 7.59% | -1.40% · PF 0.90 · n 20 · win 30% · DD 11.40% | +2.85 pp | +5.09 pp |
| 1y | -16.32% · PF 0.86 · n 184 · win 33% · DD 26.53% | -2.27% · PF 0.87 · n 35 · win 51% · DD 7.61% | -6.88% · PF 0.72 · n 34 · win 29% · DD 14.46% | +14.05 pp | +9.44 pp |
| 3y | -19.04% · PF 0.95 · n 521 · win 36% · DD 48.65% | +3.77% · PF 1.07 · n 97 · win 51% · DD 13.58% | +3.90% · PF 1.05 · n 103 · win 37% · DD 22.81% | +22.81 pp | +22.94 pp |
| 5y | -47.12% · PF 0.89 · n 845 · win 35% · DD 56.36% | +2.89% · PF 1.03 · n 173 · win 49% · DD 13.35% | -9.40% · PF 0.92 · n 176 · win 35% · DD 26.75% | +50.01 pp | +37.72 pp |

## FRX — DMC Fresh Reaction XAU (Asia, fixed 30 stop, 3R, one prior touch, W1/MN1 0.25 ATR, Dynamic 50-20)

### XAUUSD (native SET)

| Period | BASE (current) | VIDEO (untested + next-level target) | UNTESTED only | Δ VIDEO | Δ UNTESTED |
|---|---|---|---|---:|---:|
| 6m | +0.05% · PF 1.00 · n 15 · win 33% · DD 6.44% | +7.45% · PF 3.04 · n 10 · win 70% · DD 4.58% | +6.04% · PF 1.99 · n 10 · win 50% · DD 5.25% | +7.40 pp | +5.99 pp |
| 1y | +9.60% · PF 1.99 · n 15 · win 47% · DD 3.99% | +9.82% · PF 8.69 · n 8 · win 88% · DD 2.20% | +8.41% · PF 3.25 · n 8 · win 62% · DD 3.43% | +0.22 pp | -1.19 pp |
| 3y | +48.28% · PF 2.46 · n 55 · win 60% · DD 5.40% | +18.19% · PF 4.67 · n 35 · win 89% · DD 2.80% | +48.21% · PF 3.75 · n 37 · win 68% · DD 3.98% | -30.09 pp | -0.07 pp |
| 5y | +32.86% · PF 1.62 · n 85 · win 49% · DD 19.49% | +5.52% · PF 1.28 · n 55 · win 71% · DD 13.09% | +32.45% · PF 1.89 · n 59 · win 51% · DD 13.58% | -27.34 pp | -0.41 pp |

### USTEC (portable)

| Period | BASE (current) | VIDEO (untested + next-level target) | UNTESTED only | Δ VIDEO | Δ UNTESTED |
|---|---|---|---|---:|---:|
| 6m | +3.96% · PF 1.62 · n 11 · win 45% · DD 4.36% | +1.88% · PF 1.45 · n 10 · win 60% · DD 3.62% | +4.93% · PF 1.92 · n 10 · win 50% · DD 3.80% | -2.08 pp | +0.97 pp |
| 1y | -5.62% · PF 0.66 · n 25 · win 32% · DD 10.46% | -3.70% · PF 0.63 · n 17 · win 41% · DD 8.13% | -2.91% · PF 0.78 · n 19 · win 32% · DD 9.09% | +1.92 pp | +2.71 pp |
| 3y | -13.54% · PF 0.75 · n 88 · win 34% · DD 19.47% | -9.65% · PF 0.71 · n 60 · win 43% · DD 19.36% | -7.14% · PF 0.82 · n 63 · win 37% · DD 17.65% | +3.89 pp | +6.40 pp |
| 5y | -25.21% · PF 0.70 · n 144 · win 33% · DD 32.07% | -11.85% · PF 0.79 · n 100 · win 44% · DD 19.54% | -19.11% · PF 0.69 · n 105 · win 35% · DD 27.31% | +13.36 pp | +6.10 pp |

### BTCUSD (portable)

| Period | BASE (current) | VIDEO (untested + next-level target) | UNTESTED only | Δ VIDEO | Δ UNTESTED |
|---|---|---|---|---:|---:|
| 6m | -9.01% · PF 0.32 · n 16 · win 19% · DD 11.47% | -1.94% · PF 0.69 · n 11 · win 45% · DD 4.57% | -4.12% · PF 0.51 · n 11 · win 27% · DD 7.55% | +7.07 pp | +4.89 pp |
| 1y | -8.30% · PF 0.67 · n 35 · win 31% · DD 13.64% | -0.74% · PF 0.94 · n 22 · win 50% · DD 4.59% | -7.97% · PF 0.51 · n 22 · win 27% · DD 10.92% | +7.56 pp | +0.33 pp |
| 3y | -13.12% · PF 0.83 · n 109 · win 34% · DD 22.30% | +4.26% · PF 1.11 · n 65 · win 49% · DD 10.21% | -2.09% · PF 0.96 · n 69 · win 36% · DD 18.51% | +17.38 pp | +11.03 pp |
| 5y | -33.64% · PF 0.71 · n 192 · win 31% · DD 35.60% | -8.18% · PF 0.87 · n 113 · win 46% · DD 14.60% | -15.74% · PF 0.79 · n 116 · win 32% · DD 20.82% | +25.46 pp | +17.90 pp |

## FRU — DMC Fresh Reaction US100 (New York, 1.5 ATR stop, 2R, one prior touch, W1/MN1 0.25 ATR, Dynamic 50-20)

### USTEC (native SET)

| Period | BASE (current) | VIDEO (untested + next-level target) | UNTESTED only | Δ VIDEO | Δ UNTESTED |
|---|---|---|---|---:|---:|
| 6m | +1.29% · PF 1.42 · n 6 · win 50% · DD 2.45% | +0.18% · PF 1.09 · n 5 · win 60% · DD 2.13% | -0.69% · PF 0.77 · n 5 · win 40% · DD 2.46% | -1.11 pp | -1.98 pp |
| 1y | +3.75% · PF 1.88 · n 12 · win 67% · DD 2.91% | +2.86% · PF 2.35 · n 8 · win 75% · DD 2.31% | +2.36% · PF 1.75 · n 9 · win 67% · DD 2.44% | -0.89 pp | -1.39 pp |
| 3y | +18.25% · PF 2.00 · n 46 · win 65% · DD 4.30% | +15.04% · PF 2.66 · n 31 · win 74% · DD 2.30% | +16.51% · PF 2.21 · n 35 · win 66% · DD 3.81% | -3.21 pp | -1.74 pp |
| 5y | +12.53% · PF 1.33 · n 83 · win 57% · DD 8.28% | +10.89% · PF 1.61 · n 46 · win 63% · DD 4.71% | +11.93% · PF 1.51 · n 53 · win 58% · DD 6.87% | -1.64 pp | -0.60 pp |

### XAUUSD (portable)

| Period | BASE (current) | VIDEO (untested + next-level target) | UNTESTED only | Δ VIDEO | Δ UNTESTED |
|---|---|---|---|---:|---:|
| 6m | -2.02% · PF 0.61 · n 6 · win 33% · DD 4.07% | -1.27% · PF 0.69 · n 5 · win 40% · DD 3.00% | -1.18% · PF 0.71 · n 5 · win 40% · DD 3.00% | +0.75 pp | +0.84 pp |
| 1y | -0.98% · PF 0.88 · n 11 · win 36% · DD 5.59% | -1.24% · PF 0.75 · n 7 · win 43% · DD 3.33% | -0.00% · PF 1.00 · n 7 · win 43% · DD 2.92% | -0.26 pp | +0.98 pp |
| 3y | -3.33% · PF 0.81 · n 26 · win 38% · DD 10.09% | -5.42% · PF 0.54 · n 18 · win 39% · DD 6.85% | -2.92% · PF 0.80 · n 20 · win 35% · DD 7.55% | -2.09 pp | +0.41 pp |
| 5y | -15.00% · PF 0.59 · n 58 · win 38% · DD 20.07% | -11.95% · PF 0.52 · n 39 · win 38% · DD 14.08% | -12.85% · PF 0.56 · n 44 · win 34% · DD 16.47% | +3.05 pp | +2.15 pp |

### BTCUSD (portable)

| Period | BASE (current) | VIDEO (untested + next-level target) | UNTESTED only | Δ VIDEO | Δ UNTESTED |
|---|---|---|---|---:|---:|
| 6m | +0.36% · PF 41.57 · n 1 · win 100% · DD 1.14% | +0.36% · PF 41.57 · n 1 · win 100% · DD 1.14% | +0.36% · PF 41.57 · n 1 · win 100% · DD 1.14% | +0.00 pp | +0.00 pp |
| 1y | +3.07% · PF 2.35 · n 7 · win 71% · DD 3.45% | +1.25% · PF 2.13 · n 3 · win 67% · DD 2.14% | +1.25% · PF 2.13 · n 3 · win 67% · DD 2.14% | -1.82 pp | -1.82 pp |
| 3y | +1.13% · PF 1.06 · n 36 · win 50% · DD 9.02% | -1.80% · PF 0.76 · n 12 · win 42% · DD 5.30% | -2.18% · PF 0.71 · n 12 · win 42% · DD 5.64% | -2.93 pp | -3.31 pp |
| 5y | -3.94% · PF 0.90 · n 70 · win 47% · DD 10.83% | -0.12% · PF 0.99 · n 27 · win 56% · DD 5.38% | +0.74% · PF 1.06 · n 27 · win 56% · DD 5.68% | +3.82 pp | +4.68 pp |

Return beat BASE: VIDEO 21/36 cells, UNTESTED 22/36 cells.

## 5-year ablation (each video rule alone)

| Config | Symbol | BASE | UNTESTED | TARGET | VIDEO |
|---|---|---|---|---|---|
| CUR | XAUUSD | +12.0% PF 1.05 n=345 DD 37.0% | +11.6% PF 1.18 n=97 DD 13.4% | -19.4% PF 0.90 n=488 DD 28.2% | -10.5% PF 0.76 n=96 DD 20.6% |
| CUR | USTEC | -61.3% PF 0.80 n=681 DD 64.8% | -24.0% PF 0.73 n=145 DD 32.2% | -41.6% PF 0.85 n=695 DD 49.6% | -15.7% PF 0.80 n=141 DD 25.0% |
| CUR | BTCUSD | -47.1% PF 0.89 n=845 DD 56.4% | -9.4% PF 0.92 n=176 DD 26.8% | -41.3% PF 0.90 n=919 DD 50.7% | +2.9% PF 1.03 n=173 DD 13.3% |
| FRX | XAUUSD | +32.9% PF 1.62 n=85 DD 19.5% | +32.5% PF 1.89 n=59 DD 13.6% | +3.0% PF 1.07 n=109 DD 17.4% | +5.5% PF 1.28 n=55 DD 13.1% |
| FRX | USTEC | -25.2% PF 0.70 n=144 DD 32.1% | -19.1% PF 0.69 n=105 DD 27.3% | -22.4% PF 0.71 n=141 DD 29.6% | -11.8% PF 0.79 n=100 DD 19.5% |
| FRX | BTCUSD | -33.6% PF 0.71 n=192 DD 35.6% | -15.7% PF 0.79 n=116 DD 20.8% | -28.8% PF 0.71 n=191 DD 33.5% | -8.2% PF 0.87 n=113 DD 14.6% |
| FRU | USTEC | +12.5% PF 1.33 n=83 DD 8.3% | +11.9% PF 1.51 n=53 DD 6.9% | +11.2% PF 1.34 n=76 DD 6.8% | +10.9% PF 1.61 n=46 DD 4.7% |
| FRU | XAUUSD | -15.0% PF 0.59 n=58 DD 20.1% | -12.8% PF 0.56 n=44 DD 16.5% | -14.1% PF 0.56 n=53 DD 16.9% | -11.9% PF 0.52 n=39 DD 14.1% |
| FRU | BTCUSD | -3.9% PF 0.90 n=70 DD 10.8% | +0.7% PF 1.06 n=27 DD 5.7% | -4.5% PF 0.88 n=70 DD 11.4% | -0.1% PF 0.99 n=27 DD 5.4% |
