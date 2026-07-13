@echo off
setlocal
cd /d "%~dp0"

echo.
echo SATS bot is starting.
echo It scans the Self-Aware Trend System port on MT5 candles.
echo Live order sending requires SATS_LIVE_TRADING=true and SATS_PLACE_ORDERS=true in .env.
echo This window is the SATS process. Closing it stops the visible bot session.
echo Press Ctrl+C in this window to stop.
echo.

if not exist ".venv\Scripts\python.exe" (
    echo Python virtual environment was not found. Run the main setup first.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m app.sats_bot
pause
