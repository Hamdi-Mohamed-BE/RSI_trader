@echo off
setlocal
cd /d "%~dp0"
uv run bookmaper all --refresh
if errorlevel 1 (
  echo.
  echo ERROR: The backtest did not complete. Review the message above.
  pause
  exit /b 1
)
echo.
echo Finished. Open artifacts\FULL REPORT.md and the PNG equity graphs.
pause
