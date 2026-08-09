# Gold Liquidity Sweep EA — mechanical translation

## What the transcript actually specifies

1. Trade XAUUSD in the direction of aligned H1 and M15 market structure.
2. Wait for price to return to a M15 supply/demand point of interest.
3. Require a lower-timeframe liquidity sweep.
4. Enter either immediately after the sweep or after extra confirmation/market shift.
5. Keep a hard stop beyond the protected sweep candle.
6. Target the nearest logical M15 swing rather than an unlimited move.

## Objective implementation

- Trend: the two most recent confirmed swing highs and lows on H1 and M15 must both be rising for longs or both falling for shorts.
- Point of interest: the full range of the most recent opposite-colour M15 candle immediately preceding an ATR-sized displacement that closes beyond earlier structure. A zone is invalid after a close through its far edge.
- Liquidity sweep: an M5 candle trades beyond the latest confirmed M5 pivot and closes back through it with the configured recovery fraction.
- Aggressive entry: market entry after the sweep candle closes.
- Momentum entry: wait for a directional candle that closes beyond the sweep candle.
- Market-shift/retest entry: wait for a close beyond the opposite M5 pivot, then a retest of the break candle's origin.
- Stop: always remains beyond the sweep extreme plus an ATR buffer. The EA never copies the video's discretionary stop removal.
- Target: nearest confirmed M15 swing in the trade direction, subject to a minimum RR and a 3R cap.
- Risk: 1% of current equity, maximum two entries per UTC day, three-hour time exit.

## Limits

Supply/demand zones, order blocks, liquidity and market shifts are described visually and subjectively in the video. No algorithm can reproduce the speaker's drawings or “gut feeling” exactly from a transcript. This EA is a reproducible hypothesis built from those concepts, not a claim that it duplicates the showcased USD 566,000 result.
