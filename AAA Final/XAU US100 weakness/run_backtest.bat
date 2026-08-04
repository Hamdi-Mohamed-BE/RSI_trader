@echo off
setlocal
title XAU US100 WEAKNESS - BACKTEST
cd /d "%~dp0"
set "ENGINE=%~dp0..\US100 weekness"
set "PYTHONPATH=%ENGINE%\src"
"%ENGINE%\.venv\Scripts\nasdaq-weakness.exe" backtest
pause
