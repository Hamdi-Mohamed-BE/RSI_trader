@echo off
setlocal
title Calyx - Best 1-Step (no guard)
echo.
echo  BEST 1-STEP - installs 7 EAs (Nasdaq 5M, ONB, EMA3, Gold Band Wave, ORB VP VC, RSI VWAP, UK100) on the MT5 account
echo  that is open now. NO GUARD: no FTMO / prop limits, no shared daily stop, no adaptive governor.
echo  Risk is per trade per EA and stacks across open trades. The installer asks risk type and amount,
echo  the Nasdaq stop, the Nasdaq DI (tested OFF) and the weekend flat, shows everything, then
echo  restarts that MT5 once into a new 7-chart profile. It never places orders.
echo.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\Packages\Best1Step\Install-Portfolio.ps1" -UsdJpyDIFilter OFF %*
set "CALYX_EXIT=%ERRORLEVEL%"
if /I not "%~1"=="-ValidateOnly" pause
exit /b %CALYX_EXIT%
