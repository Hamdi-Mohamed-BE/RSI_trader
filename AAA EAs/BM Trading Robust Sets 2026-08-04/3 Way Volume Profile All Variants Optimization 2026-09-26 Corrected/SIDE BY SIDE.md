# 3 Way Volume Profile — all 32 side by side

Confirmed 32/32 combinations. As of 2026-09-26T17:20:16.079282+00:00.

**Comparison: 26 Sep 2025–25 Sep 2026, $10,000 starting balance per independent test, target 1% equity risk.**
These are independent strategy tests, NOT a portfolio running all EAs concurrently. Native MT5 Model 4, historical spread/costs and configured 150 ms execution delay. Earlier ticks can be generated; no claim of full real-tick coverage.

Parameters selected on older development/validation data, never on this comparison year. The last-year raw study was already observed, so this is not pristine out-of-sample evidence. No settings have been deployed. Optimized means selected by the search, not necessarily improved or suitable for trading.

Whole-position win rate/PF/trade count aggregate partial exits. Equity DD is maximum RELATIVE equity drawdown. Risk uses the original lot rounding UP; the effective risk can exceed 1%.

## USTEC — raw → optimized

| Setup | Return | Net USD | PF | Win rate | Positions | Equity DD | Longest W/L streak | Older validation |
|---|---:|---:|---:|---:|---:|---:|---|---|
| POC bounce | +6.84% → +2.12% | $684.04 → $212.50 | 1.23 → 1.09 | 39.1% → 41.5% | 46 → 41 | 7.55% → 6.61% | 2/6 → 5/6 | FAIL |
| VA reversal | -11.71% → +7.91% | $-1,171.06 → $790.86 | 0.89 → 1.09 | 32.5% → 41.8% | 151 → 141 | 23.83% → 11.77% | 4/11 → 7/8 | FAIL |
| VA breakout | -17.06% → -2.10% | $-1,705.85 → $-210.22 | 0.78 → 0.97 | 29.1% → 33.9% | 110 → 109 | 20.95% → 18.84% | 3/14 → 3/9 | FAIL |
| 3 Way combined | -6.29% → -26.47% | $-628.86 → $-2,647.40 | 0.96 → 0.76 | 33.8% → 33.0% | 213 → 206 | 16.68% → 33.65% | 5/11 → 4/9 | FAIL |

## XAUUSD — raw → optimized

| Setup | Return | Net USD | PF | Win rate | Positions | Equity DD | Longest W/L streak | Older validation |
|---|---:|---:|---:|---:|---:|---:|---|---|
| POC bounce | -12.34% → -6.57% | $-1,233.81 → $-656.68 | 0.59 → 0.76 | 23.1% → 38.5% | 39 → 39 | 16.67% → 17.25% | 3/12 → 3/6 | PASS |
| VA reversal | +9.07% → -2.56% | $906.67 → $-255.98 | 1.08 → 0.96 | 35.6% → 46.9% | 160 → 130 | 27.29% → 12.76% | 4/9 → 5/8 | FAIL |
| VA breakout | +19.82% → +15.36% | $1,981.68 → $1,535.99 | 1.30 → 1.23 | 41.0% → 39.8% | 78 → 93 | 13.43% → 13.10% | 7/7 → 3/9 | PASS |
| 3 Way combined | +27.87% → -1.81% | $2,787.41 → $-180.81 | 1.16 → 0.98 | 37.3% → 45.7% | 217 → 151 | 23.64% → 22.72% | 6/11 → 4/13 | FAIL |

## XAGUSD — raw → optimized

| Setup | Return | Net USD | PF | Win rate | Positions | Equity DD | Longest W/L streak | Older validation |
|---|---:|---:|---:|---:|---:|---:|---|---|
| POC bounce | +5.32% → +3.41% | $531.95 → $340.83 | 1.26 → 1.22 | 41.4% → 35.7% | 29 → 14 | 5.51% → 10.91% | 2/5 → 2/6 | FAIL |
| VA reversal | -22.64% → -2.55% | $-2,264.23 → $-254.74 | 0.79 → 0.90 | 27.0% → 42.9% | 122 → 28 | 27.98% → 14.99% | 3/10 → 2/5 | FAIL |
| VA breakout | -1.99% → +8.59% | $-198.84 → $858.68 | 0.98 → 1.42 | 32.6% → 48.4% | 92 → 31 | 20.56% → 7.15% | 3/10 → 4/5 | FAIL |
| 3 Way combined | +0.47% → +20.99% | $46.99 → $2,098.81 | 1.00 → 1.79 | 33.3% → 40.7% | 147 → 27 | 19.88% → 9.42% | 3/9 → 3/4 | FAIL |

## BTCUSD — raw → optimized

| Setup | Return | Net USD | PF | Win rate | Positions | Equity DD | Longest W/L streak | Older validation |
|---|---:|---:|---:|---:|---:|---:|---|---|
| POC bounce | -0.63% → +3.78% | $-62.92 → $378.39 | 0.99 → 1.29 | 34.9% → 52.0% | 63 → 25 | 11.33% → 5.50% | 3/6 → 3/4 | PASS |
| VA reversal | +50.50% → -0.70% | $5,050.25 → $-69.71 | 1.29 → 0.97 | 40.9% → 30.8% | 208 → 39 | 11.15% → 16.63% | 5/10 → 3/8 | FAIL |
| VA breakout | +22.25% → -4.17% | $2,225.27 → $-416.69 | 1.20 → 0.90 | 38.9% → 42.1% | 144 → 76 | 13.49% → 14.79% | 4/8 → 3/8 | FAIL |
| 3 Way combined | +34.29% → -0.37% | $3,428.86 → $-37.15 | 1.14 → 0.99 | 37.6% → 8.7% | 287 → 46 | 19.11% → 19.73% | 6/14 → 1/27 | FAIL |

## ETHUSD — raw → optimized

| Setup | Return | Net USD | PF | Win rate | Positions | Equity DD | Longest W/L streak | Older validation |
|---|---:|---:|---:|---:|---:|---:|---|---|
| POC bounce | +0.94% → -8.03% | $93.99 → $-802.79 | 1.03 → 0.67 | 36.5% → 22.6% | 52 → 31 | 11.33% → 15.37% | 3/10 → 3/10 | FAIL |
| VA reversal | +4.27% → -17.82% | $427.42 → $-1,782.27 | 1.03 → 0.83 | 35.8% → 34.9% | 226 → 172 | 22.90% → 26.71% | 4/13 → 5/9 | FAIL |
| VA breakout | +1.26% → -6.76% | $125.98 → $-675.80 | 1.01 → 0.63 | 34.8% → 28.0% | 132 → 25 | 22.93% → 12.39% | 4/10 → 1/6 | FAIL |
| 3 Way combined | +17.68% → -7.40% | $1,768.13 → $-739.60 | 1.09 → 0.92 | 37.0% → 32.5% | 276 → 123 | 20.04% → 24.18% | 6/16 → 4/14 | FAIL |

## EURUSD — raw → optimized

| Setup | Return | Net USD | PF | Win rate | Positions | Equity DD | Longest W/L streak | Older validation |
|---|---:|---:|---:|---:|---:|---:|---|---|
| POC bounce | -0.12% → -10.68% | $-12.17 → $-1,067.60 | 1.00 → 0.57 | 31.4% → 7.4% | 35 → 27 | 11.07% → 18.18% | 4/9 → 1/12 | FAIL |
| VA reversal | +10.69% → -19.16% | $1,068.78 → $-1,916.06 | 1.10 → 0.57 | 37.3% → 36.7% | 158 → 79 | 18.40% → 19.73% | 6/12 → 5/13 | FAIL |
| VA breakout | -15.22% → +8.18% | $-1,521.73 → $817.78 | 0.81 → 1.56 | 30.8% → 17.6% | 104 → 34 | 24.54% → 9.52% | 2/13 → 2/11 | FAIL |
| 3 Way combined | -0.50% → -6.74% | $-50.43 → $-674.26 | 1.00 → 0.67 | 35.5% → 25.6% | 172 → 39 | 22.13% → 10.70% | 3/14 → 2/8 | PASS |

## USDJPY — raw → optimized

| Setup | Return | Net USD | PF | Win rate | Positions | Equity DD | Longest W/L streak | Older validation |
|---|---:|---:|---:|---:|---:|---:|---|---|
| POC bounce | -12.17% → -7.28% | $-1,217.46 → $-727.82 | 0.51 → 0.59 | 21.9% → 16.7% | 32 → 24 | 12.63% → 13.81% | 3/6 → 1/7 | FAIL |
| VA reversal | +12.83% → -4.29% | $1,282.60 → $-428.75 | 1.12 → 0.73 | 37.7% → 58.3% | 138 → 48 | 20.24% → 9.45% | 5/13 → 5/4 | PASS |
| VA breakout | +17.63% → -16.85% | $1,762.88 → $-1,684.56 | 1.28 → 0.76 | 39.3% → 45.7% | 84 → 140 | 12.05% → 21.94% | 4/5 → 7/11 | FAIL |
| 3 Way combined | +39.74% → +5.51% | $3,974.39 → $550.64 | 1.29 → 1.07 | 41.5% → 21.7% | 164 → 143 | 16.57% → 12.80% | 7/9 → 3/16 | FAIL |

## GBPJPY — raw → optimized

| Setup | Return | Net USD | PF | Win rate | Positions | Equity DD | Longest W/L streak | Older validation |
|---|---:|---:|---:|---:|---:|---:|---|---|
| POC bounce | +2.18% → +4.18% | $217.65 → $418.49 | 1.09 → 1.23 | 38.2% → 40.7% | 34 → 27 | 7.88% → 4.27% | 5/6 → 3/4 | FAIL |
| VA reversal | -33.44% → -7.25% | $-3,344.19 → $-725.23 | 0.69 → 0.71 | 27.6% → 26.5% | 174 → 34 | 35.77% → 12.67% | 4/11 → 2/8 | FAIL |
| VA breakout | +4.92% → -1.24% | $492.34 → $-123.93 | 1.12 → 0.89 | 38.3% → 10.5% | 60 → 38 | 6.80% → 7.65% | 3/5 → 1/18 | FAIL |
| 3 Way combined | -6.25% → -17.61% | $-624.96 → $-1,761.12 | 0.93 → 0.84 | 33.8% → 31.2% | 130 → 154 | 14.00% → 23.48% | 6/7 → 4/10 | FAIL |

## Older validation and search depth

Validation window: 26 Sep 2024–25 Sep 2025. Pass requires positive P/L, whole-position PF ≥1.15, ≥30 positions and relative equity DD ≤20%. A failed validation remains a failed candidate even if its latest-year result looks good.

Fitted development return covers THREE years (26 Sep 2021–25 Sep 2024, M1 OHLC), not one year; it is in-sample and is not an expected future return.

| Asset / setup | Fitted 3y return | Validation 1y return | PF | Positions | DD | Development passes / unique vectors | Profitable nearby settings |
|---|---:|---:|---:|---:|---:|---:|---:|
| USTEC POC bounce | +34.66% | -10.72% | 0.61 | 41 | 13.12% | 265 / 245 | 100.0% |
| USTEC VA reversal | +69.22% | -5.26% | 0.93 | 119 | 23.13% | 269 / 249 | 48.1% |
| USTEC VA breakout | +86.30% | +8.68% | 1.10 | 126 | 13.88% | 279 / 259 | 100.0% |
| USTEC 3 Way combined | +153.04% | +13.80% | 1.14 | 168 | 15.62% | 284 / 264 | 100.0% |
| XAUUSD POC bounce | +93.35% | +16.20% | 1.75 | 41 | 5.83% | 265 / 245 | 100.0% |
| XAUUSD VA reversal | +62.06% | -15.63% | 0.78 | 152 | 21.13% | 246 / 226 | 55.6% |
| XAUUSD VA breakout | +52.24% | +18.88% | 1.36 | 68 | 11.71% | 279 / 259 | 100.0% |
| XAUUSD 3 Way combined | +58.35% | +2.44% | 1.03 | 156 | 10.61% | 266 / 246 | 100.0% |
| XAGUSD POC bounce | +28.52% | +7.88% | 1.57 | 18 | 6.14% | 265 / 245 | 55.6% |
| XAGUSD VA reversal | +40.72% | -2.01% | 0.90 | 27 | 13.11% | 265 / 245 | 66.7% |
| XAGUSD VA breakout | +33.34% | -11.37% | 0.57 | 32 | 15.73% | 283 / 263 | 59.3% |
| XAGUSD 3 Way combined | +53.94% | -9.35% | 0.67 | 33 | 16.14% | 285 / 265 | 100.0% |
| BTCUSD POC bounce | +23.62% | +5.36% | 1.38 | 34 | 5.35% | 269 / 249 | 100.0% |
| BTCUSD VA reversal | +54.88% | +3.09% | 1.13 | 34 | 12.77% | 265 / 245 | 100.0% |
| BTCUSD VA breakout | +46.69% | -4.94% | 0.90 | 83 | 14.84% | 278 / 258 | 92.6% |
| BTCUSD 3 Way combined | +62.88% | -4.64% | 0.80 | 34 | 16.63% | 284 / 264 | 100.0% |
| ETHUSD POC bounce | +46.38% | -4.07% | 0.83 | 32 | 14.95% | 269 / 249 | 100.0% |
| ETHUSD VA reversal | +54.73% | -4.89% | 0.95 | 183 | 18.03% | 265 / 245 | 77.8% |
| ETHUSD VA breakout | +99.78% | -6.58% | 0.72 | 31 | 15.37% | 279 / 259 | 66.7% |
| ETHUSD 3 Way combined | +263.33% | -12.90% | 0.86 | 134 | 30.48% | 285 / 265 | 100.0% |
| EURUSD POC bounce | +141.65% | +22.19% | 2.02 | 29 | 11.94% | 265 / 245 | 66.7% |
| EURUSD VA reversal | +52.62% | -13.81% | 0.67 | 72 | 20.75% | 265 / 245 | 100.0% |
| EURUSD VA breakout | +67.01% | -0.62% | 0.97 | 30 | 11.96% | 283 / 263 | 100.0% |
| EURUSD 3 Way combined | +29.10% | +6.54% | 1.52 | 32 | 6.88% | 289 / 269 | 100.0% |
| USDJPY POC bounce | +110.25% | -14.45% | 0.38 | 30 | 20.29% | 268 / 248 | 100.0% |
| USDJPY VA reversal | +39.42% | +9.07% | 1.57 | 52 | 4.38% | 265 / 245 | 88.9% |
| USDJPY VA breakout | +99.12% | +2.49% | 1.03 | 150 | 13.46% | 283 / 263 | 100.0% |
| USDJPY 3 Way combined | +274.40% | +4.34% | 1.05 | 167 | 20.31% | 284 / 264 | 100.0% |
| GBPJPY POC bounce | +22.24% | +2.33% | 1.14 | 25 | 5.81% | 265 / 245 | 37.0% |
| GBPJPY VA reversal | +44.73% | +0.64% | 1.03 | 36 | 10.64% | 269 / 249 | 74.1% |
| GBPJPY VA breakout | +46.68% | -12.74% | 0.16 | 38 | 14.58% | 283 / 263 | 100.0% |
| GBPJPY 3 Way combined | +70.54% | -17.52% | 0.84 | 152 | 22.72% | 285 / 265 | 100.0% |

## Selected settings (research only)

Search is staged with two survivors per step, not an exhaustive Cartesian grid. A saved selected configuration is not approval to trade it.

### USTEC — POC bounce

tf=M15; rr=1.5; bins=64; value=60; atr=14; buffer=0.1; breakout=1; near=0.5; depth=0.25; entry=market; stop=raw structure; stop_param=2; trail=break-even; trail_start=1.5; trail_distance=1.5; exit=fixed RR; session=07-16 UTC; direction=both; filter=none; day=all days; max_day=0; max_positions=1; reentry=1; max_bars=16; weekend=1; setups=1; poc_buffer=0.2

### USTEC — VA reversal

tf=M30; rr=2.5; bins=64; value=70; atr=14; buffer=0.1; breakout=1; near=0.5; depth=0.25; entry=market; stop=raw structure; stop_param=2; trail=EMA50; trail_start=1; trail_distance=1.5; exit=fixed RR; session=full day; direction=both; filter=none; day=all days; max_day=3; max_positions=1; reentry=1; max_bars=0; weekend=1; setups=2; poc_buffer=0.2

### USTEC — VA breakout

tf=M5; rr=3; bins=64; value=70; atr=14; buffer=0.1; breakout=1; near=0.5; depth=0.25; entry=signal breakout stop; stop=raw structure; stop_param=2; trail=ATR; trail_start=2; trail_distance=1.5; exit=fixed RR; session=full day; direction=both; filter=none; day=skip Monday; max_day=0; max_positions=1; reentry=1; max_bars=0; weekend=1; setups=4; poc_buffer=0.2

### USTEC — 3 Way combined

tf=M30; rr=2; bins=64; value=70; atr=14; buffer=0.1; breakout=0.5; near=0.5; depth=0.25; entry=market; stop=fixed price; stop_param=100; trail=ATR; trail_start=1; trail_distance=3; exit=no TP; session=full day; direction=both; filter=H1 EMA; day=all days; max_day=3; max_positions=1; reentry=1; max_bars=0; weekend=1; setups=7; poc_buffer=0.2

### XAUUSD — POC bounce

tf=H1; rr=8; bins=64; value=60; atr=14; buffer=0.1; breakout=1; near=0.5; depth=0.25; entry=market; stop=ATR distance; stop_param=1.5; trail=ATR; trail_start=1.5; trail_distance=2; exit=fixed RR; session=full day; direction=both; filter=none; day=all days; max_day=3; max_positions=1; reentry=1; max_bars=0; weekend=1; setups=1; poc_buffer=0.2

### XAUUSD — VA reversal

tf=H1; rr=1; bins=64; value=70; atr=14; buffer=0; breakout=1; near=0.5; depth=0.25; entry=market; stop=5-bar swing; stop_param=2; trail=ATR; trail_start=0.5; trail_distance=1.5; exit=fixed RR; session=full day; direction=both; filter=none; day=all days; max_day=0; max_positions=1; reentry=1; max_bars=0; weekend=1; setups=2; poc_buffer=0.2

### XAUUSD — VA breakout

tf=M5; rr=2; bins=64; value=70; atr=14; buffer=0.25; breakout=1; near=0.5; depth=0.25; entry=closed-bar confirmation; stop=fixed price; stop_param=20; trail=ATR; trail_start=2; trail_distance=3; exit=no TP; session=full day; direction=both; filter=EMA slope; day=all days; max_day=2; max_positions=1; reentry=1; max_bars=0; weekend=1; setups=4; poc_buffer=0.2

### XAUUSD — 3 Way combined

tf=H1; rr=1.25; bins=64; value=70; atr=14; buffer=0; breakout=1; near=0.5; depth=0.25; entry=market; stop=5-bar swing; stop_param=2; trail=ATR; trail_start=0.5; trail_distance=1.5; exit=fixed RR; session=full day; direction=both; filter=none; day=all days; max_day=0; max_positions=1; reentry=0; max_bars=0; weekend=1; setups=7; poc_buffer=0.2

### XAGUSD — POC bounce

tf=H4; rr=8; bins=64; value=70; atr=28; buffer=0.1; breakout=1; near=0.5; depth=0.25; entry=market; stop=ATR distance; stop_param=2; trail=ATR; trail_start=2; trail_distance=2; exit=fixed RR; session=full day; direction=both; filter=none; day=all days; max_day=0; max_positions=1; reentry=0; max_bars=0; weekend=1; setups=1; poc_buffer=0.2

### XAGUSD — VA reversal

tf=H4; rr=5; bins=96; value=70; atr=14; buffer=0.1; breakout=1; near=0.5; depth=0.25; entry=signal breakout stop; stop=ATR distance; stop_param=2; trail=chandelier; trail_start=1; trail_distance=2; exit=fixed RR; session=full day; direction=both; filter=none; day=all days; max_day=3; max_positions=1; reentry=1; max_bars=0; weekend=1; setups=2; poc_buffer=0.2

### XAGUSD — VA breakout

tf=M15; rr=2; bins=64; value=80; atr=14; buffer=0.1; breakout=1; near=0.5; depth=0.25; entry=closed-bar confirmation; stop=fixed price; stop_param=0.5; trail=ATR; trail_start=1.5; trail_distance=3; exit=no TP; session=full day; direction=both; filter=ATR percentile; day=skip Friday; max_day=0; max_positions=1; reentry=1; max_bars=0; weekend=1; setups=4; poc_buffer=0.2

### XAGUSD — 3 Way combined

tf=H4; rr=8; bins=64; value=60; atr=14; buffer=0.1; breakout=1; near=0.5; depth=0.25; entry=signal breakout stop; stop=ATR distance; stop_param=2; trail=ATR; trail_start=2; trail_distance=2; exit=fixed RR; session=full day; direction=both; filter=none; day=skip Friday; max_day=0; max_positions=1; reentry=1; max_bars=0; weekend=1; setups=7; poc_buffer=0.2

### BTCUSD — POC bounce

tf=H4; rr=3; bins=64; value=60; atr=14; buffer=0.1; breakout=1; near=0.5; depth=0.25; entry=signal breakout stop; stop=raw structure; stop_param=2; trail=step-lock; trail_start=1; trail_distance=1.5; exit=fixed RR; session=full day; direction=both; filter=none; day=skip Friday; max_day=0; max_positions=1; reentry=1; max_bars=0; weekend=1; setups=1; poc_buffer=0.2

### BTCUSD — VA reversal

tf=H4; rr=8; bins=64; value=70; atr=14; buffer=0.25; breakout=1; near=0.5; depth=0.25; entry=closed-bar confirmation; stop=fixed price; stop_param=500; trail=swing; trail_start=1; trail_distance=1.5; exit=fixed RR; session=full day; direction=both; filter=spread/ATR; day=all days; max_day=0; max_positions=2; reentry=1; max_bars=0; weekend=1; setups=2; poc_buffer=0.2

### BTCUSD — VA breakout

tf=H1; rr=2; bins=64; value=70; atr=14; buffer=0.1; breakout=0.5; near=0.5; depth=0.25; entry=0.25 ATR limit; stop=ATR distance; stop_param=3; trail=ATR; trail_start=1; trail_distance=3; exit=no TP; session=full day; direction=both; filter=H1 EMA; day=skip Monday; max_day=0; max_positions=1; reentry=1; max_bars=0; weekend=1; setups=4; poc_buffer=0.2

### BTCUSD — 3 Way combined

tf=H4; rr=8; bins=64; value=70; atr=14; buffer=0.1; breakout=0.5; near=0.5; depth=0.25; entry=closed-bar confirmation; stop=ATR distance; stop_param=0.75; trail=break-even; trail_start=1; trail_distance=1.5; exit=fixed RR; session=full day; direction=both; filter=none; day=all days; max_day=0; max_positions=1; reentry=0; max_bars=0; weekend=1; setups=7; poc_buffer=0.2

### ETHUSD — POC bounce

tf=M30; rr=2.5; bins=64; value=60; atr=14; buffer=0.1; breakout=1; near=0.5; depth=0.25; entry=0.25 ATR limit; stop=fixed price; stop_param=25; trail=ATR; trail_start=1.5; trail_distance=2; exit=fixed RR; session=full day; direction=both; filter=ATR percentile; day=all days; max_day=0; max_positions=2; reentry=1; max_bars=0; weekend=1; setups=1; poc_buffer=0.2

### ETHUSD — VA reversal

tf=H1; rr=2; bins=96; value=70; atr=14; buffer=0.1; breakout=1; near=0.5; depth=0.25; entry=asset-fixed limit; stop=5-bar swing; stop_param=2; trail=ATR; trail_start=2; trail_distance=1.5; exit=24-bar exit; session=full day; direction=both; filter=none; day=all days; max_day=2; max_positions=1; reentry=1; max_bars=0; weekend=1; setups=2; poc_buffer=0.2

### ETHUSD — VA breakout

tf=H1; rr=2; bins=32; value=70; atr=14; buffer=0.1; breakout=1; near=0.5; depth=0.25; entry=market; stop=signal extreme; stop_param=2; trail=ATR; trail_start=2; trail_distance=3; exit=no TP; session=NY 09:30-16; direction=both; filter=H1 EMA; day=all days; max_day=0; max_positions=2; reentry=1; max_bars=0; weekend=1; setups=4; poc_buffer=0.2

### ETHUSD — 3 Way combined

tf=H1; rr=6; bins=64; value=70; atr=14; buffer=0.1; breakout=1; near=0.5; depth=0; entry=asset-fixed limit; stop=ATR distance; stop_param=1.5; trail=ATR; trail_start=2; trail_distance=2; exit=fixed RR; session=full day; direction=both; filter=DI alignment; day=all days; max_day=3; max_positions=1; reentry=1; max_bars=0; weekend=1; setups=7; poc_buffer=0.2

### EURUSD — POC bounce

tf=H1; rr=2; bins=96; value=70; atr=14; buffer=0.1; breakout=1; near=0.5; depth=0.25; entry=signal breakout stop; stop=ATR distance; stop_param=0.5; trail=ATR; trail_start=1; trail_distance=3; exit=no TP; session=full day; direction=both; filter=none; day=all days; max_day=0; max_positions=1; reentry=0; max_bars=0; weekend=1; setups=1; poc_buffer=0.2

### EURUSD — VA reversal

tf=H1; rr=8; bins=64; value=70; atr=14; buffer=0.25; breakout=1; near=0.5; depth=0.25; entry=closed-bar confirmation; stop=price %; stop_param=0.1; trail=chandelier; trail_start=1; trail_distance=2; exit=fixed RR; session=full day; direction=both; filter=spread/ATR; day=all days; max_day=0; max_positions=1; reentry=1; max_bars=0; weekend=0; setups=2; poc_buffer=0.2

### EURUSD — VA breakout

tf=H1; rr=4; bins=32; value=70; atr=14; buffer=0.1; breakout=1; near=0.5; depth=0.25; entry=asset-fixed limit; stop=5-bar swing; stop_param=2; trail=break-even; trail_start=1.5; trail_distance=1.5; exit=fixed RR; session=full day; direction=both; filter=H1 EMA; day=all days; max_day=0; max_positions=1; reentry=0; max_bars=0; weekend=1; setups=4; poc_buffer=0.2

### EURUSD — 3 Way combined

tf=H4; rr=2; bins=64; value=70; atr=14; buffer=0.1; breakout=1; near=0.5; depth=0; entry=asset-fixed limit; stop=fixed price; stop_param=0.001; trail=ATR; trail_start=1; trail_distance=3; exit=partial 1R + trail; session=full day; direction=both; filter=ATR percentile; day=skip Monday; max_day=0; max_positions=1; reentry=1; max_bars=0; weekend=1; setups=7; poc_buffer=0.2

### USDJPY — POC bounce

tf=H4; rr=2; bins=64; value=60; atr=14; buffer=0.1; breakout=1; near=0.5; depth=0.25; entry=market; stop=ATR distance; stop_param=0.75; trail=ATR; trail_start=1.5; trail_distance=3; exit=no TP; session=full day; direction=both; filter=none; day=all days; max_day=0; max_positions=2; reentry=1; max_bars=0; weekend=1; setups=1; poc_buffer=0.2

### USDJPY — VA reversal

tf=M30; rr=6; bins=64; value=70; atr=14; buffer=0.25; breakout=1; near=0.5; depth=0.25; entry=market; stop=price %; stop_param=0.2; trail=ATR; trail_start=0.5; trail_distance=1; exit=fixed RR; session=12-16 UTC; direction=both; filter=none; day=all days; max_day=0; max_positions=1; reentry=1; max_bars=32; weekend=1; setups=2; poc_buffer=0.2

### USDJPY — VA breakout

tf=M30; rr=3; bins=64; value=70; atr=14; buffer=0.1; breakout=1; near=1; depth=0.25; entry=market; stop=price %; stop_param=0.1; trail=price %; trail_start=1; trail_distance=0.1; exit=fixed RR; session=full day; direction=both; filter=none; day=all days; max_day=0; max_positions=1; reentry=1; max_bars=16; weekend=1; setups=4; poc_buffer=0.2

### USDJPY — 3 Way combined

tf=M30; rr=2.5; bins=64; value=70; atr=14; buffer=0.5; breakout=1; near=0.5; depth=0.25; entry=asset-fixed limit; stop=fixed price; stop_param=0.4; trail=break-even; trail_start=1; trail_distance=1.5; exit=fixed RR; session=full day; direction=long only; filter=spread/ATR; day=all days; max_day=0; max_positions=2; reentry=1; max_bars=0; weekend=1; setups=7; poc_buffer=0.2

### GBPJPY — POC bounce

tf=M30; rr=2; bins=64; value=70; atr=14; buffer=0.1; breakout=1; near=0.5; depth=0.25; entry=0.25 ATR limit; stop=raw structure; stop_param=2; trail=ATR; trail_start=2; trail_distance=1.5; exit=fixed RR; session=full day; direction=both; filter=none; day=all days; max_day=0; max_positions=1; reentry=1; max_bars=0; weekend=0; setups=1; poc_buffer=0.2

### GBPJPY — VA reversal

tf=H4; rr=2; bins=64; value=70; atr=14; buffer=0.1; breakout=1; near=0.5; depth=0.25; entry=asset-fixed limit; stop=raw structure; stop_param=2; trail=ATR; trail_start=1.5; trail_distance=2; exit=fixed RR; session=full day; direction=both; filter=ADX20; day=all days; max_day=0; max_positions=1; reentry=1; max_bars=0; weekend=1; setups=2; poc_buffer=0.2

### GBPJPY — VA breakout

tf=M30; rr=2.5; bins=64; value=70; atr=14; buffer=0.25; breakout=1; near=0.5; depth=0.25; entry=signal breakout stop; stop=price %; stop_param=0.2; trail=break-even; trail_start=0.5; trail_distance=1.5; exit=fixed RR; session=full day; direction=both; filter=ATR percentile; day=all days; max_day=0; max_positions=1; reentry=0; max_bars=0; weekend=1; setups=4; poc_buffer=0.2

### GBPJPY — 3 Way combined

tf=M30; rr=2; bins=64; value=70; atr=14; buffer=0.1; breakout=1; near=1; depth=0.25; entry=asset-fixed limit; stop=raw structure; stop_param=2; trail=ATR; trail_start=2; trail_distance=1.5; exit=fixed RR; session=full day; direction=both; filter=spread/ATR; day=all days; max_day=0; max_positions=1; reentry=1; max_bars=0; weekend=1; setups=7; poc_buffer=0.2

## Limitations and evidence

- Only one later comparison year; selection bias remains across 32 strategies and thousands of trials.
- Original profiles use broker tick volume, not centralized exchange transaction volume.
- Development uses M1 OHLC, which can favor intrabar stop/target/trailing behavior. Native Model 4 confirmation may reverse rankings.
- No independent holdout, extra cost stress or Monte Carlo promotion approval is implied.
- These runs use the isolated historical Exness research binding, not FTMO Swing margin/rules.
- Spread and configured delay are modeled; execution quality during news is not guaranteed by a backtest.
- Each completed asset has raw-parity evidence. Source, compiled binary, inputs, native reports and journals are under `native/`.
- Combined uses a shared configuration for its three setups; it is not a portfolio of three independently tuned parameter sets.
- `positions.json` contains exact MT5 position-ID cash ledgers for final runs; commissions, fees and swap reconcile to native net P/L.
- No live terminals, orders, BATs, production EAs, website data or deployment settings were changed.
