@echo off
setlocal
cd /d "%~dp0"
title Telegram MT5 Copier

where uv >nul 2>nul
if errorlevel 1 (
  echo uv is required: https://docs.astral.sh/uv/
  pause
  exit /b 1
)

if not exist ".env" copy /y ".env.example" ".env" >nul
echo Syncing the focused copier environment...
call uv sync
if errorlevel 1 goto :failed

echo.
echo Telegram MT5 Copier: http://127.0.0.1:8787
echo Closing this window stops the copier.
call uv run python -m telegram_mt5_copier.main
exit /b %errorlevel%

:failed
echo Setup failed. Review the message above.
pause
exit /b 1
