@echo off
setlocal

if /I "%~1" NEQ "--visible" (
    start "Arbitrage Framework" /normal cmd /k ""%~f0" --visible"
    exit /b
)

cd /d "%~dp0"
title Arbitrage Framework

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
echo Arbitrage Framework is starting.
echo This strategy needs multiple independent price feeds before real arbitrage trading is useful.
echo This window is the Arbitrage process. Closing it stops this visible bot session.
echo Press Ctrl+C in this window to stop.
echo.

".venv\Scripts\python.exe" -m app.strategy_bot_worker --bot arbitrage

pause
