@echo off
setlocal
title XAU SAFE GRID - BACKTEST
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" uv sync --extra dev
".venv\Scripts\python.exe" -m xau_grid.cli backtest --days 365
echo.
pause
