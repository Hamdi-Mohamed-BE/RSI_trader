# Filtered ORB Retest Bot

The optimized default is US30 using the 09:30-09:45 New York cash opening range:

1. Build the 09:30-09:45 New York opening range.
2. Score H1 structure, a recent swing break, and H1 trend; require two of three.
3. Require price to be on the matching side of the New York daily open.
4. Require a five-minute candle to close beyond the range with at least 60% body.
5. Confirm the breakout with session VWAP and relative tick volume.
6. Wait up to six M5 candles for a retest that holds and rejects the boundary.
7. Place a stop order beyond the rejection candle. Do not chase a missed entry.
8. Risk 0.5%, take 50% at 1R, move the runner stop to break even, and target 2R.
9. Allow at most one trade per New York session.

The live worker also cancels an unfilled pending order at the configured flat
time and closes any remaining session position. If the broker's minimum lot
prevents a 55% partial close, the worker keeps the full position and moves its
stop to break even instead of sending an invalid close.

All times use `America/New_York`, so daylight-saving changes are automatic.

## Run a backtest

Double-click `backtest.bat`. The default test covers the latest 60 calendar days
available from the connected MT5 broker. JSON and CSV reports are saved under
`reports`.

`backtest_london_midpoint.bat` runs the separate US100 long-only experiment. It
requires a green 09:30-09:45 New York candle, enters at the following M15 open,
and targets the midpoint of the 03:00-09:30 pre-New-York London range. The report
compares 1:1 and 1:2 reward-to-risk stops over the latest three completed months.

## Run the bot

Double-click `run.bat`. Live sending is disabled by default. The scanner will
report setups without placing orders until both of these values are enabled:

```env
ORB_LIVE_TRADING=true
ORB_PLACE_TRADES=true
```

The bot discovers broker suffixes and aliases automatically. On the tested
account, `US100` resolves to `NAS100U6`, while gold resolves to `XAUUSD..`.
When testing gold, set `ORB_SYMBOL=XAUUSD`, `ORB_RANGE_START=08:20`, and use a
gold-appropriate spread ceiling such as `ORB_MAX_SPREAD_POINTS=80`.

Percentage risk is a hard cap. If the broker's minimum lot would exceed 0.5% risk,
the live worker blocks the order and reports the required minimum risk instead of
silently oversizing it. Set `ORB_FIXED_LOT` only when you intentionally want to
override percentage sizing.

## News filter

MT5's Python API does not expose a complete historical economic calendar. Add
high-impact USD blackout windows to `data/news_blackouts.csv`. Set
`ORB_REQUIRE_NEWS_FILE=true` if the bot must reject every day unless calendar
rows are supplied. Leaving the file empty makes the limitation explicit in the
backtest report; it does not pretend news was filtered.

## Important backtest assumptions

- Broker M5 and H1 bars are used.
- Historical spread and configured slippage are included.
- If a stop and target are both touched in one M5 candle, the stop is assumed to
  occur first.
- Commission and swap are not included.
- Backtests are research estimates, not guarantees of future results.
