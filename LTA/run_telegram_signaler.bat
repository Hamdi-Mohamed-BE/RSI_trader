@echo off
setlocal EnableExtensions

if /I not "%~1"=="--visible" (
    start "Telegram Trade Signaler" /normal cmd /k ""%~f0" --visible"
    exit /b 0
)

cd /d "%~dp0"
title Telegram Trade Signaler

if not exist ".venv\Scripts\python.exe" (
    echo Creating local Python environment...
    py -3 -m venv .venv 2>NUL
    if errorlevel 1 python -m venv .venv
)

echo Checking dependencies...
".venv\Scripts\python.exe" -c "import matplotlib, MetaTrader5" >NUL 2>NUL
if errorlevel 1 (
    echo Installing dependencies...
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)

echo.
echo Telegram trade signaler is starting.
echo It watches MT5 only and never places or modifies trades.
echo Configure TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env.
echo This window stays visible. Closing it stops Telegram notifications.
echo Press Ctrl+C to stop.
echo.

".venv\Scripts\python.exe" -m app.telegram_signaler

echo.
pause
