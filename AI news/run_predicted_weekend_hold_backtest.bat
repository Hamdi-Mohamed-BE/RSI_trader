@echo off
setlocal
cd /d "%~dp0"
echo Backtesting the predicted-direction XAUUSD weekend hold...
".venv\Scripts\python.exe" backtest_predicted_weekend_hold.py
if errorlevel 1 (
  echo.
  echo Backtest failed. Review the message above.
  pause
  exit /b 1
)
echo.
echo Finished. Open PREDICTED_WEEKEND_HOLD_BACKTEST.md for the report.
pause
