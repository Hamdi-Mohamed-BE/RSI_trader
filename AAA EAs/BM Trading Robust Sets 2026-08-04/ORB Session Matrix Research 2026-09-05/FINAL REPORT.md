# Step 6 — ORB Session × RR × Stop × Timeframe Audit

## Test design

Each session is a genuine standalone opening range: Asia 00:00 UTC, London 07:00 UTC, New York 09:30 local (DST-aware), and London/New York overlap 13:00 UTC. Risk is fixed at 1% of current equity.

Development selection used 2023-09-01 through 2025-08-31 with MT5 1-minute OHLC. The untouched locked test used 2025-09-01 through 2026-09-01 with Every Tick, broker spread, commission, swap and random delay. Three-year results are context because they include development data.

## Gold (XAUUSD)

Development-selected session: **overlap** — locked verdict: **WATCH / insufficient robustness**.

| Session | Final configuration | Locked return | PF | Win | DD | Trades | Sharpe | Recovery | MC P5 | MC DD P95 | 3Y return | 3Y PF |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Asia 00:00 UTC | M30 / OR30 / 4.0R / opposite-b10-max2 / be05 / 180m | +0.89% | 1.11 | 32.00% | 3.47% | 25 | 1.89 | 0.25 | -7.35% | 9.78% | +24.82% | 1.95 |
| London 07:00 UTC | M1 / OR30 / 1.5R / opposite-b10-max2.5 / dynamic5020 / 90m | +1.90% | 1.02 | 50.00% | 16.23% | 192 | 0.56 | 0.10 | -21.23% | 27.64% | +62.82% | 1.20 |
| New York 09:30 local | M30 / OR30 / 1.5R / opposite-b10-max2 / be05 / 180m | +2.44% | 3.04 | 45.45% | 2.64% | 11 | 2.82 | 0.90 | +0.04% | 1.56% | +13.41% | 2.36 |
| London/New York overlap 13:00 UTC | M30 / OR5 / 1.0R / opposite-b05-max1.5 / be05 / 180m | +5.21% | 2.16 | 41.67% | 3.96% | 24 | 27.14 | 1.28 | -1.17% | 4.93% | +28.10% | 2.51 |

Existing comparator: Current active XAU Dynamic 50/20 ORB — +13.46% return, PF 1.91, win 48.98%, DD 5.98%, 49 trades.

## US100 (USTEC CFD)

Development-selected session: **new-york** — locked verdict: **WATCH / insufficient robustness**.

| Session | Final configuration | Locked return | PF | Win | DD | Trades | Sharpe | Recovery | MC P5 | MC DD P95 | 3Y return | 3Y PF |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Asia 00:00 UTC | M30 / OR15 / 1.5R / signal-b10-max2 / be05 / 180m | +0.22% | 1.02 | 21.28% | 5.60% | 47 | 0.30 | 0.04 | -7.07% | 9.16% | +14.48% | 1.67 |
| London 07:00 UTC | M5 / OR5 / 1.5R / opposite-b10-max2.5 / be1 / 30m | -0.55% | 0.99 | 35.22% | 19.96% | 159 | -0.23 | -0.02 | -24.00% | 29.98% | +4.93% | 1.03 |
| New York 09:30 local | M30 / OR5 / 4.0R / opposite-b10-max2 / none / 180m | +9.66% | 1.68 | 48.15% | 4.76% | 27 | 10.26 | 1.87 | -0.94% | 6.91% | +36.94% | 2.15 |
| London/New York overlap 13:00 UTC | M5 / OR30 / 3.0R / opposite-b10-max2 / none / 180m | -11.39% | 0.80 | 27.06% | 21.93% | 85 | -5.00 | -0.46 | -34.04% | 36.87% | -6.15% | 0.95 |

Existing comparator: Prior development-selected US100 ORB — -4.49% return, PF 0.90, win 41.25%, DD 10.97%, 80 trades.

## Integrity

- RR values tested separately inside every session: 0.5, 0.75, 1, 1.5, 2, 2.5, 3 and 4.
- Signal timeframes tested separately inside every session: M1, M5, M15 and M30, with 5, 15 and 30-minute opening ranges.
- Stop families tested separately inside every session: signal-candle and opposite-range stops with ATR buffers and 1.5–2.5 ATR caps.
- Management tested separately inside every session: none, 0.5R/1R break-even, 0.5R/1R candle trail, and Dynamic 50/20.
- Trade windows tested separately inside every session: 30, 60, 90, 120 and 180 minutes.
- The best session was selected on development data before the locked period was read.
- Exness USTEC is a CFD and its tick activity is not centralized CME NQ/MNQ volume.
