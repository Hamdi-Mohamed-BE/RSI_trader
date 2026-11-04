@echo off
setlocal
title Calyx - ftmo 1_step (17 EAs, FTMO 1-Step guard)
echo.
echo  FTMO 1-STEP - installs 17 guarded EAs on the MT5 account that is open now.
echo  Rules enforced on new entries: +10%% target, 3%% daily loss, 10%% max loss trailing the
echo  highest end-of-day balance, best day at most 50%% of total profit.
echo  Before you continue: MT5 open and logged in, account FLAT (no positions/orders),
echo  Algo Trading OFF, hedging account. The installer asks for phase / risk / DI / Nasdaq
echo  stop / open-risk caps, shows everything, asks you to type a confirmation, then restarts
echo  that MT5 into a new 17-chart profile with Algo Trading still OFF. It never places orders.
echo.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-FTMO1Step.ps1" -Interactive %*
set "CALYX_EXIT=%ERRORLEVEL%"
if /I not "%~1"=="-ValidateOnly" pause
exit /b %CALYX_EXIT%
