# EMA3 risk progression / 1.7R study

- Symbol: **XAUUSD..**; timeframe: **H4**
- Period: **2025-08-02T06:07:43.094214+00:00 to 2026-08-02T06:07:43.094214+00:00**
- Base risk: **0.50%**
- Progression: **base x 1.6^loss_streak**, uncapped for research
- Target ceiling: **1.7R**

| Scenario | Trades | Win rate | R-PF | Cash PF | Net R | Ending balance | Return | Max DD | Max risk |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| flat_fixed_1_7r | 43 | 58.14% | 2.17 | 2.15 | +21.03R | $1,109.74 | 10.97% | 2.62% | 0.5000% |
| flat_trailing_cap_1_7r | 46 | 58.70% | 1.97 | 1.95 | +18.50R | $1,095.85 | 9.59% | 2.62% | 0.5000% |
| progression_fixed_1_7r | 43 | 58.14% | 2.17 | 2.56 | +21.03R | $1,208.11 | 20.81% | 2.57% | 2.0480% |
| progression_trailing_cap_1_7r | 46 | 58.70% | 1.97 | 2.40 | +18.50R | $1,195.16 | 19.52% | 2.57% | 2.0480% |

The progression scenarios intentionally have no research cap so the exact
0.5%, 0.8%, 1.28%, ... sequence is visible. Live defaults keep progression
disabled and impose a separate safety cap if it is manually enabled.
