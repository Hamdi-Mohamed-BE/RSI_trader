@echo off
setlocal
title Calyx - Best 1-Step, FTMO 1-Step guard
echo.
echo  BEST 1-STEP, FTMO 1-STEP - up to 11 guarded EAs: Nasdaq 5M, USDJPY London, 3 Way Gold, EMA3, XAU Squeeze,
echo  US100 Selective ORB V3, XAU RSI VWAP, ORB VP Volume Confirmed, Overnight Bias ORB, Gold Band Wave, UK100 Monday dip.
echo  The installer asks for EACH EA whether to install it (Enter = yes), then phase / risk / Nasdaq stop / DI filters /
echo  open-risk caps / weekend flat. Rules enforced on new entries: +10%% target, 3%% daily loss, 10%% max loss trailing
echo  the highest end-of-day balance, best day at most 50%% of total profit.
echo  Before you continue: MT5 open and logged in, account FLAT (no positions/orders), Algo Trading OFF, hedging account.
echo  It shows everything, asks you to type a confirmation, then restarts that MT5 into a new profile with Algo Trading
echo  still OFF. It never places orders. Skip EAs without questions: -SkipEAs uk100-monday-dip,3-way-gold
echo.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp01-Step\Install-Best1Step-1Step.ps1" -Interactive %*
set "CALYX_EXIT=%ERRORLEVEL%"
if /I not "%~1"=="-ValidateOnly" pause
exit /b %CALYX_EXIT%
