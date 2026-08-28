@echo off
setlocal
cd /d "%~dp0"
uv run bookmaper signals --refresh
if errorlevel 1 (
  echo.
  echo ERROR: Signal refresh failed.
  pause
  exit /b 1
)
echo.
echo Current probabilities were saved to artifacts\current-signals.json.
pause
