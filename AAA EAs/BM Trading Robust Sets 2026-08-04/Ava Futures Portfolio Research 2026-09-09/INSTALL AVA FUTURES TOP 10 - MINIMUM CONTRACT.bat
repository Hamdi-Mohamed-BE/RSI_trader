@echo off
setlocal
title Calyx - Install Ava Futures Top 10
echo Only gold News Pulse is enabled; silver and other non-gold news OFF.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-AvaFuturesTop10.ps1"
if errorlevel 1 (
  echo.
  echo Ava Futures installation did not finish. Read the message above.
) else (
  echo.
  echo Ava Futures installation finished.
)
pause
endlocal
