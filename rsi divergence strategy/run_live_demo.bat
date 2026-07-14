@echo off
setlocal
cd /d "%~dp0"

set PYTHON=C:\Users\hama101\Desktop\geek\ai trader\rsi-divergence-mt5-bot\.venv\Scripts\python.exe
set PYTHONUTF8=1

set RSI_LIVE_TRADING=true
set RSI_REQUIRE_DEMO=true
set RSI_USE_OPTIMIZED=true
set RSI_SYMBOLS=AUDUSD,XAUUSD,GBPCHF,AUDCAD,XAGUSD
set RSI_RISK_MODE=RISK_PERCENT
set RSI_RISK_PERCENT=4

echo ============================================================
echo Starting RSI Divergence DEMO live bot
echo Uses optimized 60-day settings and requires demo/trial MT5.
echo Closing this window stops the bot.
echo ============================================================
echo.

"%PYTHON%" rsi_divergence_bot.py --live-loop

echo.
pause
