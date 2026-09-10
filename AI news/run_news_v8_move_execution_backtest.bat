@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" backtest_news_v8_move_execution_3m.py
) else (
  python backtest_news_v8_move_execution_3m.py
)
if errorlevel 1 (
  echo.
  echo V8 backtest failed.
  pause
  exit /b 1
)
echo.
echo Results saved to NEWS_V8_MOVE_EXECUTION_3M_RESULTS.md
pause
