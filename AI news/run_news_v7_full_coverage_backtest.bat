@echo off
setlocal
cd /d "%~dp0"

where uv >nul 2>nul
if errorlevel 1 (
  echo uv is required. Install it from https://docs.astral.sh/uv/
  pause
  exit /b 1
)

uv sync
if errorlevel 1 goto :failed
uv run python backtest_news_v7_full_coverage.py
if errorlevel 1 goto :failed

echo.
echo V7 full-coverage model and reports completed.
pause
exit /b 0

:failed
echo.
echo V7 full-coverage build failed. Review the message above.
pause
exit /b 1
