@echo off
setlocal

if /I "%~1" NEQ "--visible" (
    start "20 Pip Challenge Bot" /normal cmd /k ""%~f0" --visible"
    exit /b
)

cd /d "%~dp0"
title 20 Pip Challenge Bot

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
echo 20 Pip Challenge bot is starting.
echo It uses a separate challenge wallet and magic number.
echo Live order sending requires CHALLENGE20_LIVE_TRADING=true and CHALLENGE20_PLACE_TRADES=true in .env.
echo This window is the challenge process. Closing it stops the visible bot session.
echo Press Ctrl+C in this window to stop.
echo.

".venv\Scripts\python.exe" scripts\clear_stale_20pip_lock.py

".venv\Scripts\python.exe" -m app.challenge_20pip

pause
