@echo off
setlocal
cd /d "%~dp0"

set PYTHONUTF8=1
set PYTHON=C:\Users\hama101\Desktop\geek\ai trader\rsi-divergence-mt5-bot\.venv\Scripts\python.exe

if not exist "%PYTHON%" (
  set PYTHON=python
)

echo ============================================================
echo XAU M1 Buy-Stop Grid
echo Reads .env, finds broker XAUUSD symbol, and places/dry-runs
echo buy stops above the latest closed M1 high and sell stops
echo below the latest closed M1 low.
echo ============================================================
echo.

"%PYTHON%" "%~dp0xau_m1_buy_stop_grid.py"
set EXIT_CODE=%ERRORLEVEL%

echo.
if not "%EXIT_CODE%"=="0" (
  echo BOT FAILED - no valid order batch was completed. Exit code: %EXIT_CODE%
) else (
  echo BOT FINISHED SUCCESSFULLY.
)
pause
exit /b %EXIT_CODE%
