# LTA A+ Setup Research Platform

Local FastAPI app for testing LTA Concepts-style A+ setups on:

- XAUUSD
- XAGUSD
- BTCUSD
- US30

The app is built for research, backtesting, and controlled local automation. Live trading is disabled by default in `.env.example`; live order placement only runs when both live switches are enabled.

Choose `ALL SYMBOLS` in the symbol selector to backtest all configured symbols together. The combined dashboard shows one shared equity curve plus a per-symbol watchlist using each symbol's configured lot size.

## Files

- `LTA_BASE_TRADING_PROMPT.md` - distilled prompt for another AI trading agent.
- `app/main.py` - FastAPI app and browser routes.
- `app/mt5_client.py` - MetaTrader 5 data adapter with safe defaults.
- `app/strategy_engine.py` - LTA-style level detection, entry confirmation, and A+ scoring.
- `app/risk_manager.py` - lot/risk/daily-loss/drawdown gates.
- `app/backtester.py` - historical simulation and report export.
- `reports/` - generated JSON and CSV reports.

## Install

From this folder:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Run

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000
```

## MT5 Notes

The app tries to fetch candles from MetaTrader 5 first. If MT5 or the Python package is unavailable, the UI can fall back to deterministic demo candles so the platform still opens and the workflow can be tested.

For real backtests:

1. Install MetaTrader 5.
2. Log in to your broker account in the MT5 terminal.
3. Make sure the symbols you want to trade are visible in Market Watch.
4. Install the Python requirements.
5. Run the app and disable demo fallback if you want MT5-only testing.

Set `MT5_TERMINAL_PATH` in `.env` if the Python MT5 package cannot auto-find your terminal. The default is `C:\Program Files\MetaTrader 5\terminal64.exe`.

Note: `US30` is kept exactly as configured. If your broker does not provide that exact symbol, the scanner will mark it unavailable unless MT5 can resolve a close broker variant.

## Safety

The strategy gate only allows score 90+ A+ setups into simulation. The risk manager can still reject a setup if lot size, drawdown, daily loss, or risk-to-reward rules fail.

Default risk settings live in `.env.example`. Copy it to `.env` if you want local defaults.

Set any of these caps to `0` to disable that specific limit: `MAX_RISK_PER_TRADE_PERCENT`, `MAX_DAILY_LOSS_PERCENT`, `MAX_TOTAL_DRAWDOWN_PERCENT`, or `MAX_TRADES_PER_DAY`.

## Telegram Trade Signaler

Use `run_telegram_signaler.bat` to run the read-only MT5 watcher, or use `run_all_bots.bat` to start it with the five active strategies. It appears in the web dashboard as **Telegram Trade Signaler** and can be started or stopped there too.

Set these values in `.env`:

```env
TELEGRAM_SIGNALER_ENABLED=true
TELEGRAM_BOT_TOKEN=your_botfather_token
TELEGRAM_CHAT_ID=your_chat_or_channel_id
```

The watcher recognizes LTA, ORB, 20 Pip, BPR, and Sniper by their MT5 magic numbers. A pending order receives the original signal message; its fill, TP/SL changes, TP1-to-break-even protection, trailing-stop updates, cancellation, and final close reply to that original message. Direct market entries receive an original live-entry message. Initial signals include an MT5 candlestick chart with entry, SL, TP, and current-price levels when `TELEGRAM_SIGNALER_SEND_CHART=true`.

Telegram state and message mappings are stored in `reports/telegram_signaler/state.json`, so reply threads survive restarts. The signaler never places, closes, or modifies an MT5 order. Use `stop_telegram_signaler.bat` to stop it.

## Automation Worker

Use `run_automation.bat` to scan MT5 continuously for A+ setups.

Defaults:

- Live automation lot sizing: `MAX_LOT_RISK_PCT=5.0`
- Max spread: `MAX_SPREAD_RISK_PERCENT=10`, meaning spread must be 10% or less of the stop distance. `MAX_SPREAD_POINTS=0` disables the fixed-points cap.
- Watchlist symbols: `AUTO_SYMBOLS=XAUUSD`
- Scan timeframes: `M15,M30,H1`
- Scan interval: `60` seconds
- Console detail limit: `AUTO_LOG_DETAIL_LIMIT=8`
- Minimum setup score: `90`
- Pending pre-place setup score: `AUTO_PREPLACE_MIN_SCORE=85`
- Pending order expiry: `AUTO_PREPLACE_EXPIRY_MINUTES=180`
- Gold target profile: `AUTO_SYMBOL_RR=XAUUSD:6`
- Total daily bot trade cap: `MAX_TRADES_PER_DAY=3`, counted across all symbols and both market/pending placements.
- Whole-bot loss streak stop: `AUTO_MAX_CONSECUTIVE_LOSSES=2`
- Symbol daily lock: `AUTO_SYMBOL_MAX_LOSSES_PER_DAY=1` or `AUTO_SYMBOL_MAX_DAILY_LOSS_R=1.0`
- Strict window: `AUTO_STRICT_SESSION_START=10:00`, `AUTO_STRICT_SESSION_END=13:00`, interpreted in `MARKET_SESSION_TIMEZONE=America/New_York`, requiring stronger internal-structure confirmation.
- Forex HTF agreement: `AUTO_FOREX_REQUIRE_HTF_AGREEMENT=true`
- Symbol activity cooldown: `AUTO_SYMBOL_ACTIVITY_COOLDOWN_MINUTES=60`
- Backtest scan step: `3` candles for faster UI runs; set it to `1` for a slower full scan.

The worker writes:

- latest scan: `reports/automation/latest_scan.json`
- prepared trade tickets: `reports/automation/prepared_orders.jsonl`
- live placement records, only if enabled: `reports/automation/placed_orders.jsonl`
- readable decision events: `reports/automation/automation_events.jsonl`

Safety gates:

- By default, it prepares tickets only.
- Edit `AUTO_SYMBOLS` to control the main LTA automation watchlist. With `CHALLENGE20_SYMBOLS=AUTO_SYMBOLS`, the 20 Pip Challenge follows the same list. `ORB_SYMBOLS` remains separate.
- It sends live market orders only when both `LIVE_TRADING=true` and `AUTO_PLACE_TRADES=true` are set in `.env`.
- It sends live pending orders only when `LIVE_TRADING=true`, `AUTO_PLACE_TRADES=true`, and `AUTO_PREPLACE_ORDERS=true` are all set in `.env`.
- Pending orders are separate from confirmed A+ market entries. The preferred pending entries are Entry Model 2 LTF Swing POC/VAH/VAL retests and fresh supply/demand base retests that produced a volume-backed structure break. Entry Model 3 break-stop orders remain available when no valid pullback level exists.
- `AUTO_PREFER_RETEST_LIMITS=true` also prepares a pullback alternative beside a confirmed market setup. If the live quote has already moved more than `AUTO_MARKET_MAX_CHASE_ATR=0.35` beyond the confirmed close, the market order is blocked and the book-aligned pending limit can remain eligible.
- Signal generation uses completed candles only. The current unfinished M15/M30/H1 candle cannot confirm an entry.
- Every market signal must still be an A+ setup and include entry, stop loss, take profit, and risk-to-reward.
- MT5 order comments include the setup grade, score, and timeframe, for example `LTA A+ S95 M15`.
- The bot checks the live bid/ask spread before preparing an order and again just before sending to MT5. If the red/blue price spread is too large versus the stop distance, the trade is blocked and logged as `blocked_spread`.
- Live automation calculates lot size from the current MT5 account balance, `MAX_LOT_RISK_PCT`, the live entry price, and the signal stop loss. With `USE_BROKER_MIN_LOT_WHEN_RISK_TOO_SMALL=true`, a calculated size below the broker minimum is rounded up to the minimum lot and the resulting risk overrun is logged.
- Duplicate protection persists across restarts in `reports/automation/trade_state.json`.
- `MAX_TRADES_PER_DAY` is a total bot cap for the day, not a per-symbol cap.
- `AUTO_MAX_CONSECUTIVE_LOSSES=2` stops all new orders after two losing bot trades in a row.
- A losing bot trade locks that symbol until the later of the current session end or the normal activity cooldown. With `AUTO_SYMBOL_MAX_LOSSES_PER_DAY=1`, that symbol is also blocked for the rest of the day after one failed A+ setup.
- `AUTO_SYMBOL_MAX_DAILY_LOSS_R=1.0` blocks a symbol for the day if its closed bot trades reach -1R or worse.
- During `AUTO_STRICT_SESSION_START` to `AUTO_STRICT_SESSION_END` in `MARKET_SESSION_TIMEZONE`, market entries need `AUTO_STRICT_SESSION_MIN_SCORE` and internal-structure confirmation. Book-aligned EM2/base retest limits are allowed when they meet `AUTO_STRICT_SESSION_PREPLACE_MIN_SCORE`; low-volume M15 retests still require a higher-timeframe confirmation.
- When forex pairs are in the loop, `AUTO_FOREX_REQUIRE_HTF_AGREEMENT=true` requires H1/H4/D1 agreement before a forex signal can pass.
- `AUTO_ONE_POSITION_PER_SYMBOL_DIRECTION=true` blocks a second position only when symbol and direction both match. A gold sell does not block a separately confirmed gold buy.
- When a new same-direction setup appears and the existing LTA position is profitable, the bot updates that existing position to the new TP instead of opening a duplicate. Its volume and SL remain unchanged; flat or losing same-direction positions still block the new entry.
- `AUTO_ONE_PENDING_PER_SYMBOL_DIRECTION=true` applies the same direction-aware rule to LTA pending orders.
- `AUTO_PROTECT_OPEN_TRADES=true` checks open automation trades every scan. The default `AUTO_TP1_PARTIAL_CLOSE=false` keeps the full position open: TP1 moves SL to break-even, TP2 moves SL to TP1, TP3 moves SL to TP2, TP4 moves SL to TP3, and TP5 moves SL to TP4.
- If the broker minimum lot does not allow a safe half-close, the bot records a skipped partial close and still trails the stop loss.
- `AUTO_SYMBOL_ACTIVITY_COOLDOWN_MINUTES=60` cools a symbol until one hour after any MT5 position on that symbol was opened or closed. This includes manual trades and break-even closes. The old `AUTO_SYMBOL_RESULT_COOLDOWN_MINUTES` name still works as a fallback.
- `reports/automation/automation.lock` and `automation_heartbeat.json` prevent accidentally running two automation workers.
- Use `stop_automation.bat` when you want to stop the worker and clear the runtime lock.

## 20 Pip Challenge Bot

Use `run_20pip_challenge.bat` to run the separate 20 Pip Challenge worker in its own visible terminal window.

This worker has its own magic number, tracker, and `.env` switches. It starts with a virtual challenge bank of `$20`, risks `23%` of that challenge bank, targets `30%`, and advances through `30` compounding levels. That is about `1.30R`, matching the common 20 Pip Challenge model.

Defaults:

- Strategy: `CHALLENGE20_STRATEGY=ORB`, using ORB entries with the 20 Pip Challenge risk/target math.
- Symbols: `CHALLENGE20_SYMBOLS=AUDUSD,USDCAD,EURUSD,GBPUSD`, in tested selection priority.
- Timeframes: `CHALLENGE20_TIMEFRAMES=M15,M30`
- ORB challenge timeframe: `CHALLENGE20_ORB_TIMEFRAME=M15`
- Minimum setup score: `CHALLENGE20_MIN_SETUP_SCORE=95`
- Daily cap: two trades, with `CHALLENGE20_SECOND_TRADE_MIN_SCORE=100` for the second entry.
- Fixed challenge exit: `CHALLENGE20_TAKE_PROFIT_PIPS=20` and `CHALLENGE20_STOP_LOSS_PIPS=18`.
- Live order sending: off, unless both `CHALLENGE20_LIVE_TRADING=true` and `CHALLENGE20_PLACE_TRADES=true`
- Account cap: `CHALLENGE20_MAX_ACCOUNT_RISK_PERCENT=23`
- Spread cap: `CHALLENGE20_MAX_SPREAD_RISK_PERCENT=15`

The worker writes:

- state: `reports/20pip_challenge/challenge_state.json`
- latest scan: `reports/20pip_challenge/latest.json`
- event log: `reports/20pip_challenge/challenge_events.jsonl`

Safety notes:

- The challenge bank is tracked separately from the MT5 account. The bot sizes from the challenge bank and checks that the account can support the risk before sending anything.
- Public versions of the challenge are very aggressive. A few losses can wipe out the challenge bank, so the live switches are intentionally separate from the main automation switches.
- `CHALLENGE20_STRATEGY=LTA` uses LTA A+ confirmation on MT5 candles. `CHALLENGE20_STRATEGY=ORB` uses the ORB session/range settings and then adjusts TP to the challenge RR.
- Set `CHALLENGE20_SYMBOLS` to a comma-separated list if you want the challenge to watch different symbols from the main LTA bot.
- The challenge bot uses a fixed 20-pip TP and 18-pip SL. It does not trail SL or close half unless `CHALLENGE20_PROTECT_OPEN_TRADES=true` is explicitly enabled.
- The current implementation does not use a true 10-second candle feed yet.
- `CHALLENGE20_ALLOW_PENDING=false` is recommended for ORB challenge mode until an OCO pair of pending breakout orders is added.
- Use `stop_20pip_challenge.bat` when you want to stop this worker and clear the challenge lock.

## ORB Bot

Use `run_orb_bot.bat` to run the separate Opening Range Breakout worker in its own visible terminal window.

Defaults:

- Symbols: `ORB_SYMBOLS=XAGUSD,XAUUSD,US100,EURUSD,GBPUSD`. These were positive over the January-June 2026 spread-filtered retest; symbols with fewer than eight accepted trades were excluded.
- Timeframe: `ORB_TIMEFRAME=M5`
- Range anchor: `ORB_SESSION_START=08:00` with `ORB_RANGE_START_UTC_OFFSET=-05:00`. This is fixed 08:00 EST, which appears as 08:00 New York in standard time and 09:00 New York during daylight-saving time.
- Trading cutoff: `ORB_SESSION_END=16:00`, interpreted in `ORB_SESSION_TIMEZONE=America/New_York`
- Entry: `ORB_ENTRY_MODEL=BREAKOUT_RETEST` requires a completed M5 close beyond the 15-minute range, then places a limit order at the last opposing candle's demand/supply boundary.
- Opening range: `ORB_RANGE_MINUTES=15`
- Per-symbol targets: `XAGUSD=2.5R`, `XAUUSD=1.5R`, `US100=1R`, `EURUSD=1.5R`, `GBPUSD=1R`
- Stop: the far edge of the demand/supply candle. `ORB_DYNAMIC_STOP_ENABLED=false` keeps live execution aligned with the tested structural stop.
- Trade protection: `ORB_PROTECT_OPEN_TRADES=true`, `ORB_TP1_PARTIAL_CLOSE=false`, `ORB_TP1_PARTIAL_CLOSE_PCT=0`
- Live order sending is controlled by `ORB_LIVE_TRADING`, `ORB_PLACE_TRADES`, and `ORB_PLACE_PENDING`.
- Candle data timezone: `MARKET_DATA_TIMEZONE=UTC`
- Console detail limit: `ORB_LOG_DETAIL_LIMIT=8`

The worker writes:

- state: `reports/orb_bot/orb_state.json`
- latest scan: `reports/orb_bot/latest.json`
- event log: `reports/orb_bot/orb_events.jsonl`
- protection log: `reports/orb_bot/orb_trade_protection.jsonl`

Safety notes:

- ORB has its own magic number and does not share the LTA automation state.
- ORB protection checks ORB-owned open positions every scan. TP1 moves SL to break-even without a partial close; later whole-R milestones trail SL to the previous milestone when the configured RR reaches them.
- Retest limit orders expire at the New York session cutoff. No order is staged before an M5 candle has closed outside the opening range.
- Use `stop_orb_bot.bat` when you want to stop this worker and clear the ORB lock.
