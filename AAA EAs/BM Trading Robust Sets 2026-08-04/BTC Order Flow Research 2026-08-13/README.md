# BTC Order-Flow Research

This project is isolated from the active MT5 BAT and deployment pipeline.

## Data hypothesis

- Market: Binance USD-M perpetual `BTCUSDT`.
- Order-book input: Binance daily `bookDepth` archive, which contains timestamped aggregate bid/ask depth at percentage bands around price.
- Executed-flow input: Binance one-minute futures candles with taker-buy base and quote volume.
- Price/execution input: the same Binance `BTCUSDT` one-minute series.

The archive is not tick-by-tick Level 2. Results must be described as an aggregate-depth/CVD backtest, not a full queue-position or heatmap replay.

## Isolation guardrail

No active EA, BAT installer, MT5 profile, or live account is modified by this research.
