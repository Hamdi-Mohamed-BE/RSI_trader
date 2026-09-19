# Gold News V9 Runtime

This folder contains the production runtime for the XAUUSD NFP, CPI, and FOMC
prediction service and its MetaTrader 5 Expert Advisor.

## Install And Run

1. Open and log in to exactly one MT5 terminal.
2. Run `INSTALL_AND_RUN_GOLD_NEWS_V9.bat`.

The installer uses `uv`, installs the locked Python dependencies, discovers the
active terminal and broker gold symbol, compiles the EA, starts the local
prediction server, and opens XAUUSD M1 with the EA attached.

Live trading is enabled by default on both demo and real accounts. The current
defaults are:

- Events: NFP, CPI, and FOMC
- Prediction lock: T-15 minutes
- Entry: T-10 seconds
- Risk: 0.75% of current balance
- Stop: $20.00 in XAUUSD price
- Target: $4.00 in XAUUSD price
- Time exit: T+15 minutes
- Comment: `AI news {event} {buy/sell} {confidence%}`

## Connection

The server writes a heartbeat, next event, and locked prediction to:

`<MT5 Common Data>\Files\GoldNewsV9EA\bridge.json`

The EA reads this shared file directly. If the file is stale or temporarily
locked, EA version 1.14 falls back to the HTTP API at
`http://127.0.0.1:8799`. A watchdog restarts an exited or unhealthy server and
is registered to start at Windows sign-in.

## Automatic On-Demand Prediction

Double-click `RUN_AUTO_PREDICTION.bat`. It discovers the next supported NFP,
CPI, or FOMC release, refreshes the calendar while waiting, runs at T-15, and
prints a compact XAUUSD direction and move-range report. MT5 must be open and
connected.

Full predictions are written to `predictions`. The readable runner log, latest
report, CSV summary, and JSONL audit log are written to `logs`.

## Logs

Installer and import errors are shown directly in the console. Server output is
also stored in:

- `tmp\gold-news-v9-server.err.log`
- `tmp\gold-news-v9-server.out.log`
- `tmp\gold-news-v9-supervisor.log`

The EA writes status messages to the active terminal's MQL5 Experts journal.
After a successful launch it should report `Initialized` and `Scheduled <event>`.

## Runtime Files

- `app.py`: local FastAPI service
- `ea_file_bridge.py`: MT5 shared-file bridge
- `server_supervisor.py`: prediction-server watchdog
- `Start-GoldNewsV9Server.ps1`: Windows sign-in launcher
- `predict_news.py`: live prediction orchestration
- `run_prediction_automatic.py`: automatic next-event runner and result logger
- `calendar_provider.py`: supported-event calendar feed
- `models\gold_news_v9_direction.joblib`: direction model
- `models\gold_news_v8_move_range.joblib`: move-range model
- `mt5\GoldNewsV9EA.mq5`: EA source
- `mt5\GoldNewsV9EA.ex5`: compiled EA
- `mt5\GoldNewsV9EA-Auto.set`: live defaults
- `Install-GoldNewsV9EA.ps1`: installer implementation
- `INSTALL_AND_RUN_GOLD_NEWS_V9.bat`: one-click launcher
- `RUN_AUTO_PREDICTION.bat`: one-click automatic on-demand prediction

The remaining Python modules in the folder are dependencies imported by the
prediction pipeline.

## Cleanup Archive

`Organize-RuntimePackage.ps1` moves caches, old research, historical backtests,
unused models, and old generated outputs into timestamped folders under
`usless`. It does not delete them. Every completed cleanup archive contains a
`MOVED_ITEMS.txt` manifest.
