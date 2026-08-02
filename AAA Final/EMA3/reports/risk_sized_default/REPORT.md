# EMA3 Risk-Sized Backtest

- Period: **2025-08-01T12:28:55.579747+00:00 to 2026-08-01T12:28:55.579747+00:00**
- Broker symbol: **XAUUSD..**
- Setup: **pivot 5 left / 5 right; trail_start_1R_distance_1R**
- Filter: **ema200_slope, slope lookback 6 H4 bars**
- Risk: **1.00% of current balance per trade**
- Structural stop: **confirmed pivot extreme**

| Metric | Result |
|---|---:|
| Trades | 37 |
| Wins / losses | 23 / 14 |
| Win rate | 62.16% |
| Profit factor | 3.39 |
| Net result | +33.51R |
| Starting balance | $1,000.00 |
| Ending balance | $1,385.87 |
| Return | 38.59% |
| Max realized drawdown | 5.29% |
| Account ruined | no |

This replaces the legacy fixed-0.10-lot, no-stop calculation. Equity is
never allowed to become negative and later recover, and every trade has
the same percentage risk through its structural stop.
