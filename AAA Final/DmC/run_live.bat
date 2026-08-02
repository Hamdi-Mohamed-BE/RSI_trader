@echo off
title AAA FINAL - DMC
setlocal
cd /d "%~dp0"
echo ============================================================
echo  AAA FINAL - DMC BOT
echo ============================================================
echo.
uv sync
uv run dmc-bot account
if errorlevel 1 (
  echo MT5 account connection failed.
  pause
  exit /b 1
)
uv run dmc-bot live
pause
