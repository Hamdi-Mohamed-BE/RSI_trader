@echo off
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" "backtest_news_v9_direction_1y.py"
  if errorlevel 1 goto :error
  ".venv\Scripts\python.exe" "backtest_news_v9_risk_1pct_1y.py"
) else (
  where uv >nul 2>nul
  if errorlevel 1 (
    echo Python environment not found. Run run.bat once first.
    goto :error
  )
  uv run python "backtest_news_v9_direction_1y.py"
  if errorlevel 1 goto :error
  uv run python "backtest_news_v9_risk_1pct_1y.py"
)

if errorlevel 1 goto :error
echo.
echo Saved NEWS_V9_RISK_1PCT_1Y_RESULTS.md
pause
exit /b 0

:error
echo.
echo One-year 1%% risk replay failed.
pause
exit /b 1
