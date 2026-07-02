@echo off
setlocal
cd /d "%~dp0"
title Telegram User API Login
call uv sync
if errorlevel 1 goto :failed
call uv run python -m telegram_mt5_copier.login
pause
exit /b %errorlevel%

:failed
echo Setup failed.
pause
exit /b 1
