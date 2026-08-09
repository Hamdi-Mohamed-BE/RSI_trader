# NQ Drift VWAP Pullback EA — transcript specification

## Exact rules implemented

- Instrument: Exness USTEC as the available NASDAQ-100 CFD proxy for NQ futures.
- Signal chart: M5. VWAP calculations: M15 bars.
- VWAP anchor: 09:30 New York, with automatic US daylight-saving conversion.
- No trades before 10:30 New York. No new entries from 15:30. Force-flat at 15:55.
- Long drift: latest completed M15 close above session VWAP, VWAP higher than its value one M15 bar earlier, and M15 price up at least 0.1% across four bars (one hour).
- Short drift: exact mirror.
- Long trigger: a red M5 candle while long drift is active. Short trigger: a green M5 candle while short drift is active. Entry is a market order at the next bar.
- Stop: 80 NASDAQ index points. Long target: 40 points. Short target: 50 points.
- One position at a time, maximum four entries and maximum two losing exits per New York day.
- Risk: 1% of current equity per stopped trade for portfolio testing.

## Broker-data limitation

The video uses NASDAQ-100 futures and centralized futures volume. Exness USTEC is an OTC CFD; its M15 VWAP is weighted with broker tick volume. The rules are reproducible, but this is not the same data or execution venue as NQ futures and must be validated independently rather than assuming the video's reported statistics transfer.
