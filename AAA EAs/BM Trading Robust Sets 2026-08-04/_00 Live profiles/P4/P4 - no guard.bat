@echo off
setlocal
title Calyx - P4 (no guard)
echo.
echo  P4 - installs 4 EAs (Overnight Bias ORB, Nasdaq 5M, EMA3, Gold Band Wave) on the MT5 account
echo  that is open now. NO GUARD: no FTMO / prop limits, no shared daily stop, no adaptive governor.
echo  Risk is per trade per EA and stacks across open trades. The installer asks risk type and amount,
echo  the Nasdaq stop and the Nasdaq DI (tested OFF), shows everything, then restarts that MT5 once
echo  into a new 4-chart profile. It never places orders.
echo.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\Packages\P4\Install-Portfolio.ps1" -UsdJpyDIFilter OFF %*
set "CALYX_EXIT=%ERRORLEVEL%"
if /I not "%~1"=="-ValidateOnly" pause
exit /b %CALYX_EXIT%
