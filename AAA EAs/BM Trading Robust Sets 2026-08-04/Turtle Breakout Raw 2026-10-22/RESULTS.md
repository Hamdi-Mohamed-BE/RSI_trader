# Turtle breakout portfolio (US500, USTEC, XAU, XAG, BTC) — raw results (generated)

Native MT5 Model 4, 150 ms, $100k, 2% of high-water-mark risk per trade. A trade = one signal (day-trading re-entries belong to the same trade).
Mean R = trade net / (2% × HWM at entry). Sharpe from the equity at each 17:00 NY rollover (√365). Consistency = profitable months.
Drawdowns are MT5 "relative" (largest % from a peak). Per-year DD uses the rollover equity samples. / day = per calendar day (Bitcoin trades 7 days).
Return before swap is a diagnostic: swap added back, without re-compounding.

## Main versions — separate native windows

| Version | Window | Return | CAGR | Sharpe | Equity DD (native, max %) | Balance DD (native, max %) | Trades | / month | / day | PF | Win % | Mean R | Win streak avg (max) | Loss streak avg (max) | Consistency | Swap $ | Return before swap | Positions > 23 h |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---:|---:|---:|---:|
| **HOLD** | 6m | +8.31% | 17.27% | 0.8 | 11.83% | 3.58% | 15 | 2.49 | 0.082 | 1.72 | 46.7 | 0.282 | 1.75 (3) | 1.6 (2) | 42.9% | -3,935 | +12.25% | 15 |
| **HOLD** | 1y | +19.16% | 19.17% | 0.69 | 33.75% | 15.81% | 32 | 2.67 | 0.087 | 1.45 | 31.2 | 0.264 | 1.67 (3) | 3.14 (8) | 46.2% | -8,656 | +27.82% | 32 |
| **HOLD** | 3y | +153.31% | 36.31% | 1.17 | 34.68% | 15.53% | 107 | 2.97 | 0.097 | 1.84 | 45.8 | 0.431 | 2.13 (6) | 2.42 (8) | 56.8% | -69,024 | +222.33% | 107 |
| **HOLD** | 5y | +111.59% | 16.17% | 0.64 | 46.9% | 50.24% | 177 | 2.95 | 0.096 | 1.47 | 38.4 | 0.208 | 2.0 (6) | 3.11 (10) | 49.2% | -89,399 | +200.99% | 177 |
| **DAY** | 6m | +2.45% | 4.95% | 0.32 | 14.4% | 13.38% | 15 | 2.49 | 0.082 | 1.18 | 40.0 | 0.107 | 1.2 (2) | 1.5 (2) | 42.9% | -2,477 | +4.93% | 3 |
| **DAY** | 1y | +6.97% | 6.97% | 0.38 | 32.38% | 30.17% | 32 | 2.67 | 0.087 | 1.17 | 28.1 | 0.083 | 1.29 (2) | 2.88 (8) | 38.5% | -4,927 | +11.90% | 9 |
| **DAY** | 3y | +53.44% | 15.34% | 0.61 | 34.99% | 32.65% | 107 | 2.97 | 0.097 | 1.36 | 37.4 | 0.191 | 1.48 (5) | 2.39 (8) | 45.9% | -36,371 | +89.81% | 46 |
| **DAY** | 5y | +0.53% | 0.11% | 0.19 | 57.94% | 56.81% | 177 | 2.95 | 0.096 | 1.0 | 31.6 | -0.003 | 1.6 (5) | 3.36 (23) | 37.7% | -48,542 | +49.07% | 71 |

## Per asset — 5 years

| Version | Asset | Trades | Positions | Net $ | PF | Win % | Mean R | Swap $ |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| HOLD | US500 | 34 | 34 | -6,320 | 0.86 | 47.1 | 0.005 | -28,772 |
| HOLD | USTEC | 37 | 37 | -1,955 | 0.96 | 40.5 | -0.056 | -23,939 |
| HOLD | XAUUSD | 32 | 32 | +32,160 | 1.77 | 37.5 | 0.345 | -14,466 |
| HOLD | XAGUSD | 34 | 34 | +27,841 | 1.56 | 35.3 | 0.166 | -8,470 |
| HOLD | BTCUSD | 40 | 40 | +59,860 | 2.22 | 32.5 | 0.549 | -13,751 |
| DAY | US500 | 34 | 656 | -7,273 | 0.77 | 44.1 | -0.092 | -13,606 |
| DAY | USTEC | 37 | 626 | -6,084 | 0.83 | 35.1 | -0.096 | -11,473 |
| DAY | XAUUSD | 32 | 514 | +9,623 | 1.27 | 37.5 | 0.151 | -10,465 |
| DAY | XAGUSD | 34 | 515 | -26,396 | 0.51 | 17.6 | -0.374 | -5,994 |
| DAY | BTCUSD | 40 | 554 | +30,664 | 1.73 | 25.0 | 0.348 | -7,004 |

## Per calendar year — 5-year runs

| Version | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|
| HOLD | -9.9% (DD 13%, PF 0.17) | -35.1% (DD 41%, PF 0.13) | +69.1% (DD 23%, PF 2.39) | +32.6% (DD 16%, PF 1.98) | +38.0% (DD 15%, PF 1.7) | +16.9% (DD 31%, PF 1.77) |
| DAY | -12.2% (DD 14%, PF 0.07) | -48.3% (DD 50%, PF 0.08) | +50.1% (DD 32%, PF 1.75) | +12.0% (DD 22%, PF 1.36) | +18.7% (DD 22%, PF 1.25) | +11.0% (DD 34%, PF 1.5) |

## Controls and sensitivities — 5 years, Model 4

| Version | Window | Return | CAGR | Sharpe | Equity DD (native, max %) | Balance DD (native, max %) | Trades | / month | / day | PF | Win % | Mean R | Win streak avg (max) | Loss streak avg (max) | Consistency | Swap $ | Return before swap | Positions > 23 h |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---:|---:|---:|---:|
| RND_DAY1 | 5y | +7.99% | 1.55% | 0.18 | 31.05% | 31.48% | 125 | 2.08 | 0.068 | 1.07 | 27.2 | 0.033 | 1.36 (4) | 3.5 (11) | 52.5% | -28,854 | +36.84% | 53 |
| RND_DAY2 | 5y | -13.88% | -2.94% | -0.03 | 48.69% | 48.4% | 136 | 2.27 | 0.074 | 0.88 | 22.8 | -0.05 | 1.35 (4) | 4.38 (16) | 37.7% | -26,350 | +12.47% | 47 |
| RND_DAY3 | 5y | -4.30% | -0.88% | 0.06 | 31.55% | 29.43% | 127 | 2.12 | 0.069 | 0.96 | 29.9 | -0.008 | 1.41 (4) | 3.42 (15) | 37.7% | -24,758 | +20.46% | 34 |
| RND_HOLD1 | 5y | +57.08% | 9.45% | 0.58 | 29.49% | 11.41% | 131 | 2.18 | 0.071 | 1.46 | 35.1 | 0.176 | 1.59 (4) | 2.83 (9) | 47.5% | -51,294 | +108.37% | 112 |
| RND_HOLD2 | 5y | +23.34% | 4.29% | 0.31 | 32.47% | 23.65% | 145 | 2.42 | 0.079 | 1.18 | 29.7 | 0.08 | 1.59 (4) | 3.64 (15) | 49.2% | -49,925 | +73.27% | 123 |
| RND_HOLD3 | 5y | +27.11% | 4.92% | 0.35 | 27.43% | 23.64% | 136 | 2.27 | 0.074 | 1.22 | 25.7 | 0.087 | 1.21 (3) | 3.61 (17) | 45.9% | -40,878 | +67.99% | 114 |
| S55 | 5y | -3.83% | -0.78% | 0.16 | 51.85% | 50.72% | 80 | 1.33 | 0.044 | 0.97 | 28.8 | -0.017 | 1.92 (5) | 4.38 (18) | 44.3% | -47,053 | +43.22% | 68 |
| SATR3 | 5y | -6.79% | -1.4% | 0.05 | 41.92% | 40.53% | 173 | 2.88 | 0.094 | 0.95 | 32.4 | -0.02 | 1.6 (5) | 3.25 (22) | 36.1% | -32,683 | +25.89% | 73 |
| SR1 | 5y | -0.11% | -0.02% | 0.08 | 29.21% | 28.38% | 177 | 2.95 | 0.096 | 1.0 | 31.6 | -0.003 | 1.6 (5) | 3.36 (23) | 39.3% | -23,869 | +23.76% | 71 |

## Raw gate

| Version | Positive 3y & 5y | PF ≥ 1.15 3y & 5y | ≥ 30 trades | Mean R > random mean | Best day / trade | Verdict |
|---|---|---|---|---|---|---|
| HOLD | yes | yes | yes | yes (0.208 vs 0.114) | yes | **PASS** |
| DAY | yes | **no** | yes | yes (-0.003 vs -0.008) | **no** | **FAIL** |

## Best-day dependence (positions)

- HOLD|3y: total $+153,315; without best day $+108,509; without best trade $+108,509; without 5 best days $-4,500 → PASS
- HOLD|5y: total $+111,586; without best day $+73,180; without best trade $+73,180; without 5 best days $-22,012 → PASS
- DAY|3y: total $+53,435; without best day $+42,643; without best trade $+46,554; without 5 best days $+7,222 → PASS
- DAY|5y: total $+533; without best day $-6,721; without best trade $-4,284; without 5 best days $-31,002 → FAIL
