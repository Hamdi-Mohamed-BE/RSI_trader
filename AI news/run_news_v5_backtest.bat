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

if not exist "models\gold_news_v4.joblib" (
  uv run python backtest_news_v4.py
  if errorlevel 1 goto :failed
)

uv run python backtest_news_v5.py
if errorlevel 1 goto :failed

echo.
echo V5 model and three-month comparison completed.
pause
exit /b 0

:failed
echo.
echo V5 backtest failed. Review the message above.
pause
exit /b 1
