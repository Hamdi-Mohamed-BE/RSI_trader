@echo off
setlocal
title XAU SAFE GRID - LIVE
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" uv sync
".venv\Scripts\python.exe" -m xau_grid.cli live
echo.
pause
