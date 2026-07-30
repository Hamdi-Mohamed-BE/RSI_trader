# US100 / Nasdaq New York Session Bot

Python-to-MT5 implementation matching the existing trading-project architecture.
It supports broker symbol discovery, real broker-history backtests, walk-forward
research, HTML/CSV reporting, dry-run scanning, and safety-locked MT5 execution.

## Install

1. Open and log into MetaTrader 5. Keep the desired account connected.
2. In this folder run `uv sync --extra dev`.
3. Run `run_discover.bat` to verify the selected broker symbol and conversion.
4. Run `run_backtest.bat` for the latest complete 365 days.
5. Open `reports/US100_report.html`.

No login, password, or terminal path is required; the bot uses the account already
connected in MT5.

## Commands

```powershell
uv run us100-bot --env .env discover
uv run us100-bot --env .env backtest
uv run us100-bot --env .env backtest --start 2025-08-01 --end 2026-07-31
uv run us100-bot --env .env live --once
uv run us100-bot --env .env live
```

`run_live_dry.bat` is signal-only with the supplied `.env`. To permit demo order
submission deliberately set:

```text
ENABLE_TRADING=true
DRY_RUN=false
DEMO_ONLY=true
```

Keep `DEMO_ONLY=true` until forward testing is complete. The default risk is 0.50%
combined for Strategy A (0.25% per leg) and 0.50% for a Strategy B entry.

## Output

- `data/`: compressed broker M1 history.
- `reports/backtest_trades.csv`: baseline fills and exits.
- `reports/monthly_results.csv`: combined monthly breakdown.
- `reports/monthly_by_strategy.csv`: monthly rows per component.
- `reports/walk_forward_oos_trades.csv`: unseen walk-forward trades.
- `reports/robustness_results.csv`: spread/slippage/parameter stress tests.
- `reports/US100_report.html`: complete readable report and charts.
- `logs/`: runtime log.
- `state/`: restart-safe daily execution state.

See [STRATEGY_SPEC.md](STRATEGY_SPEC.md) for exact rules and assumptions.
See [RESEARCH_FINDINGS.md](RESEARCH_FINDINGS.md) for the completed one-year results
and the safety-locked B2 research profile.
