# Engineered-liquidity sweep — multi-market MT5 audit

This is an objective reconstruction of the supplied transcript, not the speaker's proprietary code. Each market's configuration was chosen using only the development year, then frozen for the untouched locked year.

| Verdict | Market | Selected configuration | Dev return | Dev PF | Locked return | Locked PF | Win rate | Equity DD | Trades |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| KEEP CANDIDATE | XAUUSD | h1-d1-reclaim | +17.52% | 1.25 | +18.29% | 1.27 | 34.41% | 12.61% | 93 |
| REJECT | USDJPY | m15-h4-displacement | +0.40% | 1.00 | +2.74% | 1.05 | 30.43% | 15.64% | 69 |
| REJECT | GBPUSD | h1-d1-reclaim | -7.79% | 0.86 | -6.99% | 0.85 | 26.23% | 21.31% | 61 |
| REJECT | USDCHF | m15-h4-displacement | -4.19% | 0.88 | -9.47% | 0.90 | 28.12% | 29.78% | 128 |
| REJECT | USDCAD | m15-h4-displacement | +1.95% | 1.10 | -12.29% | 0.83 | 25.84% | 22.39% | 89 |
| REJECT | AUDUSD | m30-h4-displacement | +3.72% | 1.14 | -12.77% | 0.36 | 16.67% | 12.98% | 24 |
| REJECT | USTEC | m30-h4-displacement | +14.25% | 1.32 | -13.16% | 0.73 | 22.95% | 25.79% | 61 |
| REJECT | BTCUSD | m30-h4-reclaim | +49.55% | 1.25 | -14.17% | 0.92 | 23.83% | 40.78% | 277 |
| REJECT | EURUSD | h1-d1-reclaim | +18.72% | 1.28 | -16.33% | 0.67 | 22.86% | 27.53% | 70 |
| REJECT | NZDUSD | h1-d1-reclaim | +7.74% | 1.95 | -18.01% | 0.65 | 22.39% | 24.15% | 67 |
| REJECT | ETHUSD | m15-h4-displacement | -8.12% | 0.75 | -19.98% | 0.80 | 24.32% | 34.88% | 148 |

- Strict keep candidates: 1/11.
- Profitable with PF above 1 in both periods: 1/11.
- Equal-weight locked overlay return: -9.29%.
- Equal-weight realized drawdown: 12.56 percentage points.
- Development: 2024-08-29 to 2025-08-28; untouched locked validation: 2025-08-29 to 2026-08-28.
- $10,000 initial balance, 1% equity risk, Exness MT5 Every Tick, random execution delay, spread, commission and swap included.
- Core rule: dominant EMA trend, confirmed internal swing sweep against the trend, reclaim close, structural stop beyond the sweep and prior opposing liquidity as target.
- All signals use completed bars. No locked-period result influenced configuration selection.
- No active installation BAT or website file was changed.
