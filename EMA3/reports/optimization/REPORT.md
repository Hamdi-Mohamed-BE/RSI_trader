# EMA3 Exit Optimization

Period: 2025-07-29T05:36:54.146188+00:00 to 2026-07-29T05:36:54.146188+00:00
Training ends: 2026-04-28T23:36:54.146188+00:00; everything after it is unseen validation.
Configurations tested per symbol: 23

## Best training-selected exit per symbol

| Symbol | Exit | Train trades | Train PF | Validation trades | Validation WR | Validation PF | Validation net R | Validation DD | Last-30d PF |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| XAGUSD | fixed_4R | 108 | 2.06 | 37 | 35.1% | 1.15 | 2.08 | 4.30% | 1.36 |
| ETHUSD | fixed_5R | 147 | 1.16 | 57 | 40.4% | 1.12 | 2.78 | 5.31% | 1.13 |
| GBPJPY | fixed_4R | 117 | 1.26 | 44 | 31.8% | 1.00 | -0.08 | 10.99% | 2.10 |
| XAUUSD | trail_start_1R_distance_1R | 113 | 1.24 | 42 | 35.7% | 0.86 | -2.13 | 8.73% | 3.76 |
| EURJPY | fixed_2.5R | 113 | 1.28 | 34 | 23.5% | 0.23 | -14.25 | 13.36% | 0.31 |

## Validation portfolio

- Accepted trades: **0**
- Exposure skips: **0**
- Win rate: **0.00%**
- Profit factor: **inf**
- Net R: **0.00R**
- Ending balance: **$1,000.00**
- Return: **0.00%**
- Max realized DD: **0.00%**

Only symbols with at least the configured validation trade count,
positive validation net R, and validation PF >= 1.20 enter the mix.
