@echo off
setlocal
cd /d "%~dp0"
title NAW LTA Web

where uv >nul 2>nul
if errorlevel 1 (
  echo uv is required. Install it from https://docs.astral.sh/uv/
  pause
  exit /b 1
)

if not exist ".env" copy /y ".env.example" ".env" >nul

echo Syncing Python environment...
call uv sync
if errorlevel 1 goto :failed

where npm.cmd >nul 2>nul
if errorlevel 1 (
  echo npm is required to build the Tailwind stylesheet.
  pause
  exit /b 1
)

echo Building the interface...
call npm.cmd install --no-audit --no-fund
if errorlevel 1 goto :failed
call npm.cmd run build:css
if errorlevel 1 goto :failed

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_workers.ps1"

echo.
echo NAW LTA is opening at http://127.0.0.1:8010
echo This window is the web server. Press Ctrl+C to stop it.
call uv run uvicorn naw_lta.main:app --host 127.0.0.1 --port 8010
exit /b %errorlevel%

:failed
echo Setup failed. Review the message above.
pause
exit /b 1

