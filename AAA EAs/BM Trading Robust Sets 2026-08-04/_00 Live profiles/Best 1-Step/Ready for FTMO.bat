@echo off
setlocal
title READY FOR FTMO - Best 1-Step
echo.
echo  READY FOR FTMO: Best 1-Step, 10 EAs, FTMO 1-Step guard, 0.75%% risk per trade (Nasdaq 5M 0.75x),
echo  Nasdaq DI OFF, weekend/holiday flat ON, news guard +-2 min on the funded account, daily news calendar task.
echo  It asks only: Challenge or Funded (Funded also asks the risk per trade, Enter = 0.5%%), then the installer confirmation. MT5 restarts into a new profile with Algo Trading OFF.
echo  Before you continue: MT5 open and logged in on the FTMO account, account FLAT, Algo Trading OFF.
echo.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Ready-For-FTMO.ps1" %*
set "CALYX_EXIT=%ERRORLEVEL%"
if /I not "%~1"=="-ValidateOnly" pause
exit /b %CALYX_EXIT%
