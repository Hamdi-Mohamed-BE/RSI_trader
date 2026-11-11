@echo off
setlocal
title Calyx - Best 1-Step (no guard)
echo.
echo  BEST 1-STEP - installs 11 EAs (Core 9 + Overnight Bias ORB + Gold Band Wave) on the MT5 account
echo  that is open now. NO GUARD: no FTMO / prop limits, no shared daily stop, no adaptive governor.
echo  Risk is per trade per EA and stacks across open trades. The installer asks risk type and amount,
echo  the Nasdaq stop and the Nasdaq DI (tested OFF) / USDJPY DI (tested ON), shows everything, then
echo  restarts that MT5 once into a new 11-chart profile. It never places orders.
echo.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\Packages\Best1Step\Install-Portfolio.ps1" %*
set "CALYX_EXIT=%ERRORLEVEL%"
if /I not "%~1"=="-ValidateOnly" pause
exit /b %CALYX_EXIT%
