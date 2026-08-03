@echo off
setlocal
cd /d "%~dp0"
title XAUUSD Weekend Gap Bot
if not exist ".venv\Scripts\python.exe" (
  echo Missing .venv. Run uv sync first.
  pause
  exit /b 1
)
if not exist ".env.weekend-gap" (
  copy /y ".env.weekend-gap.example" ".env.weekend-gap" >nul
  echo Created .env.weekend-gap with demo-safe defaults.
)
echo This visible window is the weekend-gap worker. Closing it stops the bot.
echo Live placement requires both WEEKEND_GAP_LIVE_TRADING and WEEKEND_GAP_PLACE_ORDERS to be true.
echo.
".venv\Scripts\python.exe" weekend_gap_bot.py
echo.
echo Worker stopped.
pause
