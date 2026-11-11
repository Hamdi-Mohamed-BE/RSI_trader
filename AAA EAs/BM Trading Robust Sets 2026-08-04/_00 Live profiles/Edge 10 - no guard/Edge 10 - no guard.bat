@echo off
setlocal
title Calyx - Edge 10 (no guard)
echo.
echo  EDGE 10 - installs 9 EAs (Sell Nasdaq removed) on the MT5 account that is open now. NO GUARD: no FTMO / prop limits,
echo  no shared daily stop, no adaptive governor. Risk is per trade per EA and stacks across open trades.
echo  The installer asks risk type and amount, Nasdaq and USDJPY DI, and the Nasdaq stop version,
echo  shows everything, then restarts that MT5 once into a new 10-chart profile. It never places orders.
echo.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\Packages\Edge10\Install-Portfolio.ps1" %*
set "CALYX_EXIT=%ERRORLEVEL%"
if /I not "%~1"=="-ValidateOnly" pause
exit /b %CALYX_EXIT%
