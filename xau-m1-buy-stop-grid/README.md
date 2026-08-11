# XAU M1 Buy-Stop Grid

This MT5 Python script captures the current executable XAU bid/ask, then builds a news stop-order ladder around that live snapshot:

- Buy stops above the current live ask.
- Sell stops below the current live bid.
- Each stop loss is calculated from its own pending-order entry price.
- Opposite buy/sell pending orders remain active after one side triggers.
- Runner mode can trail the stop after the trade reaches a configured R multiple.

## Five-year event-offset study

Run `run_offset_study.bat` to measure the wrong-way fakeout and correct-direction move for CPI, PPI, NFP, advance GDP, and FOMC releases. The default study uses five years of historical XAUUSD M1 bid/ask data and a 30-minute post-release horizon. It writes event cases, event summaries, the full offset sweep, JSON, and a readable report under `reports/news-offset-study`.

Run:

```bat
pre_install.bat
run.bat
```

Run `pre_install.bat` once on a new Windows machine. It installs Python 3.13
and Node.js LTS through Windows Package Manager when they are missing, creates
the local `.venv`, installs the MT5 Python connector and the locked Dukascopy
Node dependency, and verifies both installations. It never starts the bot or
places orders. A logged-in MetaTrader 5 terminal remains required for broker
data and live execution.

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
SL_MODE=fixed
SL_DISTANCE_USD=6
TP_DISTANCE_USD=0
MANAGE_RUNNER=true
RUNNER_TRAIL_START_R=7
RUNNER_TRAIL_DISTANCE_R=1
RUNNER_MONITOR_MINUTES=120
SKIP_DUPLICATE_PENDING=false
```

With `SL_MODE=fixed`, every level uses its own order entry as the stop-loss
anchor. A buy stop at `4112.00` with `SL_DISTANCE_USD=6` receives an SL at
`4106.00`. A sell stop at `4078.00` receives an SL at `4084.00`. The setup
candle high and low are not used in this mode.

With the current 1:200 news-margin profile, if the live ask is `4100.00`, it prepares:

```text
BUY_STOP 4112.00
BUY_STOP 4114.00
BUY_STOP 4116.00
BUY_STOP 4118.00
```

If the live bid is `4090.00`, it also prepares:

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
