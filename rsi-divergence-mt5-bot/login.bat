@echo off
setlocal
cd /d "%~dp0"
title Telegram User API Login
if not exist ".venv\Scripts\python.exe" (
  call uv sync --no-install-project --inexact
  if errorlevel 1 goto :failed
)
set "PYTHONPATH=%CD%\src;%PYTHONPATH%"
call ".venv\Scripts\python.exe" -m telegram_mt5_copier.login
pause
exit /b %errorlevel%

:failed
echo Setup failed.
pause
exit /b 1
