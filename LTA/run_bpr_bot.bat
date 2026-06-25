@echo off
setlocal

if /I "%~1" NEQ "--visible" (
    start "BPR Bot" /normal cmd /k ""%~f0" --visible"
    exit /b
)

cd /d "%~dp0"
title BPR Bot

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
echo BPR bot is starting.
echo It trades Balanced Price Range retests formed by overlapping opposite FVGs.
echo Live order sending requires BPR_LIVE_TRADING=true and BPR_PLACE_TRADES/BPR_PLACE_PENDING=true in .env.
echo This window is the BPR process. Closing it stops the visible bot session.
echo Press Ctrl+C in this window to stop.
echo.

".venv\Scripts\python.exe" -m app.bpr_bot

pause
