# XAU M1 Buy-Stop Grid

This MT5 Python script reads the latest closed 1-minute XAU candle, then builds a news stop-order ladder around it:

- Buy stops above the candle high.
- Sell stops below the candle low.
- Opposite side is cancelled after one side triggers.
- Runner mode can trail the stop after the trade reaches a configured R multiple.

Run:

```bat
run.bat
```

All settings are in `.env`.

Important settings:

```text
PLACE_ORDERS=false
ORDER_SIDE=both
ORDER_COUNT=4
BUY_ORDER_COUNT=4
SELL_ORDER_COUNT=4
FIXED_LOT=0.01
PRICE_DIFF_USD=2.00
FIRST_OFFSET_USD=12.00
BUY_PRICE_DIFF_USD=2.00
SELL_PRICE_DIFF_USD=2.00
BUY_FIRST_OFFSET_USD=12.00
SELL_FIRST_OFFSET_USD=12.00
SL_MODE=opposite_candle
SL_ROOM_USD=20
TP_DISTANCE_USD=0
MANAGE_RUNNER=true
RUNNER_TRAIL_START_R=7
RUNNER_TRAIL_DISTANCE_R=1
RUNNER_MONITOR_MINUTES=120
SKIP_DUPLICATE_PENDING=false
```

With the current 1:200 news-margin profile, if the last closed M1 high is `4100.00`, it prepares:

```text
BUY_STOP 4112.00
BUY_STOP 4114.00
BUY_STOP 4116.00
BUY_STOP 4118.00
```

If the closed M1 low is `4090.00`, it also prepares:

```text
SELL_STOP 4078.00
SELL_STOP 4076.00
SELL_STOP 4074.00
SELL_STOP 4072.00
```

Set `PLACE_ORDERS=true` only when you want it to send the pending orders to MT5.

For a `$100` account during news capped to `1:200`, do not use `FIXED_LOT=max`. Use small fixed lots such as `0.01`.

Each run prints start time, key MT5 steps, finish time, and total elapsed seconds.
