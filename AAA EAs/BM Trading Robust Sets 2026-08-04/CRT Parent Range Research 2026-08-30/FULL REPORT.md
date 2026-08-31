# CRT parent-range — multi-market MT5 audit

Development selected one universal configuration for every market: `h4-daily-bias`. The locked year was then run without per-symbol parameter changes.

| Verdict | Market | Group | Return | PF | Win rate | Equity DD | Trades | Final |
|---|---|---|---:|---:|---:|---:|---:|---:|
| WATCH | US500 | Index | +5.47% | 1.08 | 39.45% | 10.93% | 109 | $10,546.93 |
| WATCH | USTEC | Index | +1.08% | 1.01 | 40.65% | 12.49% | 123 | $10,107.90 |
| REJECT | XAUUSD | Metal | -1.91% | 0.97 | 40.16% | 12.65% | 127 | $9,808.51 |
| REJECT | BTCUSD | Crypto | -13.07% | 0.87 | 38.04% | 18.46% | 184 | $8,692.73 |
| REJECT | AUDUSD | Forex | -13.38% | 0.81 | 36.97% | 19.49% | 119 | $8,662.03 |
| REJECT | GBPUSD | Forex | -15.56% | 0.76 | 37.50% | 22.16% | 112 | $8,444.31 |
| REJECT | USDCAD | Forex | -17.89% | 0.80 | 36.96% | 22.09% | 138 | $8,211.02 |
| REJECT | EURUSD | Forex | -24.51% | 0.67 | 33.33% | 33.04% | 123 | $7,549.20 |
| REJECT | USDJPY | Forex | -24.87% | 0.65 | 33.08% | 29.78% | 130 | $7,512.59 |
| REJECT | NZDUSD | Forex | -26.43% | 0.59 | 31.82% | 32.21% | 110 | $7,356.67 |
| REJECT | USDCHF | Forex | -27.77% | 0.65 | 34.09% | 32.49% | 132 | $7,223.06 |

- Profitable locked markets: 2/11.
- Mean locked return: -14.44%.
- $10,000 initial balance, 1% equity risk, Exness MT5 Every Tick, random execution delay, spread, commission and swap included.
- Development: 2024-08-29 to 2025-08-28; untouched locked test: 2025-08-29 to 2026-08-28.
- The EA uses completed candles only: parent range, one-side raid, close back inside, structural stop and the opposite parent boundary as target.
- No active BAT or website file was changed.

## Asset-specific development exceptions

Two configurations that were positive in development but differed from the universal winner received separate untouched locked tests:

| Market | Configuration | Development return / PF | Locked return / PF | Locked DD | Verdict |
|---|---|---:|---:|---:|---|
| XAUUSD | H4 core | +16.38% / 1.14 | -3.82% / 0.97 | 17.32% | Reject |
| USDJPY | H4 core | +33.52% / 1.22 | -38.53% / 0.67 | 40.25% | Reject |

These reversals are direct evidence that the apparent development edges were not stable.
