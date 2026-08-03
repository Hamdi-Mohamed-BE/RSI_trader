@echo off
setlocal
cd /d "%~dp0"
echo Running nested chronological XAUUSD weekend-direction V2 research...
".venv\Scripts\python.exe" backtest_weekend_direction_v2.py --refresh-context
if errorlevel 1 (
  echo.
  echo V2 research failed. Review the message above.
  pause
  exit /b 1
)
echo.
echo Finished. Open GOLD_WEEKEND_DIRECTION_V2.md for the report.
pause
