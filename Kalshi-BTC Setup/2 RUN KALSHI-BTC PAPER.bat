@echo off
title Kalshi-BTC - PAPER MODE (no real orders)
setlocal
cd /d "%~dp0..\Kalshi-BTC" || (echo Run "1 SETUP KALSHI-BTC (PAPER).bat" first. & pause & exit /b 1)
if not exist "venv\Scripts\python.exe" (echo Run setup first. & pause & exit /b 1)
set "ARGS=--paper --risk-pct 20 --starting-balance-cents 11500 --trade-log local/paper_trade_log.json --json-out local/paper_latest.json"
echo Startup check (one snapshot)...
"venv\Scripts\python.exe" scripts\btc15_live_monitor.py %ARGS% --once --no-color
echo.
echo If the check above shows PAPER with no authentication error, the monitor starts now.
echo Press Ctrl+C to stop. Paper trades are saved in Kalshi-BTC\local\paper_trade_log.json
pause
"venv\Scripts\python.exe" scripts\btc15_live_monitor.py %ARGS%
pause
