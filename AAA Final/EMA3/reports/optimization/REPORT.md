# EMA3 Exit Optimization

Period: 2025-08-02T03:07:22.196198+00:00 to 2026-08-02T03:07:22.196198+00:00
Training ends: 2026-05-02T21:07:22.196198+00:00; everything after it is unseen validation.
Configurations tested per symbol: 23
Signal definition: pivot 5; filter ema200_slope (6 H4 slope bars)

## Best training-selected exit per symbol

| Symbol | Exit | Train trades | Train PF | Validation trades | Validation WR | Validation PF | Validation net R | Validation DD | Last-30d PF |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| US30 | fixed_5R | 13 | 2.22 | 2 | 100.0% | inf | 6.61 | 0.00% | 0.00 |
| XAGUSD | trail_start_2R_distance_1R | 32 | 3.65 | 5 | 60.0% | 4.74 | 3.79 | 1.00% | 117.48 |
| ETHUSD | fixed_5R | 30 | 1.92 | 10 | 30.0% | 2.47 | 8.94 | 4.00% | 0.00 |
| XAUUSD | trail_start_2R_distance_2R | 16 | 5.06 | 9 | 44.4% | 1.61 | 3.06 | 2.97% | inf |
| BTCUSD | fixed_3R | 36 | 1.28 | 18 | 33.3% | 1.01 | 0.13 | 6.77% | 0.02 |
| GBPJPY | fixed_1R | 38 | 1.66 | 18 | 44.4% | 0.73 | -2.65 | 3.88% | 1.42 |
| GBPUSD | trail_start_1R_distance_2R | 22 | 2.05 | 12 | 16.7% | 0.57 | -3.47 | 7.79% | 0.00 |
| EURJPY | fixed_2R | 26 | 1.58 | 12 | 16.7% | 0.41 | -5.64 | 7.39% | 0.00 |

## Validation portfolio

- Accepted trades: **24**
- Exposure skips: **0**
- Win rate: **41.67%**
- Profit factor: **2.31**
- Net R: **15.79R**
- Ending balance: **$1,157.26**
- Return: **15.73%**
- Max realized DD: **4.92%**

Only symbols with at least the configured validation trade count,
positive validation net R, and validation PF >= 1.20 enter the mix.
