# Confirmed AMD Sweep/Retest Backtest

- Period: **2026-06-02T00:00:00+00:00 to 2026-08-01T00:00:00+00:00**
- Data source: **MT5 / MEXAtlantic-Demo**
- Starting balance: **$1,000.00 per symbol**
- Risk: **1.00% of current balance per trade**
- Accumulation: **full-wick Asia range, 00:00-08:00 UTC**
- Manipulation entry: **M5 sweep outside the range and close back inside**
- Distribution entry: **M5 close outside, pullback to the range edge, and directional M5 close**
- Sessions: **London**
- Target: **1.70R fade / 1.70R distribution**
- Management: **at +0.30R, stop advances to +0.15R**
- Maximum trades per day: **1**
- Signals use completed M5 candles and enter no earlier than the next M1 candle.
- Conservative rule: if SL and TP occur in one M1 bar, SL is assumed first.

| Symbol | Trades | Wins | Losses | Win rate | PF | Net R | Realized max DD | Ending balance |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| XAUUSD (XAUUSD..) | 11 | 10 | 1 | 90.91% | 4.71 | 3.85R | 1.00% | $1038.95 |
