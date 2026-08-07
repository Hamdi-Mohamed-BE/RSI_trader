# XAU M1 Buy-Stop Grid

This MT5 Python script reads the latest closed 1-minute XAU candle, then builds a news stop-order ladder around it:

- Buy stops above the candle high.
- Sell stops below the candle low.
- `KEEP_EVERYTHING_OPEN=true` keeps both stop ladders and all triggered trades open.
- In that mode the bot adds no SL/TP, uses GTC pending orders, does not trail stops,
  and does not cancel the opposite side. Positions must be closed manually.
- With that mode disabled, optional OCO cancellation and runner trailing are available.

Run:

```bat
run.bat
```

All settings are in `.env`.

Important settings:

```text
PLACE_ORDERS=false
KEEP_EVERYTHING_OPEN=true
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

Warning: `KEEP_EVERYTHING_OPEN=true` creates unprotected positions with unlimited
holding time. The configured SL, TP, expiration, runner, and OCO settings are all
ignored until this switch is turned off.

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

Pending-order expiration is calculated from the broker's MT5 server time, not
the Windows clock. This prevents `Invalid expiration` rejections when the
broker server uses a different timezone. The run also ends with an order
summary and returns a failure exit code when every live send is blocked.

## FX news-pulse backtest

Run `run_news_backtest.bat` to replay the same pre-news M1 OCO idea on:

- EURUSD for major EUR and USD releases.
- EURAUD for major AUD releases.
- EURJPY for major JPY releases.
- USDCAD for major CAD releases.

The backtest is read-only. It auto-discovers broker suffixes, uses recorded M1
spread, models gap fills and slippage, and sizes each isolated event to the
maximum broker-normalized lot allowed by the configured simulated 1:200
leverage. Results are written to:

- `news_pulse_backtest_report.json`
- `news_pulse_event_results.csv`

The default starting balance is `$100`, matching this project's original news
profile. Change `NEWS_BACKTEST_START_BALANCE` in `.env` for another balance.
`NEWS_MT5_HISTORY_OFFSET_HOURS` aligns real UTC release times with the broker's
stored MT5 bar timestamps.

## Fifteen-year direction validation

`fifteen_year_news_backtest.py` builds an official-release calendar for NFP,
advance GDP, CPI, PPI, and scheduled FOMC statements. It trains on the first
13 years and evaluates once on the untouched final two years. Features stop 30
minutes before each release. Dukascopy XAUUSD M1 bid/ask data is cached under
`data/news-event-days`.

The model is a price-action probability filter, not a substitute for archived
analyst consensus and actual-release surprise data. `NEWS_DIRECTION_WATCHLIST`
controls monitored event families. Keep only independently validated families
in `NEWS_DIRECTION_TRADE_EVENTS`.

Run `news_ml_model_comparison.py` to compare regularized logistic regression,
random forest, Extra Trees, and two gradient-boosting models without selecting
on the final two-month holdout. It writes:

- `news_ml_comparison_report.json`
- `news_ml_last_2_months.csv`
- `news_direction_model.joblib`

The saved model remains the regularized logistic classifier because it had the
lowest expanding-window cross-validation log loss. Sentiment from a released
statement must not be used by the pre-release model; it belongs in a separate
post-release strategy. Historical pre-release sentiment requires timestamped
headline archives, while macro surprise features require vintage actual values
and archived market consensus.
