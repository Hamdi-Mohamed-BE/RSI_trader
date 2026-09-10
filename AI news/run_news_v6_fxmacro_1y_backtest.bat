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
uv run python backtest_news_v6_fxmacro_1y.py
if errorlevel 1 goto :failed

echo.
echo FXMacroData one-year audit completed.
pause
exit /b 0

:failed
echo.
echo FXMacroData one-year audit failed. Review the message above.
pause
exit /b 1

