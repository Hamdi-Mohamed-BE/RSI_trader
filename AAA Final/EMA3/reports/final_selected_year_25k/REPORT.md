# EMA3 Risk-Sized Backtest

- Period: **2025-08-02T08:01:57.626591+00:00 to 2026-08-02T08:01:57.626591+00:00**
- Broker symbol: **XAUUSD..**
- Setup: **pivot 5 left / 5 right; trail_start_1.5R_distance_1R_cap_1.7R**
- Filter: **ema200_slope, slope lookback 6 H4 bars**
- Base risk: **0.50% of current balance per trade**
- Loss progression: **disabled**, multiplier **1.6x**, cap **3.2%**
- Maximum target: **1.7R**
- Structural stop: **confirmed pivot extreme**

| Metric | Result |
|---|---:|
| Trades | 44 |
| Wins / losses | 26 / 18 |
| Win rate | 59.09% |
| Profit factor | 2.20 |
| Net result | +21.67R |
| Starting balance | $25,000.00 |
| Ending balance | $27,831.40 |
| Return | 11.33% |
| Max realized drawdown | 2.62% |
| Account ruined | no |

This replaces the legacy fixed-0.10-lot, no-stop calculation. Equity is
never allowed to become negative and later recover, and every trade has
the same percentage risk through its structural stop.
