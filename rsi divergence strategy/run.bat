@echo off
setlocal
cd /d "%~dp0"

set PYTHONUTF8=1
set PYTHON=C:\Users\hama101\Desktop\geek\ai trader\rsi-divergence-mt5-bot\.venv\Scripts\python.exe

if not exist "%PYTHON%" (
  set PYTHON=python
)

echo ============================================================
echo RSI Divergence Live Bot
echo Uses .env + optimized_configs.json.
echo Connects to the currently logged-in MT5 account and can place orders.
echo Closing this window stops the bot.
echo ============================================================
echo.

"%PYTHON%" "%~dp0rsi_divergence_bot.py" --live-loop

echo.
pause
