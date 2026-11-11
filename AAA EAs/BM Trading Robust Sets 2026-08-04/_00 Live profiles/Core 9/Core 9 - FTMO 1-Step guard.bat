@echo off
setlocal
title Calyx - Core 9, FTMO 1-Step guard
echo.
echo  CORE 9, FTMO 1-STEP - installs 8 guarded EAs (Sell Nasdaq removed) on the MT5 account that is open now.
echo  Rules enforced on new entries: +10%% target, 3%% daily loss, 10%% max loss trailing the
echo  highest end-of-day balance, best day at most 50%% of total profit.
echo  Before you continue: MT5 open and logged in, account FLAT (no positions/orders),
echo  Algo Trading OFF, hedging account. The installer asks for phase / risk type and amount /
echo  Nasdaq stop / Nasdaq and USDJPY DI / open-risk caps, shows everything, asks you to type a
echo  confirmation, then restarts that MT5 into a new 8-chart profile with Algo Trading still OFF.
echo  It never places orders.
echo.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp01-Step\Install-Core9-1Step.ps1" -Interactive %*
set "CALYX_EXIT=%ERRORLEVEL%"
if /I not "%~1"=="-ValidateOnly" pause
exit /b %CALYX_EXIT%
