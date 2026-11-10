@echo off
setlocal
title Calyx - P4, FTMO 1-Step guard
echo.
echo  P4, FTMO 1-STEP - installs 4 guarded EAs (Overnight Bias ORB, Nasdaq 5M, EMA3, Gold Band Wave)
echo  on the MT5 account that is open now. Rules enforced on new entries: +10%% target, 3%% daily loss,
echo  10%% max loss trailing the highest end-of-day balance, best day at most 50%% of total profit.
echo  Before you continue: MT5 open and logged in, account FLAT (no positions/orders),
echo  Algo Trading OFF, hedging account. The installer asks for phase / risk type and amount /
echo  Nasdaq stop / Nasdaq DI (tested OFF) / open-risk caps, shows everything, asks you to type a
echo  confirmation, then restarts that MT5 into a new 4-chart profile with Algo Trading still OFF.
echo  It never places orders.
echo.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp01-Step\Install-P4-1Step.ps1" -Interactive -UsdJpyDIFilter OFF %*
set "CALYX_EXIT=%ERRORLEVEL%"
if /I not "%~1"=="-ValidateOnly" pause
exit /b %CALYX_EXIT%
