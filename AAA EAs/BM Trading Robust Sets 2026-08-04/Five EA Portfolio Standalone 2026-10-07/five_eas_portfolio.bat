@echo off
setlocal
title CALYX - FIVE EA PORTFOLIO
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-FivePortfolio.ps1" %*
set "result=%errorlevel%"
echo.
if not "%result%"=="0" echo Setup did not finish. Read the message above; do not run duplicate installers.
pause
exit /b %result%
