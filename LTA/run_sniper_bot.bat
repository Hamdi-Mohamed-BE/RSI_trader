@echo off
setlocal

if /I "%~1" NEQ "--visible" (
    start "Sniper Bot" /normal cmd /k ""%~f0" --visible"
    exit /b
)

set "LTA_ROOT=%~dp0"
set "SNIPER_ROOT=%~dp0..\sniper entry"

if not exist "%SNIPER_ROOT%\sniper_entry_bot.py" (
    echo Sniper bot folder was not found:
    echo %SNIPER_ROOT%
    pause
    exit /b 1
)

cd /d "%SNIPER_ROOT%"
title Sniper Bot

if not exist "%LTA_ROOT%.venv\Scripts\python.exe" (
    echo Creating local Python environment in LTA folder...
    cd /d "%LTA_ROOT%"
    py -3 -m venv .venv 2>NUL
    if errorlevel 1 (
        python -m venv .venv
    )
    cd /d "%SNIPER_ROOT%"
)

echo Checking dependencies...
"%LTA_ROOT%.venv\Scripts\python.exe" -c "import pandas, numpy, MetaTrader5" >NUL 2>NUL
if errorlevel 1 (
    echo Installing dependencies from LTA requirements...
    "%LTA_ROOT%.venv\Scripts\python.exe" -m pip install -r "%LTA_ROOT%requirements.txt"
)

echo.
echo Sniper Bot is starting.
echo It uses the sniper entry config from the sibling sniper entry folder.
echo This window is the Sniper process. Closing it stops this visible bot session.
echo Press Ctrl+C in this window to stop.
echo.

"%LTA_ROOT%.venv\Scripts\python.exe" sniper_entry_bot.py --loop

pause
