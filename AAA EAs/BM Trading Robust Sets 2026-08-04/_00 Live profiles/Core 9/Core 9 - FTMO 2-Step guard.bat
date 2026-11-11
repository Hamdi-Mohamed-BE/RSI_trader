@echo off
setlocal
title Calyx - Core 9, FTMO 2-Step guard
echo.
echo  CORE 9, FTMO 2-STEP - installs 8 guarded EAs (Sell Nasdaq removed) on the MT5 account that is open now.
echo  Limits enforced on new entries: 3%% daily reserve, 92%% equity buffer, 7 entries / 3 losses a day,
echo  Challenge stops at +10%%, Verification at +5%%, Funded has no target.
echo  Before you continue: MT5 open and logged in, account FLAT (no positions/orders),
echo  Algo Trading OFF, hedging account. The installer asks for phase / risk type and amount /
echo  Nasdaq stop / Nasdaq and USDJPY DI / open-risk caps, shows everything, asks you to type a
echo  confirmation, then restarts that MT5 into a new 8-chart profile with Algo Trading still OFF.
echo  It never places orders.
echo.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp02-Step\Install-Core9-2Step.ps1" -Interactive %*
set "CALYX_EXIT=%ERRORLEVEL%"
if /I not "%~1"=="-ValidateOnly" pause
exit /b %CALYX_EXIT%
