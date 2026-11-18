@echo off
setlocal
title Calyx Best 1-Step - all-in-one setup
echo.
echo  BEST 1-STEP ALL-IN-ONE: pick the account type (FTMO 1-Step challenge / funded, FTMO 2-Step, The5ers, FundingPips)
echo  and it does the rest: downloads the news calendar, sets up the daily calendar task, then runs the right
echo  Best 1-Step installer with the right answers (risk, weekend flat, no-opposite, news guard). You still press Enter
echo  for each EA and type the installer confirmation. MT5 restarts into a new profile with Algo Trading OFF.
echo  Before you continue: MT5 open and logged in, account FLAT, Algo Trading OFF, hedging account.
echo.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Setup-Best1Step.ps1" %*
set "CALYX_EXIT=%ERRORLEVEL%"
if /I not "%~1"=="-ValidateOnly" pause
exit /b %CALYX_EXIT%
