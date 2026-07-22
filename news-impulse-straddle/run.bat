@echo off
setlocal
cd /d "%~dp0"

echo.
echo XAU News Straddle Runner
echo ------------------------
echo Current config: config.best.json
echo Format example: 2026-07-15 08:30
echo IMPORTANT: enter New York news time, not UTC.
echo The bot will convert to UTC and wait automatically.
echo.

set /p NEWS_TIME=Enter New York news time: 
if "%NEWS_TIME%"=="" (
  echo No news time entered. Exiting.
  pause
  exit /b 1
)

echo.
echo Choose mode:
echo   1 = Dry run only, no orders placed
echo   2 = Execute on MT5 demo/live account
echo.
set /p MODE=Mode [1]: 

if "%MODE%"=="2" (
  echo.
  echo EXECUTE MODE SELECTED.
  echo Make sure MT5 is on the correct DEMO account.
  echo Press CTRL+C now to cancel, or any key to continue.
  pause >nul
  python news_straddle_bot.py --news-time "%NEWS_TIME%" --execute
) else (
  python news_straddle_bot.py --news-time "%NEWS_TIME%" --dry-run
)

echo.
pause
