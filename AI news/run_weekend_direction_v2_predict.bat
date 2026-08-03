@echo off
setlocal
cd /d "%~dp0"
".venv\Scripts\python.exe" predict_weekend_direction_v2.py
echo.
pause
