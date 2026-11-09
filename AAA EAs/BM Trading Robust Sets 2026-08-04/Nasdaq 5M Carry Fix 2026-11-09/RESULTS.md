# Nasdaq 5M carry fix: results (2026-11-09)

USTEC, native Model 4, 150 ms, $10k, 1%, 2019-07-16 to 2026-11-10, production EX5 `fe9f391db5af` with the Edge 10 inputs.
- **Split:** development to 2023-11-10, validation to 2024-11-10, OOS to 2026-11-10. These years have been viewed before.
- **Parity:** the research EA with the fix off matches production on 1,647 / 1,647 trades.
- **R:** net / 1% of the balance before each trade. Equity DD is MT5 "relative".

| DI | Version | Trades | /month | /weekday | Win % | PF | Total R | Closed DD (R) | Equity DD % | Dev R | Val R | OOS R | Last year R | MC resample red % | MC randomize red % | Days skipped (trade still open) | Choice rule |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| OFF | PROD | 1,647 | 18.8 | 0.86 | 45.3 | 1.10 | +87.8 | 26.9 | 25.4 | +31.3 | +0.0 | +56.5 | +27.7 | 4.9 | 35.7 | 248 | baseline |
| OFF | LATE | 1,689 | 19.2 | 0.88 | 45.4 | 1.10 | +90.1 | 31.5 | 28.9 | +35.3 | −4.5 | +59.2 | +27.6 | 5.6 | 37.3 | — | fails (validation) |
| OFF | REPLACE | 1,882 | 21.4 | 0.99 | 45.6 | 1.12 | +113.8 | 30.0 | 28.0 | +28.5 | +12.9 | +72.4 | +41.1 | 2.0 | 15.5 | — | fails (development) |
| OFF | FLIP_ONLY | 1,782 | 20.3 | 0.93 | 45.3 | 1.12 | +110.7 | 31.9 | 29.6 | +38.9 | +5.6 | +66.2 | +39.1 | 1.8 | 14.2 | — | passes the period checks, fails MC randomize (>10%) |
| ON | PROD | 1,310 | 14.9 | 0.69 | 46.3 | 1.17 | +115.3 | 27.2 | 25.3 | +47.0 | +11.5 | +56.8 | +34.7 | 1.1 | 0.1 | 197 | baseline |
| ON | LATE | 1,338 | 15.2 | 0.70 | 46.1 | 1.15 | +107.4 | 27.5 | 25.4 | +46.0 | +6.1 | +55.4 | +32.2 | 1.5 | 0.6 | — | fails |
| ON | REPLACE | 1,449 | 16.5 | 0.76 | 46.2 | 1.17 | +120.3 | 27.7 | 25.7 | +46.0 | +12.6 | +61.7 | +41.1 | 0.9 | 0.1 | — | fails (development return/DD 1.66 vs 1.73) |
| ON | FLIP_ONLY | 1,389 | 15.8 | 0.73 | 45.9 | 1.17 | +116.8 | 28.1 | 26.0 | +49.6 | +10.0 | +57.2 | +40.5 | 0.7 | 0.0 | — | fails (validation 10.0 vs 11.5) |

## Frozen-rule verdict
No version qualifies, so PROD stays.

## Notes
- **Days skipped:** the "days skipped" column counts PROD days on which an older trade was still open at the 09:35 check. That is 248 days with DI OFF (about 13% of weekdays) and 197 with DI ON.
- **Rejected-order messages:** the tester logs several hundred thousand of them in every run, identical between PROD and the production EX5. They are stop modifications attempted while the market is closed, not caused by this change.

## Addendum (owner, after the first results): the old 0.60% stop, DI OFF (`carry.py pct`, RESULTS_PCT.json)
The 0.60% runs use the installers' OLD stop (InpStopMode=2, 0.60% of the entry price). Everything else is the same, including the ATR6 trail from +1R.

| Stop | Held-trade rule | Trades | /month | /weekday | Win % | PF | Total R | Return % | Closed DD (R) | Equity DD % | Dev R (2019-07 to 2023-11) | Val R (2023-11 to 2024-11) | OOS R (2024-11 to 2026-11) | Last year R | Last 6 months R | Without best 5 days R | MC resample / randomize red % | Days skipped |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|
| ATR6 (current) | skip the day | 1,647 | 18.8 | 0.86 | 45.3 | 1.10 | +87.8 | +108.6 | 26.9 | 25.4 | +31.3 | +0.0 | +56.5 | +27.7 | +18.4 | +51.9 | 4.9 / 35.7 | 248 |
| ATR6 | REPLACE | 1,882 | 21.4 | 0.99 | 45.6 | 1.12 | +113.8 | +167.7 | 30.0 | 28.0 | +28.5 | +12.9 | +72.4 | +41.1 | +19.1 | +78.6 | 2.0 / 15.5 | — |
| ATR6 | FLIP_ONLY | 1,782 | 20.3 | 0.93 | 45.3 | 1.12 | +110.7 | +160.6 | 31.9 | 29.6 | +38.9 | +5.6 | +66.2 | +39.1 | +20.2 | +74.8 | 1.8 / 14.2 | — |
| 0.60% (old) | skip the day | 1,714 | 19.5 | 0.90 | 42.5 | 1.10 | +94.5 | +112.7 | 58.0 | 47.5 | −7.4 | −3.5 | +105.4 | +30.0 | +9.1 | +38.9 | 7.6 / 33.6 | 178 |
| 0.60% | REPLACE | 1,882 | 21.4 | 0.99 | 42.8 | 1.10 | +94.5 | +112.2 | 45.6 | 40.6 | +3.0 | −5.4 | +97.0 | +40.8 | +13.5 | +38.8 | 5.8 / 48.5 | — |
| 0.60% | FLIP_ONLY | 1,794 | 20.4 | 0.94 | 42.5 | 1.10 | +97.9 | +119.4 | 44.6 | 40.0 | +2.6 | −3.9 | +99.2 | +39.8 | +13.5 | +42.3 | 5.2 / 35.2 | — |

- **Return %:** compounding at 1% of the current balance, so it differs from Total R.
- **Monte Carlo:** every DI OFF version fails the randomize gate (10%). The 0.60% versions also fail the resample gate (5%).
- **Verdict:** the 0.60% stop is profitable only in 2024-26 and roughly doubles the drawdown, so it is not a better base for the fix. With DI OFF the best version is ATR6 + FLIP_ONLY (positive in every period) or ATR6 + REPLACE (highest total). With DI ON the results are stronger (see the table above).
