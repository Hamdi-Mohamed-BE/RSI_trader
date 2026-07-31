# Confirmed AMD Sweep/Retest Backtest

- Period: **2024-07-30T00:00:00+00:00 to 2025-07-30T00:00:00+00:00**
- Data source: **MT5 / MEXAtlantic-Demo**
- Starting balance: **$1,000.00 per symbol**
- Risk: **3.00% of current balance per trade**
- Accumulation: **full-wick Asia range, 00:00-08:00 UTC**
- Manipulation entry: **M5 sweep outside the range and close back inside**
- Distribution entry: **M5 close outside, pullback to the range edge, and directional M5 close**
- Sessions: **London**
- Target: **2.00R fade / 2.00R distribution**
- Management: **at +0.30R, stop advances to +0.15R**
- Maximum trades per day: **1**
- Signals use completed M5 candles and enter no earlier than the next M1 candle.
- Conservative rule: if SL and TP occur in one M1 bar, SL is assumed first.

| Symbol | Trades | Wins | Losses | Win rate | PF | Net R | Realized max DD | Ending balance |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| XAUUSD (XAUUSD..) | 38 | 24 | 14 | 63.16% | 0.60 | -4.85R | 24.64% | $854.42 |
