@echo off
setlocal

if /I "%~1" NEQ "--visible" (
    start "Relative Volume ORB Bot" /normal cmd /k ""%~f0" --visible"
    exit /b
)

cd /d "%~dp0"
title Relative Volume ORB Bot

if not exist ".venv\Scripts\python.exe" (
    py -3 -m venv .venv 2>NUL
    if errorlevel 1 python -m venv .venv
)

".venv\Scripts\python.exe" -c "import pandas, numpy, MetaTrader5" >NUL 2>NUL
if errorlevel 1 ".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :failed

echo.
echo Relative-volume ORB bot is starting.
echo Live orders require RELVOL_ORB_LIVE_TRADING=true and RELVOL_ORB_PLACE_ORDERS=true.
echo Closing this window stops the bot.
echo.

".venv\Scripts\python.exe" -m app.relvol_orb_bot
pause
exit /b %errorlevel%

:failed
echo Setup failed. Review the message above.
pause
exit /b 1
