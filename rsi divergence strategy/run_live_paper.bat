@echo off
setlocal
cd /d "%~dp0"

set PYTHON=C:\Users\hama101\Desktop\geek\ai trader\rsi-divergence-mt5-bot\.venv\Scripts\python.exe
set PYTHONUTF8=1

set RSI_LIVE_TRADING=false
set RSI_USE_OPTIMIZED=true
set RSI_SYMBOLS=AUDUSD,XAUUSD,GBPCHF,AUDCAD,XAGUSD

echo Starting RSI Divergence paper scanner. No orders will be sent.
echo Closing this window stops the scanner.
echo.

"%PYTHON%" rsi_divergence_bot.py --live-loop

echo.
pause
