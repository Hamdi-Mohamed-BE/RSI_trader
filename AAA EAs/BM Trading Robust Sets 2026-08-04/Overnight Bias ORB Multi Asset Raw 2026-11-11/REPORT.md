# Overnight Bias ORB on gold, BTC, EURUSD, GBPJPY — RAW REPORT (2026-11-11)

Unchanged US100 raw EA (InpStrategy 4), same New York clock and rules (PLAN.md). Native Model 4, 150 ms, $10k, 1%, M15, 2019-01-01 -> 2026-11-11 excl.
12 strategy runs + buy & hold, 0 failed strategy runs. R = net / 1% of the balance before the trade. Journal "rejected" = flat-time close retries while closed.

| Symbol | Verdict | Trades | /month | /day | All R | Return | PF | Win % | Closed DD | Dev 2019-23 R (PF) | Val R | OOS 2y R (PF) | Last year R | No-bias ctrl R | Random ctrl R | MC resample / randomize red |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BTCUSD | PASS (weak dev) | 881 | 9.3 | 0.45 | +59.8 | +72.5% | 1.18 | 43.7 | 18.4% | +8.3 (1.04) | +30.0 | +21.5 (1.25) | +18.6 | +58.4 | +4.1 | 2.8% / 8.3% |
| XAUUSD | FAIL | 852 | 9.0 | 0.43 | +2.1 | -2.7% | 1.01 | 42.8 | 27.8% | -11.3 (0.95) | +2.5 | +10.9 (1.12) | -11.3 | +20.0 | -23.4 | 47.5% / 100% |
| EURUSD | FAIL | 947 | 10.0 | 0.48 | -11.0 | -14.5% | 0.97 | 45.6 | 32.9% | +17.5 (1.08) | -9.4 | -19.2 (0.81) | -26.6 | -28.8 | -92.0 | 63.8% / 100% |
| GBPJPY | FAIL | 970 | 10.3 | 0.49 | -22.4 | -23.7% | 0.94 | 46.0 | 44.9% | -9.9 (0.96) | -4.4 | -8.1 (0.91) | +5.0 | -28.6 | -44.0 | 79.0% / 100% |

Years (R): BTC 2019 -0.3, 2020 -3.2, 2021 +2.8, 2022 -3.9, 2023 +25.1, 2024 +13.8, 2025 +12.6, 2026 +13.0 | XAU +1.6, -16.8, +2.7, +6.7, -6.1, +7.7, +16.0, -9.5 |
EURUSD +18.8, -14.7, +6.4, +9.4, -3.0, -14.6, +7.2, -20.6 | GBPJPY +9.1, +6.1, -8.9, -17.3, +2.6, -2.2, -19.8, +8.0.

Buy & hold (CFD, swap included): XAUUSD all +108.4% (DD 48.8%), last year -5.2%; BTCUSD all -101% (the CFD's financing wipes the position out; 3y +47.2%, DD 64%);
EURUSD all -17.0% (DD 27.3%); GBPJPY benchmark FAILED (did not open exactly one position) — not available.

Reading: only BTC passes the house raw gate (all-years and 3y positive, PF 1.18, beats both controls, MC within limits), but its profit is 2023-2026; 2019-2022 was
flat (-4.6R) and the development window PF is only 1.04. Gold makes money only on the OOS years and loses the last year; the bias adds nothing on gold (no-bias
control better). EURUSD and GBPJPY lose. Transfer of a US-equity opening-bell clock to 24h markets, declared as such. No optimisation. Nothing installed or pushed.
