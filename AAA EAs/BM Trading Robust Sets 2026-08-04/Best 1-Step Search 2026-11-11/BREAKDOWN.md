# Best 1-Step full breakdown (ledger overlay, equal risk per trade, no guard)

| Window | Trades | /month | /day | Total R | at 0.5% | PF | Win % | Avg R | Closed DD R | Worst day R |
|---|---|---|---|---|---|---|---|---|---|---|
| dev | 3652 | 62.7 | 2.98 | 166.1 | 83.0% | 1.1 | 48.7 | 0.045 | 45.3 | -6.58 |
| val | 809 | 67.3 | 3.2 | 174.5 | 87.2% | 1.53 | 51.9 | 0.216 | 22.7 | -4.78 |
| oos | 1578 | 65.8 | 3.13 | 308.7 | 154.3% | 1.49 | 54.4 | 0.196 | 25.9 | -5.33 |
| all | 6039 | 64.0 | 3.05 | 649.2 | 324.6% | 1.25 | 50.6 | 0.108 | 45.3 | -6.58 |
| last_year | 749 | 62.5 | 2.97 | 161.6 | 80.8% | 1.52 | 54.5 | 0.216 | 14.7 | -4.48 |
| last month | 71 | 67.5 | 3.22 | 35.5 | 17.8% | 2.31 | 57.7 | 0.5 | 6.0 | -5.35 |

Years (R): 2019 -38.4, 2020 66.0, 2021 -2.4, 2022 116.5, 2023 51.4, 2024 175.9, 2025 137.1, 2026 143.1

MC: resample red 0.0%, randomize red 0.0%, real DD worse than 95.8% of shuffles

Last month by week (R): 2026-W42 11.65, 2026-W43 4.05, 2026-W44 5.89, 2026-W45 10.95, 2026-W46 2.94

## EAs

| EA | Trades | /month | All R | PF | Win % | DD R | Dev R | Val R | OOS R | Last 12 m R | Last month n | Last month R |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Nasdaq 5M (REPLACE, DI OFF) | 1882 | 20.0 | 113.8 | 1.12 | 45.6 | 30.0 | 28.5 | 12.9 | 72.4 | 41.1 | 21 | 7.1 |
| USDJPY London | 731 | 7.8 | 104.3 | 1.46 | 46.6 | 10.1 | 41.9 | 36.8 | 25.7 | 21.7 | 8 | -2.6 |
| 3 Way Gold (breakout) | 640 | 6.8 | 79.7 | 1.43 | 73.1 | 16.6 | 37.0 | 15.7 | 27.0 | 8.6 | 5 | 2.2 |
| Sell Nasdaq 15min | 368 | 3.9 | 77.4 | 1.35 | 39.1 | 20.3 | 21.8 | 17.5 | 38.1 | 6.0 | 4 | 5.5 |
| EMA3 | 306 | 3.2 | 44.4 | 1.25 | 55.6 | 13.0 | 3.1 | 7.3 | 34.1 | 18.6 | 5 | 4.7 |
| ORB VP Volume Confirmed | 198 | 2.1 | 25.2 | 1.28 | 38.4 | 13.7 | 1.2 | 1.5 | 22.5 | 12.1 | 3 | 2.6 |
| XAU Squeeze | 210 | 2.2 | 23.8 | 1.33 | 41.0 | 9.9 | 0.5 | 19.2 | 4.1 | -1.9 | 0 | 0 |
| US100 Selective ORB V3 | 63 | 0.7 | 10.5 | 1.87 | 77.8 | 4.1 | 4.8 | 2.1 | 3.6 | 2.1 | 1 | -0.1 |
| XAU RSI VWAP | 404 | 4.3 | 8.2 | 1.06 | 69.1 | 21.3 | -16.8 | 11.3 | 13.6 | 4.4 | 7 | 0.5 |
| Overnight Bias ORB | 782 | 8.3 | 117.5 | 1.35 | 49.4 | 9.9 | 44.5 | 28.5 | 44.5 | 28.8 | 11 | 13.7 |
| Gold Band Wave | 455 | 4.8 | 44.3 | 1.22 | 44.0 | 19.1 | -0.4 | 21.7 | 23.1 | 20.0 | 6 | 1.9 |

## EA years (R)

| EA | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|
| Nasdaq 5M (REPLACE, DI OFF) | -6.9 | 9.9 | 11.2 | 26.8 | -11.8 | 24.6 | 28.8 | 31.1 |
| USDJPY London | -7.9 | 17.4 | 4.3 | 19.3 | 11.4 | 33.4 | 8.9 | 17.5 |
| 3 Way Gold (breakout) | 6.8 | 11.7 | -4.3 | 9.9 | 20.7 | 9.9 | 15.6 | 9.3 |
| Sell Nasdaq 15min | -5.7 | 15.0 | 3.3 | 4.1 | 1.4 | 23.5 | 32.1 | 3.7 |
| EMA3 | -7.1 | -1.4 | 0.8 | 7.5 | 5.5 | 4.8 | 17.8 | 16.6 |
| ORB VP Volume Confirmed | 1.9 | -7.6 | -4.2 | 8.0 | 0.0 | 5.1 | 8.8 | 13.1 |
| XAU Squeeze | -7.7 | 3.0 | -3.7 | 6.0 | 9.0 | 13.2 | 6.9 | -2.8 |
| US100 Selective ORB V3 | 1.3 | -0.6 | -1.4 | 3.5 | 1.0 | 3.1 | 2.0 | 1.6 |
| XAU RSI VWAP | -3.1 | -7.2 | -7.8 | 2.4 | 0.4 | 12.4 | 6.0 | 4.9 |
| Overnight Bias ORB | -4.1 | 11.7 | 3.9 | 26.2 | 11.9 | 34.0 | 6.5 | 27.3 |
| Gold Band Wave | -5.9 | 14.1 | -4.4 | 2.7 | 1.8 | 11.7 | 3.8 | 20.5 |

## Last month FTMO 1-Step replay (closed-trade, NO guard, recent2m.challenge, $100k)
Start 2026-10-10: pass day 21 at 0.5% (day 14 at 0.75%); start 10-12: day 19 (12); start 10-13: day 21 (18); start 10-20: BREACH day 16 at 0.5% and 0.75% (2026-11-04 = -5.35R:
Nasdaq 5M -1.03 / -1.02, Gold Band Wave -1.30, EMA3 -1.28, Overnight Bias ORB -1.06, USDJPY +0.35). The guard's 2.5% daily reserve would have blocked the later entries that day (not replayed).
$100k from 10-12 at 0.5% no guard: $119,161 by 11-10, never below $100,000; best day +$3,983 (10-30), worst -$2,673 (11-04).
Caveats: Core 9 members' all-years runs end 2026-11-01 (last month uses the separate r2m runs to 11-10); real DD worse than 95.8% of shuffles = CLUMPED losses
(plan DD = max(real, shuffle p95)); worst day -6.58R = -3.3% at 0.5% > FTMO 3% daily without the guard.
