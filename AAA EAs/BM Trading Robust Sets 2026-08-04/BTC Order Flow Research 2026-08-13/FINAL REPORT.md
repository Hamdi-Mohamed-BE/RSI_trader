# BTCUSDT Order-Flow EA Research — Final Report

## Verdict

**REJECTED for live trading and not added to the MT5 installer.**

The strict order-flow configuration produced **zero trades** in the untouched six-month holdout. Removing the historical book filter exposed a large loss. The training result was attractive but based on only 19 trades, and it did not survive the unseen period.

## Untouched holdout results

Test window: **2026-02-11 through 2026-08-10 UTC**. Initial balance: **$10,000**. Risk: **1% of current equity per trade**. Maximum notional leverage: **3x**.

| Test | Final balance | Net return | Profit factor | Win rate | Trades | Max equity drawdown | Decision |
|---|---:|---:|---:|---:|---:|---:|---|
| Full order-flow filter | $10,000.00 | 0.00% | N/A | N/A | 0 | 0.00% | Failed: no signals |
| CVD without book filter | $5,550.17 | -44.50% | 0.46 | 37.43% | 187 | 45.09% | Reject |
| Price sweep only | $3,293.99 | -67.06% | 0.49 | 37.74% | 371 | 67.52% | Reject |

The flat full-filter curve is not a safe result: it means the frozen signal stopped trading completely out of sample.

## Training result and why it was rejected

Training window: **2024-08-11 through 2026-02-10 UTC**, split into three independent six-month blocks.

The least-bad M15 reversal setting returned **+12.88%**, PF **4.36**, win rate **78.95%**, and max drawdown **1.91%**, but took only **19 trades**. The three blocks had 7, 3, and 9 trades. This is too sparse to support the apparent PF and win rate. None of the 600 screened candidates passed the robustness gate.

## Frozen strategy

- BTCUSDT USD-M perpetual, M15 decisions.
- Liquidity sweep and close-back-inside reversal.
- Opposing taker-flow/CVD condition.
- Depth imbalance at ±1% and ±5%, plus short-horizon replenishment.
- 48-bar sweep lookback and relative-volume filter.
- Stop: 1 ATR; target: 1.5R; break-even at 1.5R; maximum hold: 12 bars.
- Both long and short signals.

## Data and execution model

- 730 calendar days: **2024-08-11 through 2026-08-10**.
- **1,036,522** usable one-minute observations across all 730 days, approximately **98.6%** of possible minutes.
- Binance BTCUSDT futures OHLCV, taker-buy volume/CVD, book-depth bands, replenishment proxies, and **2,190 actual historical funding events**.
- Entry on the bar after a closed signal.
- Taker fee: **0.05% per side**.
- Slippage: **0.01% per side**.
- Actual Binance funding rates and mark prices included when applicable.
- If stop and target were both touched in the same bar, the stop was assumed first.
- Positions were forcibly closed across unusable data gaps.

## Historical-order-book limitation

The free Binance `bookDepth` archive is sampled aggregate depth, not tick-by-tick L2 queue replay. It can approximate broad bid/ask pressure but cannot faithfully reconstruct queue position, cancellations, spoofing, microsecond replenishment, heatmap behavior, or realistic passive fills. Therefore this is an honest low-frequency order-flow proxy test, not a full exchange-matching-engine simulation.

## Cost diagnosis

In the CVD-without-book holdout, fees alone totaled **$3,794.34**. The strategy was still negative before fees once modeled slippage is retained, so cheaper fees would not rescue the tested edge. The price-sweep-only version paid **$5,706.03** in fees and lost even more.

## Files

- `backtest_orderflow.py` — optimization, frozen holdout, ablation tests, costs, and graph generation.
- `download_and_normalize.py` — public Binance price, taker-flow, and depth normalization.
- `download_funding.py` — historical funding download.
- `Data/` — normalized two-year research dataset and metadata.
- `Results/final-results.json` — full machine-readable statistics.
- `Results/final-summary.csv` — compact final comparison.
- `Results/*-trades.csv` — trade-level audit files.
- `Results/*-equity.csv` — equity audit files.
- `Results/final-equity-comparison.png` — holdout equity chart.

## Deployment status

No `.mq5`/`.ex5` live EA was installed because the tested strategy failed validation. No active EA, BAT file, chart template, or current MT5 account was changed.

## Sensible next experiment

Record live BTCUSDT tick-by-tick L2 updates for at least 8–12 weeks, including trades, book deltas, cancels, and latency timestamps. Then test event-time features such as order-flow imbalance, queue depletion, replenishment velocity, and spoof-resistance under a fill model. Keep this separate from the active MT5 portfolio until a fresh untouched holdout is profitable after all costs.
