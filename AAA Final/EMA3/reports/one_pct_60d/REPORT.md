# EMA3 Risk-Sized Backtest

- Period: **2026-06-03T11:00:54.958504+00:00 to 2026-08-02T11:00:54.958504+00:00**
- Broker symbol: **XAUUSD..**
- Setup: **pivot 5 left / 5 right; trail_start_1.5R_distance_1R_cap_1.7R**
- Filter: **ema200_slope, slope lookback 6 H4 bars**
- Base risk: **1.00% of current balance per trade**
- Loss progression: **disabled**, multiplier **1.6x**, cap **3.2%**
- Maximum target: **1.7R**
- Structural stop: **confirmed pivot extreme**

| Metric | Result |
|---|---:|
| Trades | 6 |
| Wins / losses | 4 / 2 |
| Win rate | 66.67% |
| Profit factor | 2.67 |
| Net result | +3.33R |
| Starting balance | $25,000.00 |
| Ending balance | $25,833.70 |
| Return | 3.33% |
| Max realized drawdown | 1.00% |
| Account ruined | no |

This replaces the legacy fixed-0.10-lot, no-stop calculation. Equity is
never allowed to become negative and later recover, and every trade has
the same percentage risk through its structural stop.
