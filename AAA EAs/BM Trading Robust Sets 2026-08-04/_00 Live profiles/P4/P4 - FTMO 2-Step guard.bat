@echo off
setlocal
title Calyx - P4, FTMO 2-Step guard
echo.
echo  P4, FTMO 2-STEP - installs 4 guarded EAs (Overnight Bias ORB, Nasdaq 5M, EMA3, Gold Band Wave)
echo  on the MT5 account that is open now. Limits enforced on new entries: 3%% daily reserve, 92%% equity
echo  buffer, 7 entries / 3 losses a day; Challenge stops at +10%%, Verification at +5%%, Funded no target.
echo  Before you continue: MT5 open and logged in, account FLAT (no positions/orders),
echo  Algo Trading OFF, hedging account. The installer asks for phase / risk type and amount /
echo  Nasdaq stop / Nasdaq DI (tested OFF) / open-risk caps, shows everything, asks you to type a
echo  confirmation, then restarts that MT5 into a new 4-chart profile with Algo Trading still OFF.
echo  It never places orders.
echo.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp02-Step\Install-P4-2Step.ps1" -Interactive -UsdJpyDIFilter OFF %*
set "CALYX_EXIT=%ERRORLEVEL%"
if /I not "%~1"=="-ValidateOnly" pause
exit /b %CALYX_EXIT%
