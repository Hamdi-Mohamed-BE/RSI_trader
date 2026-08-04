@echo off
setlocal
title XAU WEAKNESS - BACKTEST
cd /d "%~dp0"
if not exist ".venv\Scripts\xau-weakness.exe" uv sync --extra dev || goto :error
".venv\Scripts\xau-weakness.exe" backtest --days 365 --balance 10000
pause
exit /b %errorlevel%
:error
pause
exit /b 1
