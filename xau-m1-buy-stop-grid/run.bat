@echo off
setlocal
cd /d "%~dp0"

set PYTHONUTF8=1
set "PYTHON=%~dp0.venv\Scripts\python.exe"

if not exist "%PYTHON%" set "PYTHON=python"

echo ============================================================
echo XAU M1 Buy-Stop Grid
echo Reads .env, finds broker XAUUSD symbol, and places/dry-runs
echo buy stops above the live ask and sell stops below the live bid.
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
