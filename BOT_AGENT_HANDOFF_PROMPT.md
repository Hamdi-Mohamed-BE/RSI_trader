# Agent Prompt: XAUUSD News Pulse + Weekend Direction Bots

You are a senior Python and MetaTrader 5 engineer working inside:

`C:\Users\hama101\Desktop\geek\ai trader`

Build two independent XAUUSD-only MT5 workers: a high-impact USD news-pulse bot and a Friday weekend-direction hold bot. Preserve existing work and reuse established modules where appropriate. Every path below is relative to the repository root. Never fabricate market data, calendar values, broker symbols, model validation, spreads, or fills.

## Shared requirements

- Python 3.12+, typed code, UTC internally, timezone-aware scheduling, and MT5 execution.
- Dynamically discover the broker's gold symbol from `XAUUSD`; support prefixes/suffixes such as `XAUUSD..`, `XAUUSDm`, and `GOLD` only when the broker description confirms gold versus USD.
- Normalize price, volume, stops level, freeze level, filling mode, and expiration from `symbol_info`.
- Run `order_check` before `order_send`. Log the complete request, check result, send result, retcode, comment, and `mt5.last_error()`.
- Include separate `.env.example`, persistent SQLite/JSON state, magic number, structured logs, tests, README, and visible `run.bat` for each bot.
- Defaults: `LIVE_TRADING=false` and `PLACE_ORDERS=false`; require both before sending orders.
- Persist event/week IDs, signal hashes, order tickets, position tickets, and lifecycle state. Restarts must not duplicate trades.
- Support `fixed_lot` and `risk_percent` sizing through `order_calc_profit`. Never silently exceed the configured cap because of broker minimum lot.
- Enforce maximum spread, slippage, open risk, daily loss, daily trades, one idea per event/week, and a kill switch.
- Manage only orders and positions matching the worker's magic number.
- Backtests must use bid/ask when available and include spread, commission, slippage, gap fills, broker stops, and pessimistic same-M1-bar sequencing.

## Bot 1: XAUUSD high-impact USD news pulse

Target events: `NFP`, `CPI`, `PPI`, `Advance GDP`, and `FOMC Statement`. Event times must come from a point-in-time calendar and be converted to UTC. Never use post-release actual values in a T-30 or T-15 forecast.

Reference files:

- `AI news/news_pending_strategy.py`
- `AI news/backtest_news_pending.py`
- `AI news/NEWS_PENDING_2Y_RESULTS.md`
- `AI news/news_15y_calendar.csv`
- `AI news/predict_news.py`
- `AI news/news_ensemble.py`
- `AI news/release_intelligence.py`
- `AI news/monitor_release.py`
- `AI news/NEWS_IMPACT_PREDICTION_PROMPT.md`
- `AI news/data/news-event-days/`

Gold prediction artifacts, for inference only:

- `AI news/models/gold_news_max_ensemble.joblib`
- `AI news/models/gold_news_impulse_30m.joblib`
- `AI news/models/gold_news_impulse_15m.joblib`
- `AI news/models/gold_news_direction.joblib`
- `AI news/models/gold_news_v3_candidate.joblib`

These artifacts explicitly have `execution_capability=false`. Do not edit that metadata or let the model send orders. Build a separate deterministic execution layer that consumes a saved prediction only after validation and user-enabled execution gates. The ensemble policy says T-15 is the final directional decision; T-30 is an earlier forecast.

News lifecycle:

1. At T-60 through T-31, build and freeze the completed XAUUSD M1 bid/ask range.
2. At T-30, run and permanently save the T-30 forecast, probability, feature timestamp, model version, and data-quality flags.
3. At T-15, run the final forecast. Trade only supported events and only if confidence reaches the artifact threshold (currently 0.60 for the individual T-30/T-15 models), required data is point-in-time, and spread/execution gates pass.
4. Implement two separately testable modes:
   - `forecast`: place one pending stop in the T-15 predicted direction.
   - `oco`: place a BUY_STOP above the frozen range and SELL_STOP below it; first fill immediately cancels the opposite order.
5. Entry buffer is `max(broker minimum distance, configured minimum, spread * multiplier, ATR * multiplier)`. Widen away from price when spread rises; never move the pending entry closer.
6. XAU research convention: `1 pip = $0.10`; a 90-pip stop is `$9.00`, not `$0.90`. Use `order_calc_profit` for actual account risk.
7. Initial research grid: breakout SL `90` pips, RR `3,4,5,7`; re-entry SL `50` pips and RR `5`. The existing locked result selected XAU `PPI`, `oco`, `5R`, with re-entry, but its holdout has only four trades. Treat it as provisional and rerun chronological walk-forward tests before enabling live trading.
8. Optional re-entry: after a stop hunt, use the validated `0.60` range Fibonacci level for BUY and `0.50` for SELL only once per event. Never average into a losing position.
9. Pending orders expire at T+15. A filled trade has a maximum 180-minute time stop unless a newly validated configuration is stricter.
10. At release, record actual/forecast/previous/revisions separately. Mixed components may cancel unfilled directional orders; post-release data must never rewrite the pre-release prediction.
11. Log event, release time, prediction, confidence, frozen range, spread, buffer, entry, SL, TP, lot, dollar risk, tickets, fill slippage, MFE, MAE, exit, R result, and cancellation reason.

## Bot 2: XAUUSD Friday weekend-direction hold

Purpose: take at most one directional position shortly before the broker's Friday close and close it at the first weekly-reopen tick unless SL or TP closes it first.

Reference files:

- `AI news/predicted_weekend_hold_strategy.py`
- `AI news/backtest_predicted_weekend_hold.py`
- `AI news/PREDICTED_WEEKEND_HOLD_BACKTEST.md`
- `AI news/weekend_direction_v2.py`
- `AI news/weekend_gap_strategy.py`
- `AI news/weekend_gap_bot.py`
- `AI news/data/weekend-direction/market_5y.npz`
- `AI news/gold_weekend_direction_v2_predictions.csv`

Weekend model artifacts:

- `AI news/models/gold_weekend_direction_v2.joblib`
- `AI news/models/gold_weekend_direction.joblib`
- `AI news/models/gold_weekend_direction.metadata.json`

Important: the weekend models are currently rejected and `gold_weekend_direction_v2.joblib` has `validated=false`. The bot must inspect this flag and return `NO_TRADE`; never use rejected ML as live authorization. Add `ALLOW_PROVISIONAL_MOMENTUM_MODE=false` for explicit demo-only forward testing.

Provisional momentum flow:

1. Infer Friday close and next weekly reopen from recent XAUUSD M1 trading gaps; never hardcode PC timezone.
2. Four minutes before inferred close, calculate the completed 24-hour XAUUSD return.
3. Compute the rolling 70th percentile of absolute Friday 24-hour returns using earlier weeks only. Trade only when current absolute momentum reaches that threshold.
4. Follow momentum: positive = BUY, negative = SELL.
5. Enter one market position. Research default: fixed `$30` XAUUSD price stop and `3R` target (`$90`), spread-aware.
6. If still open, close on the first executable weekly-reopen tick. Apply unfavorable gap slippage; do not assume an SL can fill inside the closed-market gap.
7. Skip when spread is above cap, Friday schedule/history is uncertain, another bot-owned position exists, market/margin checks fail, or the state says this weekend was already processed.
8. Log momentum, rolling threshold, side, spread, entry, SL, TP, lot, risk, gap/slippage, exit, and result in R.

The strongest observed momentum candidate had selection bias despite encouraging historical results. Label it provisional and require new forward-demo weekends before promotion.

## Validation and delivery

- Keep training, prediction, execution, and post-event evaluation as separate modules.
- Use expanding chronological walk-forward validation with an embargo and one untouched final holdout. No random split and no tuning on holdout.
- Report per-event/per-year trades, coverage, win rate, profit factor, expectancy in R, net R, maximum drawdown, spread/slippage sensitivity, and confidence calibration.
- Reject deployment when sample size or untouched evidence is inadequate; encode that as `validated=false` and force `NO_TRADE`.
- Deliver exact commands for tests, backtests, paper mode, and live mode. Leave live mode disabled by default.
