@echo off
setlocal
cd /d "%~dp0"
echo Training the XAUUSD weekend-direction model with a frozen final-year test...
".venv\Scripts\python.exe" train_weekend_direction_model.py --years 5
if errorlevel 1 (
  echo.
  echo Training failed. Review the message above.
  pause
  exit /b 1
)
echo.
echo Finished. Open GOLD_WEEKEND_DIRECTION_5Y.md for the validation report.
pause
