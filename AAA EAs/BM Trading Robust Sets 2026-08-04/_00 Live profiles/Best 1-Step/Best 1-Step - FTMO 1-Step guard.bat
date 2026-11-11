@echo off
setlocal
title Calyx - Best 1-Step, FTMO 1-Step guard
echo.
echo  BEST 1-STEP, FTMO 1-STEP - installs 7 guarded EAs (Nasdaq 5M, ONB, EMA3, Gold Band Wave, ORB VP VC, RSI VWAP, UK100)
echo  on the MT5 account that is open now. Rules enforced on new entries: +10%% target, 3%% daily loss,
echo  10%% max loss trailing the highest end-of-day balance, best day at most 50%% of total profit.
echo  Before you continue: MT5 open and logged in, account FLAT (no positions/orders),
echo  Algo Trading OFF, hedging account. The installer asks for phase / risk type and amount (tested 0.5%%) /
echo  Nasdaq stop / Nasdaq DI (tested OFF) / open-risk caps / weekend flat, shows everything, asks
echo  you to type a confirmation, then restarts that MT5 into a new 7-chart profile with Algo Trading still OFF.
echo  It never places orders.
echo.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp01-Step\Install-Best1Step-1Step.ps1" -Interactive -UsdJpyDIFilter OFF %*
set "CALYX_EXIT=%ERRORLEVEL%"
if /I not "%~1"=="-ValidateOnly" pause
exit /b %CALYX_EXIT%
