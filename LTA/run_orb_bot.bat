@echo off
setlocal

if /I "%~1" NEQ "--visible" (
    start "ORB Bot" /normal cmd /k ""%~f0" --visible"
    exit /b
)

cd /d "%~dp0"
title ORB Bot

if not exist ".venv\Scripts\python.exe" (
    echo Creating local Python environment...
    py -3 -m venv .venv 2>NUL
    if errorlevel 1 (
        python -m venv .venv
    )
)

echo Checking dependencies...
".venv\Scripts\python.exe" -c "import pandas, numpy, MetaTrader5" >NUL 2>NUL
if errorlevel 1 (
    echo Installing dependencies...
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)

echo.
echo ORB bot is starting.
echo It uses a separate ORB magic number, state file, and live switches.
echo Live order sending requires ORB_LIVE_TRADING=true and ORB_PLACE_TRADES=true in .env.
echo Pending stop sending also requires ORB_PLACE_PENDING=true.
echo This window is the ORB process. Closing it stops the visible bot session.
echo Press Ctrl+C in this window to stop.
echo.

".venv\Scripts\python.exe" scripts\clear_stale_orb_lock.py

".venv\Scripts\python.exe" -m app.orb_bot

pause
