@echo off
title AAA FINAL - EMA3
setlocal
cd /d "%~dp0"
echo ============================================================
echo  AAA FINAL - EMA3 BOT
echo ============================================================
echo.
uv sync
uv run ema3-live
pause
