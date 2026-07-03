@echo off
setlocal

if /I "%~1" NEQ "--visible" (
    start "LTA A+ Setup Automation" /normal cmd /k ""%~f0" --visible"
    exit /b
)

cd /d "%~dp0"
title LTA A+ Setup Automation

if not exist ".venv\Scripts\python.exe" (
    py -3 -m venv .venv 2>NUL
    if errorlevel 1 python -m venv .venv
)

".venv\Scripts\python.exe" -c "import pandas, numpy, MetaTrader5" >NUL 2>NUL
if errorlevel 1 ".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :failed

echo.
echo LTA bot is starting.
echo Sizing mode is controlled by LOT_SIZING_MODE in .env.
echo Closing this window stops the LTA bot.
echo.

".venv\Scripts\python.exe" -m app.automation
pause
exit /b %errorlevel%

:failed
echo LTA setup failed. Review the message above.
pause
exit /b 1
