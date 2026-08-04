@echo off
setlocal
title XAU SAFE GRID - OPTIMIZE
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" uv sync --extra dev
".venv\Scripts\python.exe" -m xau_grid.cli optimize --days 550 --validation-days 90 --holdout-days 90 --top 32
echo.
pause
