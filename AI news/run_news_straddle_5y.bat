@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Virtual environment not found. Run the project setup first.
  pause
  exit /b 1
)

echo Preparing the five-year USD news event list...
".venv\Scripts\python.exe" export_news_tick_manifest.py || goto :failed

echo Downloading and reusing cached XAUUSD release ticks...
node download_news_ticks.js "data\xau-news-ticks-5y\manifest.json" "data\xau-news-ticks-5y" 6 || goto :failed

echo Running the spread-aware straddle optimization...
".venv\Scripts\python.exe" optimize_news_straddle_5y.py || goto :failed

echo.
echo Complete. Open NEWS_STRADDLE_TICK_5Y.md for the report.
pause
exit /b 0

:failed
echo.
echo Study failed. Review the message above.
pause
exit /b 1
