@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" backtest_news_v8_one_year.py
) else (
  python backtest_news_v8_one_year.py
)
if errorlevel 1 (
  echo.
  echo One-year V8 replay failed.
  pause
  exit /b 1
)
echo.
echo Results saved to NEWS_V8_ONE_YEAR_RESULTS.md
pause
