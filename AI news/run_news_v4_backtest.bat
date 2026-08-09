@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Python environment is missing. Run run.bat once first.
  pause
  exit /b 1
)

echo Running frozen NFP, CPI, and FOMC V4 replay...
.venv\Scripts\python.exe backtest_news_v4.py
if errorlevel 1 (
  echo V4 backtest failed. Review the error above.
  pause
  exit /b 1
)

echo.
echo V4 report is ready: NEWS_V4_3M_RESULTS.md
pause
