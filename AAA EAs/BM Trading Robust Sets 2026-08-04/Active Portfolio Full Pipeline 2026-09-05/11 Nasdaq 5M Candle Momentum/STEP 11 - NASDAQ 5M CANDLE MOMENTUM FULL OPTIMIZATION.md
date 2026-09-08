# Step 11 — Nasdaq 5M Candle Momentum full optimization

## Decision

Promote **fixed-rr2.5** because it passed the frozen locked-year gate.

Every native test used Exness USTEC, a $10,000 account and exactly 1% equity risk per trade. Development used M1 OHLC for search speed. The untouched locked year and exact three-year finalists used MT5 Every Tick with random execution delay.

## Frozen comparison

| Window / configuration | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| Development — current | +30.00% | 1.13 | 55.66% | 28.39% | 512 | 2.18 | 1.05 |
| Development — frozen challenger | +47.63% | 1.14 | 40.32% | 14.21% | 506 | 2.45 | 2.09 |
| Locked year — current | +34.98% | 1.25 | 55.04% | 11.92% | 258 | 4.73 | 2.02 |
| Locked year — frozen challenger | +38.12% | 1.21 | 41.41% | 12.12% | 256 | 4.01 | 2.17 |
| Exact 3 years — current | +64.30% | 1.16 | 54.94% | 32.40% | 770 | 2.68 | 1.96 |
| Exact 3 years — frozen challenger | +100.07% | 1.17 | 40.29% | 16.26% | 762 | 2.89 | 3.83 |
| Exact 3 years — challenger Full Safe | +21.15% | 1.18 | 40.74% | 19.12% | 189 | 3.59 | 1.09 |

## Monte Carlo — 10,000 five-trade block paths from exact three-year net trades

| Configuration | Return P5 | Median | Return P95 | P95 DD | Profitable paths | P(DD >= 20%) |
|---|---:|---:|---:|---:|---:|---:|
| Current | -11.64% | +62.73% | +204.82% | 39.64% | 90.42% | 68.38% |
| Frozen challenger | +0.60% | +99.29% | +288.33% | 39.76% | 95.12% | 72.82% |

## What was tested

- RR targets from 0.5R through 5R, plus nine adaptive-RR rules.
- ATR stops from 1–5 ATR and signal-candle stops with four buffers.
- M1, M5, M15 and M30 signals.
- New York 09:30 baseline plus Asia, London, overlap and 10:00 New York standalone anchors.
- Both directions, long-only and short-only.
- No management, ATR trailing, breakeven and Dynamic 50/20 variants.
- EMA slope, candle-body, EMA-distance and relative-volume filters.

The completed-D1 Full Safe gate was also applied to the selected 2.5R configuration. It returned +21.15% with PF 1.18, a 40.74% win rate and 19.12% drawdown across 189 exact three-year trades, so Standard remains the recommended mode.

Alternate anchors are separate once-daily momentum hypotheses, not generic session filters. The original rule only fires at 09:30 New York, so applying an Asia/London gate to it would merely produce zero trades.

The complete development table is in `all-results.csv`; exact inputs are retained in `Sets`. Full MT5 reports and reconciled trade ledgers are retained in `Reports`.

Historical results are not a guarantee of future performance.
