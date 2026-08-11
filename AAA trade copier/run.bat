@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if not exist ".env" (
  echo First run detected. Preparing AAA Trade Copier...
  call dev.bat setup || exit /b 1
)

if not exist ".venv\Scripts\aaa-trade-copier-web.exe" (
  echo Python environment is incomplete. Preparing AAA Trade Copier...
  call dev.bat setup || exit /b 1
)

echo Ensuring the default dashboard user is ready...
uv run aaa-trade-copier ensure-admin || exit /b 1

echo Starting AAA Trade Copier...
call dev.bat start || exit /b 1

timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:8100"
echo Dashboard: http://127.0.0.1:8100
exit /b 0
