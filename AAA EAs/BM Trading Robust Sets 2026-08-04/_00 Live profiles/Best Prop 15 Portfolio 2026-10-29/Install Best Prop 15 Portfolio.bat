@echo off
setlocal
title Calyx - Best Prop 15 Portfolio (15 EAs, 1%% risk)
echo.
echo  BEST PROP 15 PORTFOLIO - installs 15 guarded EAs on the MT5 account that is open now.
echo  Before you continue: MT5 open and logged in, account FLAT (no positions/orders),
echo  Algo Trading OFF, hedging account. The installer asks for phase / risk / Nasdaq DI,
echo  shows everything, asks you to type a confirmation, then restarts that MT5 into a
echo  new 15-chart profile with Algo Trading still OFF. It never places orders.
echo.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-BestProp15.ps1" -Interactive %*
set "CALYX_EXIT=%ERRORLEVEL%"
if /I not "%~1"=="-ValidateOnly" pause
exit /b %CALYX_EXIT%
