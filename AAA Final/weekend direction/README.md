# XAUUSD Friday Weekend Direction

Independent Friday-close worker with broker-session inference, persistent week IDs, risk-safe MT5 sizing, gap-aware exits, and strict model validation gates.

The saved weekend model is rejected (`validated=false`), so the default action is always `NO_TRADE`. `ALLOW_PROVISIONAL_MOMENTUM_MODE=true` enables the separately researched Friday-momentum rule only on a demo account. It does not rehabilitate or authorize the rejected model.

The provisional rule:

- infers Friday close and weekly reopen from historical M1 gaps;
- at T−4 calculates the completed 24-hour return;
- compares it with the rolling 70th percentile from earlier Fridays only;
- opens one same-direction position with a `$30` stop and `3R` target;
- closes remaining exposure on the first executable reopening tick, including adverse gap slippage.

## Commands

- Tests: `uv sync --extra dev && uv run pytest`
- Backtest: `uv run weekend-direction backtest`
- One safe paper cycle: `run.bat`
- Continuous validation-gated live worker: `run_live.bat`

The working `.env` is live-enabled, but the rejected model gate is independent of the order switches and currently forces `NO_TRADE`. This keeps the process deployment-ready without authorizing a failed model. The `paper` command forcibly disables sending regardless of `.env`. State and logs live under `state/` and `logs/`; magic number `860302` isolates ownership.
