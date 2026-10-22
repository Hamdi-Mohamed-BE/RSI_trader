@echo off
setlocal
title Calyx - Create a new MT5 instance
echo.
echo  CREATE MT5 INSTANCE - makes a new, empty MetaTrader 5 copy in its own folder
echo  (C:\MT5 Instances\^<name^>) with a desktop shortcut, then starts it so you can log in.
echo  It copies program files only: no accounts, passwords, EAs or history. It does not
echo  touch any running MT5, AutoTrading or profile. Apply a Calyx profile BAT afterwards.
echo.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Create-MT5Instance.ps1" %*
set "CALYX_EXIT=%ERRORLEVEL%"
if /I not "%~1"=="-ValidateOnly" pause
exit /b %CALYX_EXIT%
