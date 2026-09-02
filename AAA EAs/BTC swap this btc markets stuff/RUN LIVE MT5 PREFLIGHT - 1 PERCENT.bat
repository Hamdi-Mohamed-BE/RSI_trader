@echo off
setlocal EnableExtensions DisableDelayedExpansion
title BTC Basis - MT5 Live Preflight - 1 Percent Risk
cd /d "%~dp0"
echo.
echo BTC BASIS - GUARDED MT5 LIVE PREFLIGHT
echo --------------------------------------
echo This checks the broker, both required symbols, Databento and the 1%% risk cap.
echo It will NOT send an order while the current post-2026 strategy is unvalidated.
echo.
if not exist "config\mt5-live.json" (
  copy /y "config\mt5-live.example.json" "config\mt5-live.json" >nul
  echo Created config\mt5-live.json from the safe example.
  echo Edit futures_symbol and add your Databento API key before trying again.
  echo.
)
uv sync
if errorlevel 1 goto :failed
uv run python scripts\check_mt5_live_readiness.py
set "result=%errorlevel%"
echo.
if "%result%"=="0" (
  echo READY.
) else (
  echo NOT READY. No trade was placed.
)
pause
exit /b %result%

:failed
echo.
echo Setup failed. No trade was placed.
pause
exit /b 1
