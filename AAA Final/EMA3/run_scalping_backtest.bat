@echo off
setlocal
title EMA3 - M1 M5 M15 SCALPING BACKTEST
cd /d "%~dp0"
uv sync
uv run ema3-compare-timeframes --symbols XAUUSD --timeframes M1,M5,M15 --days 30 --risk-pct 1 --output reports\scalping_30d
pause
