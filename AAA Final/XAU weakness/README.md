# XAU Weakness

M15 XAUUSD breakout system:

1. A completed bearish impulse must exceed the configured ATR threshold.
2. Price must reject the same resistance twice, with a configurable separation and tolerance.
3. After the second M15 candle closes, the bot places a buy stop above resistance.
4. The stop is below the observed consolidation floor; the target is 1R or 2R.
5. The pending order expires or is canceled if the range floor fails before entry.

The optimizer uses a chronological 67% training / 17% validation / 16% untouched holdout split. Live execution uses the currently connected MT5 account and automatically discovers the broker's XAUUSD alias.
