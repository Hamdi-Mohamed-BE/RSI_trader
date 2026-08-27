# XAU Weakness multi-timeframe bias-filter research

Research date: 2026-08-25

Decision: **do not add a bias filter to the active BAT version.** The best training candidate, H4, reduced the training loss but failed to improve the locked final-year result.

## Definition tested

A timeframe is bullish when the last closed candle is above EMA(50) and EMA(50) is higher than it was three closed candles earlier. Bearish is the inverse. H1, H4 and D1 were tested independently and as any-one, two-of-three majority, and all-three combinations.

Two forms were tested:

- Buy gate: long entries require bullish bias; short entries remain unchanged.
- Symmetric gate: long entries require bullish bias and short entries require bearish bias.

All runs use Exness XAUUSD M15, USD 10,000 initial balance, 1% risk per trade and the active XAU Weakness RR 2 setup.

## Training screen: 2021-08-11 through 2025-08-10

MT5 one-minute-OHLC screening model.

| Variant | Return | PF | Win rate | Max equity DD | Trades |
|---|---:|---:|---:|---:|---:|
| Symmetric H4 | -11.24% | 0.98 | 34.97% | 47.17% | 1,178 |
| Buy-only H4 | -18.47% | 0.97 | 34.74% | 49.59% | 1,255 |
| Symmetric majority | -27.11% | 0.95 | 34.46% | 55.80% | 1,242 |
| Buy-only majority | -30.09% | 0.94 | 34.29% | 55.19% | 1,318 |
| Buy-only all three | -31.05% | 0.95 | 33.84% | 52.26% | 1,253 |
| Baseline / no bias | -32.72% | 0.94 | 34.88% | 57.07% | 1,207 |
| Symmetric all three | -37.17% | 0.89 | 33.33% | 55.25% | 747 |
| Symmetric D1 | -38.43% | 0.92 | 33.83% | 52.58% | 1,076 |
| Buy-only D1 | -42.18% | 0.92 | 33.70% | 56.81% | 1,169 |
| Buy-only any one | -44.98% | 0.91 | 34.08% | 65.21% | 1,297 |
| Symmetric any one | -45.77% | 0.91 | 34.06% | 65.84% | 1,292 |
| Buy-only H1 | -52.44% | 0.90 | 33.66% | 71.97% | 1,438 |
| Symmetric H1 | -57.92% | 0.88 | 33.31% | 74.85% | 1,411 |

Every training variant lost money. H4 was merely the least-bad filter, so it was carried forward without re-optimizing it on the validation year.

## Locked MT5 every-tick validation: 2025-08-11 through 2026-08-10

| Variant | Return | PF | Win rate | Max equity DD | Trades |
|---|---:|---:|---:|---:|---:|
| Baseline / no bias | **+11.42%** | **1.06** | **35.84%** | 17.60% | 279 |
| Symmetric H4 | +7.62% | 1.04 | 35.31% | **17.28%** | 303 |
| Buy-only H4 | +5.48% | 1.03 | 35.03% | 18.04% | 314 |

The symmetric H4 filter gives up 3.80 percentage points of return for only 0.32 percentage points less drawdown. The buy-only H4 filter is worse on return, PF, win rate and drawdown. Neither passes.

The EA and reports in this folder are isolated research artifacts. The active EA, SET files and installer BAT were not changed.
