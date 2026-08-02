@echo off
setlocal
cd /d "%~dp0"
uv sync --extra dev
uv run dmc-bot backtest --days 60
pause
