@echo off
setlocal
cd /d "%~dp0"
uv sync
uv run amd-bot backtest --days 60
pause
