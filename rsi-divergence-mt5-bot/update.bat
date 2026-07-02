@echo off
setlocal
cd /d "%~dp0"
title Update Telegram MT5 Copier

where uv >nul 2>nul
if errorlevel 1 (
  echo uv is required: https://docs.astral.sh/uv/
  pause
  exit /b 1
)

echo Updating copier dependencies...
echo You may leave the old rsi-bot.exe alone; this app runs directly from source.
call uv sync --no-install-project --inexact
if errorlevel 1 goto :failed

echo.
echo Update complete. You can now start run.bat.
pause
exit /b 0

:failed
echo Update failed. Close any Python or copier windows and try again.
pause
exit /b 1
