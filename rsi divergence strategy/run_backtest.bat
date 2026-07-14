@echo off
setlocal
cd /d "%~dp0"

set PYTHON=C:\Users\hama101\Desktop\geek\ai trader\rsi-divergence-mt5-bot\.venv\Scripts\python.exe
set PYTHONUTF8=1

echo Running RSI divergence 60-day backtest...
"%PYTHON%" rsi_divergence_bot.py --backtest --days 60 --balance 300 --risk 4 --use-optimized --symbols AUDUSD,XAUUSD,GBPCHF,AUDCAD,XAGUSD

echo.
pause
