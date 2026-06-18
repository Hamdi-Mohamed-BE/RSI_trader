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

- XAUUSD lot: `0.05`
- XAGUSD lot: `0.05`
- BTCUSD lot: `0.08`
- EURUSD lot: `1.0`
- USDJPY lot: `1.0`
- GBPUSD lot: `1.0`
- USDCAD lot: `1.0`
- USDAUD lot: `1.0`
- AUDUSD lot: `1.0`
- NZDUSD lot: `1.0`
- EURGBP lot: `1.0`
- EURJPY lot: `1.0`
- GBPJPY lot: `1.0`
- US30 lot: `1.0`
- US300 lot: `1.0`
- Scan timeframes: `M5,M15,M30,H1,H4,D1,W1`
- Scan interval: `60` seconds
- Minimum setup score: `90`
- Minimum R:R: `5.0`
- TP/SL symbol cooldown: `60` minutes
- Backtest scan step: `3` candles for faster UI runs; set it to `1` for a slower full scan.

The worker writes:

- latest scan: `reports/automation/latest_scan.json`
- prepared trade tickets: `reports/automation/prepared_orders.jsonl`
- live placement records, only if enabled: `reports/automation/placed_orders.jsonl`

Safety gates:

- By default, it prepares tickets only.
- It sends live market orders only when both `LIVE_TRADING=true` and `AUTO_PLACE_TRADES=true` are set in `.env`.
- Every signal must still be an A+ setup and include entry, stop loss, take profit, and risk-to-reward.
- Duplicate protection persists across restarts in `reports/automation/trade_state.json`.
- `AUTO_ONE_POSITION_PER_SYMBOL=true` blocks new entries when that symbol already has an open position.
- `AUTO_PROTECT_OPEN_TRADES=true` checks open automation trades every scan. With the default 1:5 profile, TP1 moves SL to break-even, TP2 moves SL to TP1, TP3 moves SL to TP2, TP4 moves SL to TP3, and TP5 moves SL to TP4 if the position is still open.
- `AUTO_SYMBOL_RESULT_COOLDOWN_MINUTES=60` cools a symbol down after an automation trade closes by TP or SL. A break-even SL close does not trigger this cooldown.
- `reports/automation/automation.lock` and `automation_heartbeat.json` prevent accidentally running two automation workers.
- Use `stop_automation.bat` when you want to stop the worker and clear the runtime lock.
