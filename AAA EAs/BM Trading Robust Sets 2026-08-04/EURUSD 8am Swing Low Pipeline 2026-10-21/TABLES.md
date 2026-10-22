# EURUSD 8am swing low pipeline — tables (generated)

Configurations tested (all stages, both tracks, incl. plateau grids): **699**; parity: {"L8": {"engine_trades": 100, "raw_trades": 100, "mismatches": 0, "engine_net": 349.94, "raw_net": 349.94, "first_mismatch": null}, "NY8": {"engine_trades": 130, "raw_trades": 130, "mismatches": 0, "engine_net": 404.95, "raw_net": 404.95, "first_mismatch": null}, "SHORT_NY8": {"engine_trades": 159, "raw_trades": 159, "mismatches": 0, "engine_net": -417.53, "raw_net": -417.53, "first_mismatch": null}}

## london — staged search on development 2016-10-17 → 2023-10-17 (Model 1)

| Stage | Tested | Best carried configuration | Trades | / month | / day | Return | PF | Win % | Closed DD | Equity DD | Max win / loss streak |
|---|---|---|---|---|---|---|---|---|---|---|---|
| swing | 72 | London 08:00 | H1 fractal 1 window 2 lower-low | long after low | market | stop pivot - 0.1 ATR (min 0.5) | mgmt none | exit 4 h | filters none | 272 | 3.24 | 0.149 | +45.7% | 1.2 | 37.1% | 14.27% | 15.1% | 4/7 |
| entry | 12 | London 08:00 | M30 fractal 2 window 4 lower-low | long after low | stop-entry | stop pivot - 0.1 ATR (min 0.5) | mgmt none | exit 4 h | filters none | 221 | 2.63 | 0.121 | +51.3% | 1.35 | 43.9% | 9.26% | 10.1% | 4/10 |
| stop | 27 | London 08:00 | M30 fractal 2 window 4 lower-low | long after low | stop-entry | stop pivot - 0.5 ATR (min 0.5) | mgmt none | exit 4 h | filters none | 221 | 2.63 | 0.121 | +57.6% | 1.44 | 47.5% | 6.72% | 7.5% | 5/7 |
| mgmt | 24 | London 08:00 | M30 fractal 2 window 4 lower-low | long after low | stop-entry | stop pivot - 0.5 ATR (min 0.5) | mgmt none | exit 4 h | filters none | 221 | 2.63 | 0.121 | +57.6% | 1.44 | 47.5% | 6.72% | 7.5% | 5/7 |
| exit | 87 | London 08:00 | M30 fractal 2 window 4 lower-low | long after low | stop-entry | stop pivot - 0.5 ATR (min 0.5) | mgmt none | exit 4 h | filters none | 221 | 2.63 | 0.121 | +57.6% | 1.44 | 47.5% | 6.72% | 7.5% | 5/7 |
| anchor | 18 | London 08:00 | M30 fractal 2 window 4 lower-low | long after low | stop-entry | stop pivot - 0.5 ATR (min 0.5) | mgmt none | exit 4 h | filters none | 221 | 2.63 | 0.121 | +57.6% | 1.44 | 47.5% | 6.72% | 7.5% | 5/7 |
| direction | 9 | London 08:00 | M30 fractal 2 window 4 lower-low | long after low | stop-entry | stop pivot - 0.5 ATR (min 0.5) | mgmt none | exit 4 h | filters none | 221 | 2.63 | 0.121 | +57.6% | 1.44 | 47.5% | 6.72% | 7.5% | 5/7 |
| filters | 33 | London 08:00 | M30 fractal 2 window 4 lower-low | long after low | stop-entry | stop pivot - 0.5 ATR (min 0.5) | mgmt none | exit 4 h | filters skip Fri | 174 | 2.07 | 0.095 | +61.9% | 1.65 | 50.6% | 6.94% | 7.7% | 5/6 |

### london — best development result per option (side by side)

| Dimension | Option | Best PF | Trades | Return | Configs |
|---|---|---|---|---|---|
| swing: tf | M15 | 1.17 | 247 | +31.0% | 24 |
| swing: tf | M30 | 1.13 | 329 | +32.7% | 24 |
| swing: tf | H1 | 1.2 | 272 | +45.7% | 24 |
| swing: n | 1 | 1.2 | 272 | +45.7% | 24 |
| swing: n | 2 | 1.13 | 329 | +32.7% | 24 |
| swing: n | 3 | 1.17 | 247 | +31.0% | 24 |
| swing: w | 1 | 0.98 | 259 | -3.3% | 18 |
| swing: w | 2 | 1.2 | 272 | +45.7% | 18 |
| swing: w | 4 | 1.13 | 329 | +32.7% | 18 |
| swing: w | 6 | 1.11 | 527 | +43.3% | 18 |
| swing: ll | 0 | 1.03 | 758 | +14.1% | 36 |
| swing: ll | 1 | 1.2 | 272 | +45.7% | 36 |
| entry: entry | market | 1.2 | 272 | +45.7% | 3 |
| entry: entry | limit | 1.14 | 242 | +29.5% | 6 |
| entry: entry | stop-entry | 1.35 | 221 | +51.3% | 3 |
| stop: stop_type | 0 | 1.44 | 221 | +57.6% | 12 |
| stop: stop_type | 1 | 1.39 | 221 | +108.2% | 15 |
| mgmt: be_r | 0 | 1.49 | 221 | +55.2% | 15 |
| mgmt: be_r | 0.5 | 1.49 | 221 | +47.6% | 3 |
| mgmt: be_r | 1 | 1.41 | 221 | +56.5% | 3 |
| mgmt: be_r | 1.5 | 1.42 | 221 | +54.0% | 3 |
| mgmt: trail_atr | 0 | 1.49 | 221 | +47.6% | 12 |
| mgmt: trail_atr | 1 | 1.29 | 221 | +32.2% | 6 |
| mgmt: trail_atr | 2 | 1.49 | 221 | +55.2% | 6 |
| exit: tp_r | 0 | 1.49 | 221 | +55.2% | 21 |
| exit: tp_r | 0.5 | 1.05 | 221 | +3.7% | 6 |
| exit: tp_r | 0.75 | 0.98 | 221 | -2.0% | 6 |
| exit: tp_r | 1 | 0.98 | 221 | -1.9% | 6 |
| exit: tp_r | 1.25 | 1.03 | 221 | +2.9% | 6 |
| exit: tp_r | 1.5 | 0.99 | 221 | -1.2% | 6 |
| exit: tp_r | 2 | 0.99 | 221 | -0.6% | 6 |
| exit: tp_r | 2.5 | 1.02 | 221 | +2.4% | 6 |
| exit: tp_r | 3 | 1.03 | 221 | +2.9% | 6 |
| exit: tp_r | 4 | 1.06 | 221 | +6.2% | 6 |
| exit: tp_r | 5 | 1.13 | 221 | +17.2% | 6 |
| exit: tp_r | 6 | 1.21 | 221 | +28.5% | 6 |
| exit: hold_h | 0 | 1.21 | 221 | +28.7% | 36 |
| exit: hold_h | 1 | 1.24 | 221 | +17.4% | 3 |
| exit: hold_h | 2 | 1.11 | 221 | +8.5% | 3 |
| exit: hold_h | 3 | 1.36 | 221 | +35.0% | 3 |
| exit: hold_h | 4 | 1.49 | 221 | +55.2% | 3 |
| exit: hold_h | 6 | 1.33 | 221 | +44.2% | 3 |
| exit: hold_h | 8 | 1.21 | 221 | +28.5% | 36 |
| anchor: hour | 7 | 1.2 | 233 | +20.9% | 6 |
| anchor: hour | 8 | 1.49 | 221 | +55.2% | 6 |
| anchor: hour | 9 | 1.03 | 438 | +4.2% | 6 |
| direction: dir | long after low | 1.49 | 221 | +55.2% | 3 |
| direction: dir | short after high | 1.08 | 267 | +9.2% | 3 |
| direction: dir | both | 1.22 | 468 | +54.0% | 3 |
| filters: trend | none | 1.99 | 127 | +52.9% | 24 |
| filters: trend | H1 EMA200 side | 0.94 | 99 | -2.5% | 3 |
| filters: trend | EMA50 slope | 1.01 | 92 | +0.5% | 3 |
| filters: trend | D1 EMA20 side | 1.45 | 103 | +22.2% | 3 |
| filters: adx_min | 0 | 1.99 | 127 | +52.9% | 27 |
| filters: adx_min | 20 | 1.49 | 173 | +40.2% | 3 |
| filters: adx_min | 25 | 1.42 | 123 | +22.0% | 3 |
| filters: atr_regime | any | 1.99 | 127 | +52.9% | 27 |
| filters: atr_regime | ATR above median | 3.21 | 15 | +10.3% | 3 |
| filters: atr_regime | ATR below median | 1.4 | 206 | +40.4% | 3 |
| filters: dow | all days | 1.49 | 173 | +40.2% | 24 |
| filters: dow | skip Mon | 1.6 | 174 | +51.3% | 3 |
| filters: dow | skip Fri | 1.72 | 174 | +56.9% | 3 |
| filters: dow | skip Mon+Fri | 1.99 | 127 | +52.9% | 3 |

### london — plateau (joint ±1 step grid: freshness window × exit × anchor ±30 min, development)

| Finalist | Configuration | Dev PF / trades / return | Neighbours | Profitable neighbours | Median neighbour PF | Plateau |
|---|---|---|---|---|---|---|
| 1 | London 08:00 | M30 fractal 2 window 4 lower-low | long after low | stop-entry | stop pivot - 0.5 ATR (min 0.5) | mgmt none | exit 4 h | filters skip Fri | 1.65 / 174 / +61.9% | 27 | 52% | 1.00 | **FAIL** |
| 2 | London 08:00 | M30 fractal 2 window 4 lower-low | long after low | stop-entry | stop pivot - 0.5 ATR (min 0.5) | mgmt  trail 2 ATR from 0.5R | exit 4 h | filters skip Mon+Fri | 1.99 / 127 / +52.9% | 27 | 44% | 0.91 | **FAIL** |
| 3 | London 08:00 | M30 fractal 2 window 4 lower-low | long after low | stop-entry | stop pivot - 0.5 ATR (min 0.5) | mgmt  trail 2 ATR from 0.5R | exit 4 h | filters skip Fri | 1.72 / 174 / +56.9% | 27 | 56% | 1.01 | **FAIL** |

## newyork — staged search on development 2016-10-17 → 2023-10-17 (Model 1)

| Stage | Tested | Best carried configuration | Trades | / month | / day | Return | PF | Win % | Closed DD | Equity DD | Max win / loss streak |
|---|---|---|---|---|---|---|---|---|---|---|---|
| swing | 72 | New York 08:00 | H1 fractal 2 window 1 lower-low | long after low | market | stop pivot - 0.1 ATR (min 0.5) | mgmt none | exit 4 h | filters none | 143 | 1.7 | 0.078 | +30.2% | 1.37 | 37.8% | 12.48% | 14.2% | 4/9 |
| entry | 12 | New York 08:00 | H1 fractal 2 window 1 lower-low | long after low | limit 0.25 ATR | stop pivot - 0.1 ATR (min 0.5) | mgmt none | exit 4 h | filters none | 122 | 1.45 | 0.067 | +50.7% | 1.6 | 40.2% | 11.06% | 16.3% | 5/6 |
| stop | 27 | New York 08:00 | H1 fractal 2 window 1 lower-low | long after low | limit 0.25 ATR | stop pivot - 0 ATR (min 0.5) | mgmt none | exit 4 h | filters none | 122 | 1.45 | 0.067 | +53.2% | 1.59 | 37.7% | 10.92% | 16.3% | 5/7 |
| mgmt | 24 | New York 08:00 | H1 fractal 2 window 1 lower-low | long after low | limit 0.25 ATR | stop pivot - 0 ATR (min 0.5) | mgmt none | exit 4 h | filters none | 122 | 1.45 | 0.067 | +53.2% | 1.59 | 37.7% | 10.92% | 16.3% | 5/7 |
| exit | 87 | New York 08:00 | H1 fractal 2 window 1 lower-low | long after low | limit 0.25 ATR | stop pivot - 0 ATR (min 0.5) | mgmt none | exit 4 h | filters none | 122 | 1.45 | 0.067 | +53.2% | 1.59 | 37.7% | 10.92% | 16.3% | 5/7 |
| anchor | 18 | New York 08:00 | H1 fractal 2 window 1 lower-low | long after low | limit 0.25 ATR | stop pivot - 0 ATR (min 0.5) | mgmt none | exit 4 h | filters none | 122 | 1.45 | 0.067 | +53.2% | 1.59 | 37.7% | 10.92% | 16.3% | 5/7 |
| direction | 9 | New York 08:00 | H1 fractal 2 window 1 lower-low | long after low | limit 0.25 ATR | stop pivot - 0 ATR (min 0.5) | mgmt none | exit 4 h | filters none | 122 | 1.45 | 0.067 | +53.2% | 1.59 | 37.7% | 10.92% | 16.3% | 5/7 |
| filters | 33 | New York 08:00 | H1 fractal 2 window 1 lower-low | long after low | limit 0.25 ATR | stop pivot - 0.1 ATR (min 0.5) | mgmt none | exit 4 h | filters ATR below median | 77 | 0.92 | 0.042 | +48.5% | 1.82 | 36.4% | 9.11% | 13.7% | 3/6 |

### newyork — best development result per option (side by side)

| Dimension | Option | Best PF | Trades | Return | Configs |
|---|---|---|---|---|---|
| swing: tf | M15 | 1.03 | 84 | +1.9% | 24 |
| swing: tf | M30 | 1.19 | 152 | +18.9% | 24 |
| swing: tf | H1 | 1.37 | 143 | +30.2% | 24 |
| swing: n | 1 | 1.15 | 400 | +38.3% | 24 |
| swing: n | 2 | 1.37 | 143 | +30.2% | 24 |
| swing: n | 3 | 1.19 | 152 | +18.9% | 24 |
| swing: w | 1 | 1.37 | 143 | +30.2% | 18 |
| swing: w | 2 | 1.16 | 292 | +30.0% | 18 |
| swing: w | 4 | 1.1 | 611 | +37.9% | 18 |
| swing: w | 6 | 1.09 | 754 | +57.8% | 18 |
| swing: ll | 0 | 1.25 | 203 | +29.6% | 36 |
| swing: ll | 1 | 1.37 | 143 | +30.2% | 36 |
| entry: entry | market | 1.37 | 143 | +30.2% | 3 |
| entry: entry | limit | 1.6 | 122 | +50.7% | 6 |
| entry: entry | stop-entry | 1.46 | 94 | +17.6% | 3 |
| stop: stop_type | 0 | 1.6 | 122 | +50.7% | 12 |
| stop: stop_type | 1 | 1.28 | 122 | +34.0% | 15 |
| mgmt: be_r | 0 | 1.6 | 122 | +50.7% | 15 |
| mgmt: be_r | 0.5 | 1.31 | 122 | +15.8% | 3 |
| mgmt: be_r | 1 | 1.29 | 122 | +20.8% | 3 |
| mgmt: be_r | 1.5 | 1.27 | 122 | +21.5% | 3 |
| mgmt: trail_atr | 0 | 1.6 | 122 | +50.7% | 12 |
| mgmt: trail_atr | 1 | 1.12 | 122 | +7.2% | 6 |
| mgmt: trail_atr | 2 | 1.36 | 122 | +31.3% | 6 |
| exit: tp_r | 0 | 1.6 | 122 | +50.7% | 21 |
| exit: tp_r | 0.5 | 0.91 | 122 | -3.5% | 6 |
| exit: tp_r | 0.75 | 0.98 | 122 | -1.1% | 6 |
| exit: tp_r | 1 | 1.04 | 122 | +2.0% | 6 |
| exit: tp_r | 1.25 | 0.94 | 122 | -3.9% | 6 |
| exit: tp_r | 1.5 | 0.85 | 122 | -10.2% | 6 |
| exit: tp_r | 2 | 0.93 | 122 | -5.4% | 6 |
| exit: tp_r | 2.5 | 1.06 | 122 | +4.8% | 6 |
| exit: tp_r | 3 | 1.05 | 122 | +4.2% | 6 |
| exit: tp_r | 4 | 1.24 | 122 | +20.3% | 6 |
| exit: tp_r | 5 | 1.21 | 122 | +18.0% | 6 |
| exit: tp_r | 6 | 1.34 | 122 | +31.9% | 6 |
| exit: hold_h | 0 | 1.33 | 122 | +30.9% | 36 |
| exit: hold_h | 1 | 1.38 | 122 | +21.5% | 3 |
| exit: hold_h | 2 | 1.43 | 122 | +32.0% | 3 |
| exit: hold_h | 3 | 1.37 | 122 | +30.0% | 3 |
| exit: hold_h | 4 | 1.6 | 122 | +50.7% | 3 |
| exit: hold_h | 6 | 1.39 | 122 | +34.3% | 3 |
| exit: hold_h | 8 | 1.37 | 122 | +34.4% | 36 |
| anchor: hour | 7 | 0.78 | 163 | -21.0% | 6 |
| anchor: hour | 8 | 1.6 | 122 | +50.7% | 6 |
| anchor: hour | 9 | 0.94 | 88 | -2.5% | 6 |
| direction: dir | long after low | 1.6 | 122 | +50.7% | 3 |
| direction: dir | short after high | 0.71 | 120 | -19.6% | 3 |
| direction: dir | both | 1.1 | 241 | +17.3% | 3 |
| filters: trend | none | 1.82 | 77 | +48.5% | 24 |
| filters: trend | H1 EMA200 side | 1.14 | 59 | +5.5% | 3 |
| filters: trend | EMA50 slope | 1.25 | 49 | +7.7% | 3 |
| filters: trend | D1 EMA20 side | 1.35 | 59 | +14.4% | 3 |
| filters: adx_min | 0 | 1.82 | 77 | +48.5% | 27 |
| filters: adx_min | 20 | 0.84 | 90 | -9.0% | 3 |
| filters: adx_min | 25 | 0.81 | 65 | -8.0% | 3 |
| filters: atr_regime | any | 1.6 | 122 | +50.7% | 27 |
| filters: atr_regime | ATR above median | 1.16 | 45 | +3.6% | 3 |
| filters: atr_regime | ATR below median | 1.82 | 77 | +48.5% | 3 |
| filters: dow | all days | 1.82 | 77 | +48.5% | 24 |
| filters: dow | skip Mon | 1.58 | 101 | +40.3% | 3 |
| filters: dow | skip Fri | 1.43 | 97 | +27.8% | 3 |
| filters: dow | skip Mon+Fri | 1.35 | 76 | +17.6% | 3 |

### newyork — plateau (joint ±1 step grid: freshness window × exit × anchor ±30 min, development)

| Finalist | Configuration | Dev PF / trades / return | Neighbours | Profitable neighbours | Median neighbour PF | Plateau |
|---|---|---|---|---|---|---|
| 1 | New York 08:00 | H1 fractal 2 window 1 lower-low | long after low | limit 0.25 ATR | stop pivot - 0.1 ATR (min 0.5) | mgmt none | exit 4 h | filters ATR below median | 1.82 / 77 / +48.5% | 18 | 33% | 0.90 | **FAIL** |
| 2 | New York 08:00 | H1 fractal 2 window 1 lower-low | long after low | limit 0.25 ATR | stop pivot - 0 ATR (min 0.5) | mgmt none | exit 4 h | filters none | 1.59 / 122 / +53.2% | 18 | 28% | 0.80 | **FAIL** |
| 3 | New York 08:00 | H1 fractal 2 window 1 lower-low | long after low | limit 0.25 ATR | stop pivot - 0.1 ATR (min 0.5) | mgmt none | exit 4 h | filters none | 1.60 / 122 / +50.7% | 18 | 28% | 0.83 | **FAIL** |

## POST-REJECTION DIAGNOSTIC (not a selection): the six rejected finalists, Model 4

| Track / finalist | Window | Trades | / month | / day | Return | PF | Win % | Closed DD | Equity DD | Max win / loss streak |
|---|---|---|---|---|---|---|---|---|---|---|
| London 1 | Validation 2023-24 | 28 | 2.33 | 0.107 | -5.0% | 0.66 | 35.7% | 7.54% | 8.5% | 2/4 |
| London 1 | OOS 2024-26 | 61 | 2.54 | 0.117 | -12.7% | 0.51 | 39.3% | 12.8% | 13.2% | 6/10 |
| London 2 | Validation 2023-24 | 23 | 1.91 | 0.088 | -3.6% | 0.66 | 34.8% | 5.84% | 6.8% | 1/3 |
| London 2 | OOS 2024-26 | 49 | 2.04 | 0.094 | -13.6% | 0.29 | 36.7% | 13.66% | 14.5% | 4/6 |
| London 3 | Validation 2023-24 | 28 | 2.33 | 0.107 | -7.0% | 0.5 | 28.6% | 9.11% | 10.0% | 1/5 |
| London 3 | OOS 2024-26 | 61 | 2.54 | 0.117 | -12.5% | 0.47 | 37.7% | 12.6% | 13.0% | 5/7 |
| New York 1 | Validation 2023-24 | 12 | 1.0 | 0.046 | +17.1% | 4.5 | 58.3% | 2.03% | 4.8% | 4/2 |
| New York 1 | OOS 2024-26 | 23 | 0.96 | 0.044 | -15.1% | 0.1 | 17.4% | 15.12% | 16.0% | 1/11 |
| New York 2 | Validation 2023-24 | 16 | 1.33 | 0.061 | +13.8% | 2.64 | 43.8% | 2.29% | 5.7% | 3/3 |
| New York 2 | OOS 2024-26 | 30 | 1.25 | 0.057 | -9.9% | 0.53 | 23.3% | 10.63% | 11.5% | 1/5 |
| New York 3 | Validation 2023-24 | 16 | 1.33 | 0.061 | +15.4% | 3.12 | 50.0% | 2.27% | 4.8% | 4/3 |
| New York 3 | OOS 2024-26 | 30 | 1.25 | 0.057 | -10.8% | 0.48 | 23.3% | 11.13% | 11.9% | 1/5 |
