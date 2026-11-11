@echo off
setlocal
title Calyx - Core 9 (no guard)
echo.
echo  CORE 9 - installs 9 EAs on the MT5 account that is open now. NO GUARD: no FTMO / prop limits,
echo  no shared daily stop, no adaptive governor. Risk is per trade per EA and stacks across open trades.
echo  The installer asks risk type and amount, the Nasdaq stop, then Nasdaq and USDJPY DI,
echo  shows everything, then restarts that MT5 once into a new 8-chart profile. It never places orders.
echo.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\Packages\Core9\Install-Portfolio.ps1" %*
set "CALYX_EXIT=%ERRORLEVEL%"
if /I not "%~1"=="-ValidateOnly" pause
exit /b %CALYX_EXIT%
