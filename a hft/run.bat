@echo off
cd /d "%~dp0"
title HFT Scalper

echo Starting MT5 crypto scalper...
echo Edit config.py to change settings. Press Ctrl+C to stop.
echo.

python bot.py
if errorlevel 1 (
    echo.
    echo Bot exited with an error. Run diagnose.bat or: python diagnose.py
    pause
)
