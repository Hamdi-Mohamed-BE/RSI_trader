@echo off
setlocal
title Calyx - Best 1-Step (no guard)
echo.
echo  BEST 1-STEP - up to 10 EAs: Nasdaq 5M (0.75x risk), USDJPY London, 3 Way Gold, EMA3, US100 Selective ORB V3,
echo  XAU RSI VWAP, ORB VP Volume Confirmed, Overnight Bias ORB, UK100 Monday dip, Asia Breakout, on the MT5 account that is
echo  open now. NO GUARD: no FTMO / prop limits, no shared daily stop, no adaptive governor. Risk is per trade per EA and
echo  stacks across open trades. The installer asks risk, Nasdaq stop, DI filters, weekend flat, no-opposite
echo  trades (ON for FundingPips: no buy and sell on one symbol at once), news guard (5 min default) and then EACH EA (Enter =
echo  install), shows everything, then restarts that MT5 once into a new profile. It never places orders.
echo  Skip EAs without questions: -SkipEAs uk100-monday-dip,3-way-gold
echo.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\Packages\Best1Step\Install-Portfolio.ps1" %*
set "CALYX_EXIT=%ERRORLEVEL%"
if /I not "%~1"=="-ValidateOnly" pause
exit /b %CALYX_EXIT%
