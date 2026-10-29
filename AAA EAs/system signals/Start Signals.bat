@echo off
rem Calyx MT5 -> Telegram signal forwarder. Lists the MT5 terminals, asks which one to watch, then forwards every trade event.
rem Extra arguments pass through, e.g.  "Start Signals.bat" --dry-run   or   --test-telegram   or   --terminal 3
setlocal
cd /d "%~dp0"
if not exist ".env" (
  echo No .env file yet. Copy .env.example to .env and fill in TELEGRAM_API_ID / TELEGRAM_API_HASH ^(QR login^) or a bot token.
  echo Or run:  "Start Signals.bat" --dry-run   to see the messages in this window without Telegram.
  echo.
)
python -c "import MetaTrader5, telethon, qrcode" 2>nul
if not errorlevel 1 goto run_python
where uv >nul 2>nul
if not errorlevel 1 goto run_uv
echo Python packages are missing. Install them with:  python -m pip install MetaTrader5 telethon qrcode[pil]
goto end

:run_python
python "%~dp0signals.py" %*
goto end

:run_uv
uv run --no-project --with MetaTrader5 --with telethon --with "qrcode[pil]" python "%~dp0signals.py" %*

:end
echo.
pause
