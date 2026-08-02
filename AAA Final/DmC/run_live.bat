@echo off
setlocal
cd /d "%~dp0"
uv sync
uv run dmc-bot account
if errorlevel 1 (
  echo MT5 account connection failed.
  pause
  exit /b 1
)
uv run dmc-bot live
pause
