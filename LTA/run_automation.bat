@echo off
setlocal

if /I "%~1" NEQ "--visible" (
    start "LTA A+ Setup Automation" /normal cmd /k ""%~f0" --visible"
    exit /b
)

cd /d "%~dp0"
title LTA A+ Setup Automation

if not exist ".venv\Scripts\python.exe" (
    echo Creating local Python environment...
    py -3 -m venv .venv 2>NUL
    if errorlevel 1 (
        python -m venv .venv
    )
)

echo Checking dependencies...
".venv\Scripts\python.exe" -c "import fastapi, uvicorn, jinja2, pandas, numpy, MetaTrader5" >NUL 2>NUL
if errorlevel 1 (
    echo Installing dependencies...
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)

echo.
echo LTA automation is starting.
echo It scans MT5 and prepares A+ trade tickets.
echo Live order sending requires LIVE_TRADING=true and AUTO_PLACE_TRADES=true in .env.
echo This window is the automation process. Closing it stops the visible bot session.
echo Press Ctrl+C in this window to stop.
echo.

".venv\Scripts\python.exe" -m app.automation

pause
