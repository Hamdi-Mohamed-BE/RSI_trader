@echo off
setlocal
title XAU WEAKNESS - LIVE
cd /d "%~dp0"
if not exist ".venv\Scripts\xau-weakness.exe" (
  uv sync --extra dev || goto :error
)
".venv\Scripts\xau-weakness.exe" live
if errorlevel 1 goto :error
exit /b 0
:error
echo.
echo XAU Weakness stopped with an error.
pause
exit /b 1
