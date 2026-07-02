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

if not exist ".venv\Scripts\python.exe" (
  echo Preparing the focused copier environment...
  call uv sync --no-install-project --inexact
  if errorlevel 1 goto :failed
)

set "PYTHONPATH=%CD%\src;%PYTHONPATH%"
".venv\Scripts\python.exe" -c "import fastapi, httpx, MetaTrader5, telethon, uvicorn" >nul 2>nul
if errorlevel 1 (
  echo Required packages are missing. Running a dependency update...
  call uv sync --no-install-project --inexact
  if errorlevel 1 goto :failed
)

echo.
echo Telegram MT5 Copier: http://127.0.0.1:8787
echo Closing this window stops the copier.
call ".venv\Scripts\python.exe" -m telegram_mt5_copier.main
exit /b %errorlevel%

:failed
echo Setup failed. Close any older copier windows, run update.bat, then try again.
pause
exit /b 1
