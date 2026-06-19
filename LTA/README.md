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

## Automation Worker

Use `run_automation.bat` to scan MT5 continuously for A+ setups.

Defaults:

- Live automation lot sizing: `MAX_LOT_RISK_PCT=3.0`
- Max spread: `MAX_SPREAD_RISK_PERCENT=15`, meaning spread must be 15% or less of the stop distance. `MAX_SPREAD_POINTS=0` disables the fixed-points cap.
- Watchlist symbols: `AUTO_SYMBOLS=XAUUSD,XAGUSD,BTCUSD,US30`
- Scan timeframes: `M15,M30,H1,H4,D1,W1`
- Scan interval: `60` seconds
- Console detail limit: `AUTO_LOG_DETAIL_LIMIT=8`
- Minimum setup score: `90`
- Pending pre-place setup score: `AUTO_PREPLACE_MIN_SCORE=85`
- Pending order expiry: `AUTO_PREPLACE_EXPIRY_MINUTES=240`
- Minimum R:R: `5.0`
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
- Pending orders are separate from confirmed A+ market entries. They are only created from `preplace` setups where a trigger price would complete an LTA Entry Model 3 internal break or a clean Entry Model 2 LTF swing retest.
- Every market signal must still be an A+ setup and include entry, stop loss, take profit, and risk-to-reward.
- MT5 order comments include the setup grade, score, and timeframe, for example `LTA A+ S95 M15`.
- The bot checks the live bid/ask spread before preparing an order and again just before sending to MT5. If the red/blue price spread is too large versus the stop distance, the trade is blocked and logged as `blocked_spread`.
- Live automation does not use fixed per-symbol lots. It calculates lot size from the current MT5 account balance, `MAX_LOT_RISK_PCT`, the live entry price, and the signal stop loss. If the broker minimum lot would risk more than the budget, the trade is blocked instead of rounded up.
- Duplicate protection persists across restarts in `reports/automation/trade_state.json`.
- `MAX_TRADES_PER_DAY` is a total bot cap for the day, not a per-symbol cap.
- `AUTO_MAX_CONSECUTIVE_LOSSES=2` stops all new orders after two losing bot trades in a row.
- A losing bot trade locks that symbol until the later of the current session end or the normal activity cooldown. With `AUTO_SYMBOL_MAX_LOSSES_PER_DAY=1`, that symbol is also blocked for the rest of the day after one failed A+ setup.
- `AUTO_SYMBOL_MAX_DAILY_LOSS_R=1.0` blocks a symbol for the day if its closed bot trades reach -1R or worse.
- During `AUTO_STRICT_SESSION_START` to `AUTO_STRICT_SESSION_END` in `MARKET_SESSION_TIMEZONE`, market entries need `AUTO_STRICT_SESSION_MIN_SCORE` and internal-structure confirmation. Pending orders need `AUTO_STRICT_SESSION_PREPLACE_MIN_SCORE` and must be break-stop orders.
- When forex pairs are in the loop, `AUTO_FOREX_REQUIRE_HTF_AGREEMENT=true` requires H1/H4/D1 agreement before a forex signal can pass.
- `AUTO_ONE_POSITION_PER_SYMBOL=true` blocks new entries when that symbol already has an open position.
- `AUTO_ONE_PENDING_PER_SYMBOL=true` blocks a second LTA pending order on a symbol that already has one.
- `AUTO_PROTECT_OPEN_TRADES=true` checks open automation trades every scan. With the default 1:5 profile, TP1 moves SL to break-even, TP2 moves SL to TP1, TP3 moves SL to TP2, TP4 moves SL to TP3, and TP5 moves SL to TP4 if the position is still open.
- `AUTO_SYMBOL_ACTIVITY_COOLDOWN_MINUTES=60` cools a symbol until one hour after any MT5 position on that symbol was opened or closed. This includes manual trades and break-even closes. The old `AUTO_SYMBOL_RESULT_COOLDOWN_MINUTES` name still works as a fallback.
- `reports/automation/automation.lock` and `automation_heartbeat.json` prevent accidentally running two automation workers.
- Use `stop_automation.bat` when you want to stop the worker and clear the runtime lock.

## 20 Pip Challenge Bot

Use `run_20pip_challenge.bat` to run the separate 20 Pip Challenge worker in its own visible terminal window.

This worker has its own magic number, tracker, and `.env` switches. It starts with a virtual challenge bank of `$20`, risks `23%` of that challenge bank, targets `30%`, and advances through `30` compounding levels. That is about `1.30R`, matching the common 20 Pip Challenge model.

Defaults:

- Strategy: `CHALLENGE20_STRATEGY=ORB`, using ORB entries with the 20 Pip Challenge risk/target math.
- Symbols: `CHALLENGE20_SYMBOLS=AUTO_SYMBOLS`, meaning it follows the main LTA bot watchlist from `AUTO_SYMBOLS`
- Timeframes: `CHALLENGE20_TIMEFRAMES=M15,M30`
- ORB challenge timeframe: `CHALLENGE20_ORB_TIMEFRAME=M15`
- Minimum setup score: `CHALLENGE20_MIN_SETUP_SCORE=90`
- One challenge trade per day: `CHALLENGE20_ONE_TRADE_PER_DAY=true`
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
- The current implementation does not use a true 10-second candle feed yet.
- `CHALLENGE20_ALLOW_PENDING=false` is recommended for ORB challenge mode until an OCO pair of pending breakout orders is added.
- Use `stop_20pip_challenge.bat` when you want to stop this worker and clear the challenge lock.

## ORB Bot

Use `run_orb_bot.bat` to run the separate Opening Range Breakout worker in its own visible terminal window.

Defaults:

- Symbols: `ORB_SYMBOLS=BTCUSD,XAGUSD,US30,EURUSD,GBPUSD,USDCHF,XAUUSD,NZDUSD,AUDUSD,USDCAD,USDJPY`, ordered by latest positive ORB net R.
- Timeframe: `ORB_TIMEFRAME=M15`
- Session window: `ORB_SESSION_START=09:30`, `ORB_SESSION_END=16:00`, interpreted in `ORB_SESSION_TIMEZONE=America/New_York`
- Opening range: `ORB_RANGE_MINUTES=15`
- Target: `ORB_RR=5.0`
- Trade protection: `ORB_PROTECT_OPEN_TRADES=true`, `ORB_PROTECTION_FINAL_RR=5.0`
- Live order sending: off, unless `ORB_LIVE_TRADING=true` and `ORB_PLACE_TRADES=true`
- Pending stop sending: off, unless `ORB_PLACE_PENDING=true`
- Candle data timezone: `MARKET_DATA_TIMEZONE=UTC`

The worker writes:

- state: `reports/orb_bot/orb_state.json`
- latest scan: `reports/orb_bot/latest.json`
- event log: `reports/orb_bot/orb_events.jsonl`
- protection log: `reports/orb_bot/orb_trade_protection.jsonl`

Safety notes:

- ORB has its own magic number and does not share the LTA automation state.
- ORB protection checks ORB-owned open positions every scan. With the default 1:5 profile, TP1 moves SL to break-even, TP2 moves SL to TP1, TP3 moves SL to TP2, TP4 moves SL to TP3, and TP5 moves SL to TP4.
- Pending ORB stops are prepared by default but not sent unless the pending live switch is enabled.
- Use `stop_orb_bot.bat` when you want to stop this worker and clear the ORB lock.
