# Step 6 — Volatility Compression → Expansion

## Objective

Test whether an objectively measured low-volatility state followed by a completed-candle range breakout produces a repeatable, tradable edge on XAUUSD, XAGUSD, BTCUSD, US30, USTEC and GBPJPY.

## Frozen research design

- Development: 2023-09-01 through 2024-09-01.
- Pre-lock validation: 2024-09-01 through 2025-09-01.
- Untouched locked year: 2025-09-01 through 2026-09-01.
- Three-year context: 2023-09-01 through 2026-09-01.
- Risk: fixed at 1% of current equity per trade; risk is not optimized upward.
- Execution proxy: broker M5 bars, recorded spread with a conservative floor, next-bar market entry and an added 0.02R friction charge.
- Native validation: MT5 Every Tick with broker spread, commission, swap and random execution delay.

## Pipeline

1. Timeframes: M5, M15, M30, H1 and H4.
2. Sessions: all day, Asia, London, New York, London/New York overlap and London-or-New-York.
3. Compression: fast/slow ATR ratio, Bollinger BandWidth percentile, narrow-range rank and Bollinger-inside-Keltner approximation.
4. Range/trigger: 6/12/20-bar frozen range, 3/6/12-bar arming lifetime and 0/0.1/0.2 ATR close buffer.
5. Confirmation: close-only, directional body, relative tick volume or body-plus-volume.
6. Direction/trend: both/long/short with none, EMA50, EMA200 or EMA50/200 alignment.
7. Stops: frozen compression range, ATR, signal candle and five-bar swing variants.
8. Targets: 0.5R, 0.75R, 1R, 1.5R, 2R, 2.5R, 3R, 4R and 6R.
9. Management: none, break-even, ATR trail and M15-close Dynamic 50/20.
10. Time exits: 6, 12, 24 and 48 signal bars.
11. Robustness: untouched locked year, native MT5 reconciliation, overlapping rolling six-month windows and 10,000-path block bootstrap.

No candidate is added to production until the locked results are reviewed by the user.
