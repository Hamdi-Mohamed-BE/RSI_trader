# ATR Touch — raw test report (2026-09-25)

Source: IQ Capital reel (@iqcapitalofficial) about trader "MNQ" — screenshot kept as `source-reel-screenshot.webp`:
long when the candle's lower wick touches a lower ATR band (whiteboard: 3.1 × ATR, "×3.1 = 155" with ATR 50), long only,
no other filter, a limit order that follows the band. Unspecified parts fixed before testing (`run-config.json`).
**Result: 23 of 24 symbol/timeframe/target cells fail the screen; the only survivor (XAU H1 2:1) weakens with real
ticks (5y PF 1.14, last year negative) — not recommended.** Research only; nothing deployed. Tables: `RESULTS.md`.

## Rules (EA/ATR Touch Research EA.mq5, 0 errors / 0 warnings)

Band = close[1] − 3.1 × ATR(14); buy limit re-placed each new bar while flat; stop 1 × ATR below the limit; target 1:1 or
2:1; 48-bar time stop; long only; 1% risk. Timeframes M5/M15/H1; USTEC (MNQ proxy), US500, XAUUSD, BTCUSD.
Control: random longs (~1% of bars) with the same exits. Screen Model 1 on 3y/5y (96 runs), then Model 4 on all periods
for survivors. One screen case failed when port 3000 (the MT5 agent port) was taken by another program; it is kept
as `native/FAILED-port3000-*` and was rerun.

## Screen, 5 years (trades per month / per trading day · return · PF)

| Symbol | M5 1:1 | M5 2:1 | M15 1:1 | M15 2:1 | H1 1:1 | H1 2:1 |
|---|---|---|---|---|---|---|
| USTEC | 23.5/mo −99.2% 0.41 | 23.4/mo −98.8% 0.52 | 14.0/mo −91.2% 0.48 | 13.9/mo −90.8% 0.57 | 7.6/mo −61.3% 0.63 | 7.4/mo −56.3% 0.72 |
| US500 | 21.1/mo −98.8% 0.45 | 20.9/mo −97.7% 0.58 | 11.8/mo −87.4% 0.53 | 11.8/mo −85.7% 0.64 | 6.3/mo −64.2% 0.59 | 6.2/mo −62.5% 0.67 |
| XAUUSD | 19.1/mo −72.1% 0.78 | 18.9/mo −51.6% 0.89 | 10.3/mo −45.8% 0.83 | 10.2/mo −10.5% 0.98 | 3.7/mo +8.2% 1.07 | **3.7/mo +31.6% 1.19** |
| BTCUSD | 35.2/mo −96.1% 0.54 | 34.8/mo −96.2% 0.65 | 14.4/mo −84.3% 0.57 | 14.2/mo −88.6% 0.60 | 5.2/mo −16.7% 0.89 | 5.1/mo −24.2% 0.86 |

## Real-tick confirmation — XAUUSD H1 2:1 (Model 4)

| Window | Trades (/mo, /day) | Return | PF | Random-long control |
|---|---|---|---|---|
| 6m | 21 (3.5, 0.16) | −7.8% | 0.53 | — |
| 1y | 49 (4.1, 0.19) | −3.3% | 0.91 | — |
| 3y | 127 (3.5, 0.16) | +27.2% | 1.29 | +12.8%, PF 1.10 |
| 5y | 220 (3.7, 0.17) | +22.3% | 1.14 | −4.1%, PF 0.98 |

## Findings

1. On the US indices (the reel's MNQ market) it loses on every timeframe (5y PF 0.41–0.72) — buying 3.1-ATR flushes
   with a 1-ATR stop is mostly catching falling knives; on M5 most fills happen in thin overnight spikes and last ~1 minute.
2. XAU H1 2:1 is the only positive cell: it beats random longs over 3y/5y, but with real ticks its 5y PF drops to 1.14
   (below the 1.15 gate) and the last 6–12 months are negative. Not robust enough to build on.
3. Journal "[Market closed]" lines are the resting limit being re-placed on closed-market bars; harmless.
4. Disk: the folder is ~1 GB because re-placing the limit every M5 bar for 5 years produces very large journals/reports
   (~60 MB compressed per M5 run). Exclude `native/at-m1-*` journals/reports if this folder is ever pushed.

## Decision

Fails the pre-registered gate on real ticks; no optimization.
