@echo off
cd /d "%~dp0"
uv run nasdaq-weakness backtest
pause
