@echo off
setlocal
cd /d "%~dp0"
set "PYTHONDONTWRITEBYTECODE=1"

title Gold News V9 - Automatic Prediction
echo ==============================================================
echo GOLD NEWS V9 - AUTOMATIC ON-DEMAND PREDICTION
echo ==============================================================
echo This finds the next NFP, CPI, or FOMC event automatically.
echo If started early, it waits until T-15 and refreshes the calendar.
echo.

where uv >nul 2>nul
if errorlevel 1 (
  echo Installing uv...
  powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
  set "PATH=%USERPROFILE%\.local\bin;%USERPROFILE%\.cargo\bin;%PATH%"
)

where uv >nul 2>nul
if errorlevel 1 (
  echo ERROR: uv could not be installed automatically.
  pause
  exit /b 1
)

echo Checking dependencies...
uv sync --quiet
if errorlevel 1 (
  echo ERROR: Dependency setup failed.
  pause
  exit /b 1
)

if not exist "models\gold_news_v9_direction.joblib" (
  echo ERROR: Missing models\gold_news_v9_direction.joblib
  pause
  exit /b 1
)
if not exist "models\gold_news_v8_move_range.joblib" (
  echo ERROR: Missing models\gold_news_v8_move_range.joblib
  pause
  exit /b 1
)

uv run --quiet python -u run_prediction_automatic.py %*
set "RESULT=%ERRORLEVEL%"

echo.
if "%RESULT%"=="0" (
  echo Prediction completed. Logs are in: %~dp0logs
) else (
  echo Prediction stopped with an error. The error is shown above.
  echo Log file: %~dp0logs\prediction-runner.log
)
echo.
pause
exit /b %RESULT%
