# LTA A+ Setup Research Platform

Local FastAPI app for testing LTA Concepts-style A+ setups on:

- XAUUSD
- XAGUSD
- BTCUSD
- EURUSD
- USDJPY
- GBPUSD
- USDCAD
- USDAUD
- AUDUSD
- NZDUSD
- EURGBP
- EURJPY
- GBPJPY
- US30
- US300

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

Note: `USDAUD`, `US30`, and `US300` are kept exactly as configured. If your broker does not provide those exact symbols, the scanner will mark them unavailable unless MT5 can resolve a close broker variant.

## Safety

The strategy gate only allows score 90+ A+ setups into simulation. The risk manager can still reject a setup if lot size, drawdown, daily loss, or risk-to-reward rules fail.

Default risk settings live in `.env.example`. Copy it to `.env` if you want local defaults.

Set any of these caps to `0` to disable that specific limit: `MAX_RISK_PER_TRADE_PERCENT`, `MAX_DAILY_LOSS_PERCENT`, `MAX_TOTAL_DRAWDOWN_PERCENT`, or `MAX_TRADES_PER_DAY`.

## Automation Worker

Use `run_automation.bat` to scan MT5 continuously for A+ setups.

Defaults:

- Live automation lot sizing: `MAX_LOT_RISK_PCT=3.0`
- Max spread: `MAX_SPREAD_RISK_PERCENT=15`, meaning spread must be 15% or less of the stop distance. `MAX_SPREAD_POINTS=0` disables the fixed-points cap.
- Scan timeframes: `M5,M15,M30,H1,H4,D1,W1`
- Scan interval: `60` seconds
- Console detail limit: `AUTO_LOG_DETAIL_LIMIT=8`
- Minimum setup score: `90`
- Minimum R:R: `5.0`
- Symbol activity cooldown: `AUTO_SYMBOL_ACTIVITY_COOLDOWN_MINUTES=60`
- Backtest scan step: `3` candles for faster UI runs; set it to `1` for a slower full scan.

The worker writes:

- latest scan: `reports/automation/latest_scan.json`
- prepared trade tickets: `reports/automation/prepared_orders.jsonl`
- live placement records, only if enabled: `reports/automation/placed_orders.jsonl`
- readable decision events: `reports/automation/automation_events.jsonl`

Safety gates:

- By default, it prepares tickets only.
- It sends live market orders only when both `LIVE_TRADING=true` and `AUTO_PLACE_TRADES=true` are set in `.env`.
- Every signal must still be an A+ setup and include entry, stop loss, take profit, and risk-to-reward.
- MT5 order comments include the setup grade, score, and timeframe, for example `LTA A+ S95 M15`.
- The bot checks the live bid/ask spread before preparing an order and again just before sending to MT5. If the red/blue price spread is too large versus the stop distance, the trade is blocked and logged as `blocked_spread`.
- Live automation does not use fixed per-symbol lots. It calculates lot size from the current MT5 account balance, `MAX_LOT_RISK_PCT`, the live entry price, and the signal stop loss. If the broker minimum lot would risk more than the budget, the trade is blocked instead of rounded up.
- Duplicate protection persists across restarts in `reports/automation/trade_state.json`.
- `AUTO_ONE_POSITION_PER_SYMBOL=true` blocks new entries when that symbol already has an open position.
- `AUTO_PROTECT_OPEN_TRADES=true` checks open automation trades every scan. With the default 1:5 profile, TP1 moves SL to break-even, TP2 moves SL to TP1, TP3 moves SL to TP2, TP4 moves SL to TP3, and TP5 moves SL to TP4 if the position is still open.
- `AUTO_SYMBOL_ACTIVITY_COOLDOWN_MINUTES=60` cools a symbol until one hour after any MT5 position on that symbol was opened or closed. This includes manual trades and break-even closes. The old `AUTO_SYMBOL_RESULT_COOLDOWN_MINUTES` name still works as a fallback.
- `reports/automation/automation.lock` and `automation_heartbeat.json` prevent accidentally running two automation workers.
- Use `stop_automation.bat` when you want to stop the worker and clear the runtime lock.
