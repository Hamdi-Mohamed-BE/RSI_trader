@echo off
setlocal
title Calyx - Mixed 22 (no guard)
echo.
echo  MIXED 22 - installs 22 EAs on the MT5 account that is open now. NO GUARD: no FTMO / prop limits,
echo  no shared daily stop, no adaptive governor. Risk is per trade per EA and stacks across open trades.
echo  The installer asks risk type and amount, Nasdaq and USDJPY DI, and the Nasdaq stop version,
echo  shows everything, then restarts that MT5 once into a new 22-chart profile. It never places orders.
echo.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\Packages\Mixed22\Install-Portfolio.ps1" %*
set "CALYX_EXIT=%ERRORLEVEL%"
if /I not "%~1"=="-ValidateOnly" pause
exit /b %CALYX_EXIT%
