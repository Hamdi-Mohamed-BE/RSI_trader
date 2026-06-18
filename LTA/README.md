# LTA A+ Setup Research Platform

Local FastAPI app for testing LTA Concepts-style A+ setups on:

- XAUUSD
- XAGUSD
- BTCUSD

The app is built for research and backtesting. Live trading is disabled by default, and live order placement is intentionally not implemented in this first version.

Choose `ALL SYMBOLS` in the symbol selector to backtest XAUUSD, XAGUSD, and BTCUSD together. The combined dashboard shows one shared equity curve plus a per-symbol watchlist using each symbol's configured lot size.

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
3. Make sure XAUUSD, XAGUSD, and BTCUSD are visible in Market Watch.
4. Install the Python requirements.
5. Run the app and disable demo fallback if you want MT5-only testing.

## Safety

The strategy gate only allows score 90+ A+ setups into simulation. The risk manager can still reject a setup if lot size, drawdown, daily loss, or risk-to-reward rules fail.

Default risk settings live in `.env.example`. Copy it to `.env` if you want local defaults.

## Automation Worker

Use `run_automation.bat` to scan MT5 continuously for A+ setups.

Defaults:

- XAUUSD lot: `0.05`
- XAGUSD lot: `0.05`
- BTCUSD lot: `0.08`
- Scan timeframes: `M5,M15,M30,H1,H4`
- Scan interval: `60` seconds
- Minimum setup score: `90`
- Minimum R:R: `2.0`

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
- `reports/automation/automation.lock` and `automation_heartbeat.json` prevent accidentally running two automation workers.
- Use `stop_automation.bat` when you want to stop the worker and clear the runtime lock.
