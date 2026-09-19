# US500 transfer — unchanged active presets

2025.09.19 inclusive to 2026.09.19 exclusive. Each independent USD 10,000 test uses the saved 1% base risk. Native MT5 / 150 ms modeled delay. No optimization or adaptive portfolio overlay.

| Original preset transferred to US500 | Return | Net USD | Trades | Net win rate | Net PF | Equity DD | Commission | Swap | History quality |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| DMC Fresh Reaction US100 | -7.57% | -757.26 | 23 | 34.78% | 0.49 | 10.63% | -26.33 | -32.89 | 71% real ticks |
| Nasdaq 5M Candle Momentum | +21.74% | +2174.04 | 256 | 39.06% | 1.12 | 12.78% | -400.12 | -209.27 | 71% real ticks |
| US100 Month End Flow | +10.60% | +1059.71 | 34 | 47.06% | 1.61 | 5.39% | -55.95 | -58.76 | 71% real ticks |
| Nasdaq Overnight | +5.75% | +574.76 | 74 | 68.92% | 1.92 | 1.21% | -13.44 | -108.47 | 71% real ticks |
| Sell Nasdaq 15min (recommended dynamic) | +8.14% | +813.95 | 44 | 36.36% | 1.31 | 9.43% | -65.86 | 0.00 | 71% real ticks |
| US100 H1 ORB 13UTC | +16.83% | +1683.41 | 69 | 53.62% | 1.50 | 9.26% | -80.78 | 0.00 | 71% real ticks |
| US100 ORB New York M30 | -5.31% | -531.46 | 17 | 23.53% | 0.57 | 7.79% | -28.74 | -23.60 | 71% real ticks |
| US100 Selective ORB V3 | -2.33% | -233.50 | 5 | 0.00% | 0.00 | 2.67% | -5.81 | 0.00 | 71% real ticks |
| ORB Volume Profile (XAU preset) | -4.66% | -465.74 | 17 | 29.41% | 0.56 | 7.34% | -22.40 | 0.00 | 71% real ticks |
| ORB Volume Confirmed (XAU preset) | -1.67% | -167.25 | 6 | 16.67% | 0.60 | 4.35% | -7.50 | 0.00 | 71% real ticks |
| XAU ORB New York M30 | +0.00% | +0.00 | 0 | N/A | N/A | 0.00% | 0.00 | 0.00 | 71% real ticks |
| XAU ORB London NY Overlap M30 | +0.84% | +83.99 | 22 | 40.91% | 1.11 | 3.42% | -66.88 | 0.00 | 71% real ticks |

## Limits

- This is a transfer screen of 12 active presets, not the hundreds of archived research variants and not a simultaneous portfolio.
- Native spread and recorded commissions/swaps included. Delay models execution effects; live news fills are not demonstrated.
- Real/generated tick coverage and warnings are retained in each summary. A year with generated ticks is not a full real-tick validation.
- DMC historical clock only mapped from EET/UTC+3 to Exness UTC. No trading parameters retuned. Minimum lots/upward rounding can exceed 1%.
- Sell Nasdaq uses the currently recommended dynamic-exit source/SET, not its archived fixed-pip baseline.
- Equity DD uses the larger native relative value and tick-observed value. SL/TP are from original native order records; they are not the final trailing stop.
- No system deployment or website/BAT changes. Gold Value Area full pipeline remains separate.

## Streaks and risk

| Preset | Max win streak | Max loss streak | Max initial risk | Native equity DD | Tick-observed DD |
|---|---:|---:|---:|---:|---:|
| DMC Fresh Reaction US100 | 2 | 4 | 1.060% | 10.53% | 10.63% |
| Nasdaq 5M Candle Momentum | 7 | 7 | 1.094% | 12.64% | 12.78% |
| US100 Month End Flow | 3 | 3 | 1.142% | 5.21% | 5.39% |
| Nasdaq Overnight | 6 | 3 | 1.060% | 1.15% | 1.21% |
| Sell Nasdaq 15min (recommended dynamic) | 2 | 9 | 1.025% | 9.33% | 9.43% |
| US100 H1 ORB 13UTC | 4 | 4 | 1.067% | 9.21% | 9.26% |
| US100 ORB New York M30 | 2 | 8 | 1.183% | 7.69% | 7.79% |
| US100 Selective ORB V3 | 0 | 5 | 1.008% | 2.67% | 2.67% |
| ORB Volume Profile (XAU preset) | 1 | 3 | 1.020% | 7.34% | 7.34% |
| ORB Volume Confirmed (XAU preset) | 1 | 5 | 1.021% | 4.35% | 4.35% |
| XAU ORB New York M30 | 0 | 0 | 0.000% | 0.00% | 0.00% |
| XAU ORB London NY Overlap M30 | 5 | 4 | 1.220% | 3.35% | 3.42% |

## Original settings retained

| Preset | Signal chart | Opening range | Target | Break-even trigger | Dynamic 50/20 | Other stop inputs |
|---|---|---|---|---|---|---|
| DMC Fresh Reaction US100 | H1 | N/A min | 2.0R | disabled | true | DmCStopATR=1.5 |
| Nasdaq 5M Candle Momentum | M5 | N/A min | 2.5R | disabled | false | StopMode=0, InitialStopATR=4.0 |
| US100 Month End Flow | M30 | N/A min | 2.5R | disabled | false | StopMode=0, StopValue=1.5 |
| Nasdaq Overnight | M1 | N/A min | Time exit; no fixed TP | disabled | false | EmergencyStopPercent=2 |
| Sell Nasdaq 15min (recommended dynamic) | M15 | 15 min | 3.0R | 0.0 | false | StopMode=3, StopAtrMultiple=2.5 |
| US100 H1 ORB 13UTC | M15 | 60 min | 6.0R | 0.0 | false | StopMode=1, StopBufferATR=0.1 |
| US100 ORB New York M30 | M30 | 5 min | 4.0R | 0.0 | false | StopMode=1, StopBufferATR=0.1 |
| US100 Selective ORB V3 | M5 | 30 min | 2.00R | 1.00 | false |  |
| ORB Volume Profile (XAU preset) | M5 | 15 min | 2.5R | 1.0 | true | StopMode=1, StopBufferATR=0.1 |
| ORB Volume Confirmed (XAU preset) | M5 | 15 min | 2.5R | 1.0 | true | StopMode=1, StopBufferATR=0.1 |
| XAU ORB New York M30 | M30 | 30 min | 1.5R | 0.5 | false | StopMode=1, StopBufferATR=0.1 |
| XAU ORB London NY Overlap M30 | M30 | 5 min | 1.0R | 0.5 | false | StopMode=1, StopBufferATR=0.05 |

## Session-exit caveat

Some native tests reject scheduled closes because the broker reports Market closed. Intraday strategies can therefore hold beyond their intended exit. Their actual ledger, including resulting swap, is retained rather than inventing a timely exit. A broker-session-aware exit audit is required before any US500 promotion. Overnight and multi-hour DMC/Month-End positions are not inherently violations.

| Preset | Overnight trades (NY dates) | Intraday exits >1 minute late | Market-closed messages |
|---|---:|---:|---|
| DMC Fresh Reaction US100 | 6 | N/A | False |
| Nasdaq 5M Candle Momentum | 8 | 11 | True |
| US100 Month End Flow | 1 | N/A | True |
| Nasdaq Overnight | 74 | N/A | True |
| Sell Nasdaq 15min (recommended dynamic) | 0 | 0 | False |
| US100 H1 ORB 13UTC | 0 | 0 | False |
| US100 ORB New York M30 | 1 | 1 | True |
| US100 Selective ORB V3 | 0 | 0 | False |
| ORB Volume Profile (XAU preset) | 0 | 0 | False |
| ORB Volume Confirmed (XAU preset) | 0 | 0 | False |
| XAU ORB New York M30 | 0 | 0 | False |
| XAU ORB London NY Overlap M30 | 0 | 0 | False |

## Tick-history date segments

These partition the original full-year ledger by entry date; they are not independently restarted accounts. January onward is where broker real ticks become available, not a promise that every tick is real. Entries before January can close later.

| Preset | Entry-date segment | Trades | Net USD | Net PF |
|---|---|---:|---:|---:|
| DMC Fresh Reaction US100 | Before real-tick availability | 9 | -496.58 | 0.18 |
| DMC Fresh Reaction US100 | Real-tick-available dates | 14 | -260.68 | 0.70 |
| Nasdaq 5M Candle Momentum | Before real-tick availability | 72 | +1406.89 | 1.31 |
| Nasdaq 5M Candle Momentum | Real-tick-available dates | 184 | +767.15 | 1.06 |
| US100 Month End Flow | Before real-tick availability | 9 | +197.88 | 1.47 |
| US100 Month End Flow | Real-tick-available dates | 25 | +861.83 | 1.65 |
| Nasdaq Overnight | Before real-tick availability | 12 | +136.48 | 4.95 |
| Nasdaq Overnight | Real-tick-available dates | 62 | +438.28 | 1.74 |
| Sell Nasdaq 15min (recommended dynamic) | Before real-tick availability | 16 | +1071.97 | 2.40 |
| Sell Nasdaq 15min (recommended dynamic) | Real-tick-available dates | 28 | -258.02 | 0.86 |
| US100 H1 ORB 13UTC | Before real-tick availability | 15 | +605.53 | 2.13 |
| US100 H1 ORB 13UTC | Real-tick-available dates | 54 | +1077.88 | 1.38 |
| US100 ORB New York M30 | Before real-tick availability | 2 | -206.38 | 0.00 |
| US100 ORB New York M30 | Real-tick-available dates | 15 | -325.08 | 0.68 |
| US100 Selective ORB V3 | Before real-tick availability | 2 | -103.39 | 0.00 |
| US100 Selective ORB V3 | Real-tick-available dates | 3 | -130.11 | 0.00 |
| ORB Volume Profile (XAU preset) | Before real-tick availability | 4 | -59.68 | 0.81 |
| ORB Volume Profile (XAU preset) | Real-tick-available dates | 13 | -406.06 | 0.45 |
| ORB Volume Confirmed (XAU preset) | Before real-tick availability | 3 | +42.88 | 1.21 |
| ORB Volume Confirmed (XAU preset) | Real-tick-available dates | 3 | -210.13 | 0.00 |
| XAU ORB New York M30 | Before real-tick availability | 0 | +0.00 | N/A |
| XAU ORB New York M30 | Real-tick-available dates | 0 | +0.00 | N/A |
| XAU ORB London NY Overlap M30 | Before real-tick availability | 3 | -306.52 | 0.00 |
| XAU ORB London NY Overlap M30 | Real-tick-available dates | 19 | +390.51 | 1.85 |

## Monthly net USD / trade count

### DMC Fresh Reaction US100

| Month | Trades | Wins | Net USD | Commission | Swap |
|---|---:|---:|---:|---:|---:|
| 2025-09 | 1 | 0 | -110.98 | -1.52 | -9.06 |
| 2025-10 | 3 | 2 | -27.45 | -3.14 | -3.66 |
| 2025-11 | 2 | 1 | -62.10 | -2.34 | 0.00 |
| 2025-12 | 3 | 0 | -296.05 | -4.77 | 0.00 |
| 2026-01 | 3 | 1 | -161.99 | -4.34 | 0.00 |
| 2026-02 | 3 | 2 | +118.56 | -2.84 | -4.73 |
| 2026-03 | 2 | 0 | -192.93 | -1.58 | -2.84 |
| 2026-04 | 3 | 1 | -20.17 | -2.17 | -12.60 |
| 2026-06 | 2 | 0 | -185.96 | -2.30 | 0.00 |
| 2026-08 | 1 | 1 | +181.81 | -1.33 | 0.00 |

### Nasdaq 5M Candle Momentum

| Month | Trades | Wins | Net USD | Commission | Swap |
|---|---:|---:|---:|---:|---:|
| 2025-09 | 8 | 3 | +72.68 | -17.73 | 0.00 |
| 2025-10 | 23 | 10 | +444.83 | -42.22 | 0.00 |
| 2025-11 | 19 | 7 | +458.86 | -27.43 | 0.00 |
| 2025-12 | 22 | 9 | +430.52 | -41.43 | -85.86 |
| 2026-01 | 21 | 6 | -610.89 | -35.66 | 0.00 |
| 2026-02 | 18 | 9 | +931.37 | -25.28 | -16.98 |
| 2026-03 | 23 | 8 | -14.76 | -20.70 | -18.10 |
| 2026-04 | 21 | 11 | +639.46 | -31.19 | 0.00 |
| 2026-05 | 21 | 7 | -783.61 | -37.15 | 0.00 |
| 2026-06 | 22 | 8 | +330.16 | -28.00 | -24.37 |
| 2026-07 | 23 | 9 | +250.21 | -34.17 | -63.96 |
| 2026-08 | 21 | 9 | +159.33 | -36.96 | 0.00 |
| 2026-09 | 14 | 4 | -134.12 | -22.20 | 0.00 |

### US100 Month End Flow

| Month | Trades | Wins | Net USD | Commission | Swap |
|---|---:|---:|---:|---:|---:|
| 2025-10 | 3 | 1 | +38.78 | -7.23 | 0.00 |
| 2025-11 | 3 | 2 | +96.08 | -4.06 | 0.00 |
| 2025-12 | 3 | 2 | +63.02 | -5.29 | 0.00 |
| 2026-01 | 2 | 0 | -209.71 | -3.62 | 0.00 |
| 2026-02 | 3 | 1 | -165.52 | -3.88 | 0.00 |
| 2026-03 | 3 | 2 | +313.55 | -2.27 | 0.00 |
| 2026-04 | 2 | 1 | +249.04 | -1.90 | 0.00 |
| 2026-05 | 3 | 1 | -57.35 | -5.30 | 0.00 |
| 2026-06 | 3 | 2 | +421.26 | -6.55 | 0.00 |
| 2026-07 | 3 | 1 | -96.26 | -6.16 | -58.76 |
| 2026-08 | 3 | 2 | +295.58 | -5.23 | 0.00 |
| 2026-09 | 3 | 1 | +111.24 | -4.46 | 0.00 |

### Nasdaq Overnight

| Month | Trades | Wins | Net USD | Commission | Swap |
|---|---:|---:|---:|---:|---:|
| 2025-09 | 3 | 2 | -6.13 | -0.57 | -3.39 |
| 2025-10 | 9 | 8 | +142.61 | -1.71 | -14.68 |
| 2026-03 | 11 | 7 | +173.68 | -2.14 | -19.79 |
| 2026-04 | 6 | 4 | +54.16 | -1.09 | -8.85 |
| 2026-05 | 6 | 5 | +34.82 | -1.08 | -8.49 |
| 2026-06 | 10 | 7 | +97.48 | -1.79 | -14.84 |
| 2026-07 | 11 | 8 | -12.47 | -1.98 | -13.75 |
| 2026-08 | 9 | 6 | +54.28 | -1.53 | -13.31 |
| 2026-09 | 9 | 4 | +36.33 | -1.55 | -11.37 |

### Sell Nasdaq 15min (recommended dynamic)

| Month | Trades | Wins | Net USD | Commission | Swap |
|---|---:|---:|---:|---:|---:|
| 2025-10 | 5 | 1 | -32.89 | -8.71 | 0.00 |
| 2025-11 | 4 | 2 | +111.79 | -4.44 | 0.00 |
| 2025-12 | 7 | 4 | +993.07 | -13.61 | 0.00 |
| 2026-01 | 4 | 1 | -177.00 | -6.91 | 0.00 |
| 2026-02 | 3 | 2 | +539.86 | -5.84 | 0.00 |
| 2026-03 | 3 | 1 | -111.89 | -2.57 | 0.00 |
| 2026-04 | 4 | 0 | -372.25 | -4.87 | 0.00 |
| 2026-05 | 4 | 0 | -439.18 | -4.66 | 0.00 |
| 2026-06 | 1 | 0 | -106.83 | -0.88 | 0.00 |
| 2026-07 | 3 | 2 | +300.30 | -4.20 | 0.00 |
| 2026-08 | 3 | 1 | +47.25 | -5.14 | 0.00 |
| 2026-09 | 3 | 2 | +61.72 | -4.03 | 0.00 |

### US100 H1 ORB 13UTC

| Month | Trades | Wins | Net USD | Commission | Swap |
|---|---:|---:|---:|---:|---:|
| 2025-09 | 1 | 1 | +276.55 | -2.30 | 0.00 |
| 2025-10 | 7 | 6 | +250.61 | -5.78 | 0.00 |
| 2025-11 | 3 | 1 | +83.39 | -4.78 | 0.00 |
| 2025-12 | 4 | 2 | -5.02 | -6.16 | 0.00 |
| 2026-01 | 11 | 6 | +784.89 | -16.23 | 0.00 |
| 2026-02 | 7 | 4 | +894.34 | -11.08 | 0.00 |
| 2026-03 | 6 | 4 | +354.20 | -4.17 | 0.00 |
| 2026-04 | 4 | 2 | -60.31 | -3.67 | 0.00 |
| 2026-05 | 8 | 3 | -378.25 | -7.20 | 0.00 |
| 2026-06 | 5 | 3 | +60.15 | -3.70 | 0.00 |
| 2026-07 | 2 | 1 | -63.96 | -1.65 | 0.00 |
| 2026-08 | 6 | 1 | -452.63 | -8.76 | 0.00 |
| 2026-09 | 5 | 3 | -60.55 | -5.30 | 0.00 |

### US100 ORB New York M30

| Month | Trades | Wins | Net USD | Commission | Swap |
|---|---:|---:|---:|---:|---:|
| 2025-09 | 1 | 0 | -101.37 | -1.11 | 0.00 |
| 2025-12 | 1 | 0 | -105.01 | -3.55 | 0.00 |
| 2026-01 | 1 | 0 | -101.80 | -3.09 | 0.00 |
| 2026-02 | 2 | 0 | -201.87 | -1.99 | 0.00 |
| 2026-03 | 4 | 1 | +173.30 | -4.11 | -23.60 |
| 2026-04 | 2 | 1 | +20.01 | -3.63 | 0.00 |
| 2026-05 | 1 | 1 | +43.47 | -1.24 | 0.00 |
| 2026-07 | 1 | 0 | -100.72 | -1.51 | 0.00 |
| 2026-09 | 4 | 1 | -157.47 | -8.51 | 0.00 |

### US100 Selective ORB V3

| Month | Trades | Wins | Net USD | Commission | Swap |
|---|---:|---:|---:|---:|---:|
| 2025-09 | 1 | 0 | -102.22 | -2.08 | 0.00 |
| 2025-10 | 1 | 0 | -1.17 | -1.01 | 0.00 |
| 2026-01 | 1 | 0 | -2.58 | -1.01 | 0.00 |
| 2026-03 | 1 | 0 | -25.59 | -0.60 | 0.00 |
| 2026-05 | 1 | 0 | -101.94 | -1.11 | 0.00 |

### ORB Volume Profile (XAU preset)

| Month | Trades | Wins | Net USD | Commission | Swap |
|---|---:|---:|---:|---:|---:|
| 2025-10 | 1 | 1 | +249.15 | -1.36 | 0.00 |
| 2025-11 | 3 | 0 | -308.83 | -3.80 | 0.00 |
| 2026-01 | 1 | 1 | +47.76 | -2.00 | 0.00 |
| 2026-03 | 3 | 1 | +14.50 | -2.44 | 0.00 |
| 2026-04 | 1 | 0 | -29.97 | -1.29 | 0.00 |
| 2026-05 | 3 | 1 | -59.48 | -4.48 | 0.00 |
| 2026-07 | 1 | 0 | -102.68 | -1.80 | 0.00 |
| 2026-08 | 1 | 1 | +25.50 | -1.27 | 0.00 |
| 2026-09 | 3 | 0 | -301.69 | -3.96 | 0.00 |

### ORB Volume Confirmed (XAU preset)

| Month | Trades | Wins | Net USD | Commission | Swap |
|---|---:|---:|---:|---:|---:|
| 2025-10 | 1 | 1 | +249.15 | -1.36 | 0.00 |
| 2025-11 | 2 | 0 | -206.27 | -1.76 | 0.00 |
| 2026-05 | 1 | 0 | -2.99 | -2.02 | 0.00 |
| 2026-09 | 2 | 0 | -207.14 | -2.36 | 0.00 |

### XAU ORB New York M30

| Month | Trades | Wins | Net USD | Commission | Swap |
|---|---:|---:|---:|---:|---:|

### XAU ORB London NY Overlap M30

| Month | Trades | Wins | Net USD | Commission | Swap |
|---|---:|---:|---:|---:|---:|
| 2025-10 | 1 | 0 | -103.13 | -2.68 | 0.00 |
| 2025-11 | 2 | 0 | -203.39 | -5.35 | 0.00 |
| 2026-01 | 5 | 3 | +160.55 | -23.34 | 0.00 |
| 2026-02 | 4 | 4 | +369.77 | -14.36 | 0.00 |
| 2026-03 | 4 | 0 | -112.67 | -7.43 | 0.00 |
| 2026-04 | 1 | 1 | +95.51 | -3.02 | 0.00 |
| 2026-05 | 2 | 1 | +93.76 | -3.46 | 0.00 |
| 2026-06 | 3 | 0 | -216.41 | -7.24 | 0.00 |

