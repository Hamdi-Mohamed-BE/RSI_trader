@echo off
setlocal
cd /d "%~dp0"
echo Running the one-year XAUUSD weekend-straddle optimization...
if not exist ".venv\Scripts\python.exe" (
  echo Missing .venv. Run uv sync first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" backtest_weekend_gap_bot.py %*
echo.
echo Report: %CD%\WEEKEND_GAP_BACKTEST_1Y.md
pause
