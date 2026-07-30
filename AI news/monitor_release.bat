@echo off
setlocal
cd /d "%~dp0"

set /p PREDICTION_FILE=Enter the saved prediction JSON path: 
if not defined PREDICTION_FILE exit /b 1

uv sync
if errorlevel 1 (
  echo Dependency setup failed.
  pause
  exit /b 1
)

uv run python monitor_release.py "%PREDICTION_FILE%"
echo.
pause
