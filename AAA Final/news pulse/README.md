# XAUUSD News Pulse

Independent deterministic MT5 execution worker around the existing prediction-only AI News models. It preserves `execution_capability=false`; the model never sends an order.

## Current research selection

- PPI only
- OCO buy-stop/sell-stop around the completed T-60 through T-31 range
- 90 pips where one gold pip is `$0.10` (`$9` stop distance)
- 5R target and one Fibonacci re-entry
- unfilled orders expire at T+15; positions time out after 180 minutes

The T-30 range and early prediction are sealed. The T-15 prediction is final. Late starts, stale bars, post-release data, low confidence, invalid spread/margin, duplicate state, and minimum-lot risk violations all produce `NO_TRADE`.

## Commands

- Tests: `uv sync --extra dev && uv run pytest`
- Backtest: `uv run news-pulse backtest`
- One safe paper cycle: `run.bat`
- Continuous live worker: `run_live.bat`

The working `.env` is live-enabled. The worker refreshes the high-impact USD calendar automatically, keeps the frozen historical calendar for research, and fails closed if no valid future event is available. The `paper` command forcibly disables sending even when the working `.env` is live.

All three execution gates must remain aligned: `LIVE_TRADING=true`, `PLACE_ORDERS=true`, and `DRY_RUN=false`. The selected live event-family filter remains PPI-only because that is the only provisionally validated family in the current research.

State is stored in `state/news-pulse.json`; logs are stored in `logs/news-pulse.log`. The worker owns only magic `860301`.
