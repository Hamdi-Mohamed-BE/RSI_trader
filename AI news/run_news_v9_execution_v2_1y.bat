@echo off
setlocal
cd /d "%~dp0"
uv sync
if errorlevel 1 exit /b 1
uv run python backtest_news_v9_execution_v2_1y.py
pause
