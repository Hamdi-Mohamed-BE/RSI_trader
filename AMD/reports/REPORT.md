# Confirmed AMD Sweep/Retest Backtest

- Period: **2025-07-30T00:00:00+00:00 to 2026-07-30T00:00:00+00:00**
- Data source: **MT5 / MEXAtlantic-Demo**
- Starting balance: **$1,000.00 per symbol**
- Risk: **3.00% of current balance per trade**
- Accumulation: **full-wick Asia range, 00:00-08:00 UTC**
- Manipulation entry: **M5 sweep outside the range and close back inside**
- Distribution entry: **M5 close outside, pullback to the range edge, and directional M5 close**
- Sessions: **London**
- Target: **1.50R fade / 1.50R distribution**
- Management: **at +0.30R, stop advances to +0.15R**
- Maximum trades per day: **1**
- Signals use completed M5 candles and enter no earlier than the next M1 candle.
- Conservative rule: if SL and TP occur in one M1 bar, SL is assumed first.

| Symbol | Trades | Wins | Losses | Win rate | PF | Net R | Realized max DD | Ending balance |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| XAUUSD (XAUUSD..) | 67 | 57 | 10 | 85.07% | 1.97 | 10.70R | 6.66% | $1359.44 |
| US30 (US30) | 19 | 16 | 3 | 84.21% | 2.08 | 3.45R | 5.06% | $1104.11 |
| US100 (NAS100U6) | 7 | 4 | 3 | 57.14% | 0.62 | -1.05R | 8.32% | $966.68 |
| BTCUSD (BTCUSD) | 47 | 29 | 18 | 61.70% | 0.74 | -4.20R | 23.55% | $868.17 |
| ETHUSD (ETHUSD) | 5 | 4 | 1 | 80.00% | 1.87 | 0.95R | 3.00% | $1027.40 |
| EURUSD (EURUSD..) | 0 | 0 | 0 | 0.00% | 0.00 | 0.00R | 0.00% | $1000.00 |
| GBPJPY (GBPJPY..) | 0 | 0 | 0 | 0.00% | 0.00 | 0.00R | 0.00% | $1000.00 |
| XAGUSD (XAGUSD..) | 19 | 6 | 13 | 31.58% | 0.28 | -9.40R | 28.71% | $748.28 |
| XPTUSD (XPTUSD..) | 14 | 2 | 12 | 14.29% | 0.03 | -11.70R | 29.99% | $700.10 |
