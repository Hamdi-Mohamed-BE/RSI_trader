@echo off
setlocal
title Calyx - reviwed_Eas
echo Owner-selected reviewed portfolio. Passed to live trading phase is not a profitability guarantee.
echo This installs only the 25 selected EAs; normal risk and separate news risk are asked below.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0_Auto Deploy\Start-Reviewed-Portfolio.ps1" %*
set "REVIEW_EXIT=%ERRORLEVEL%"
if not "%REVIEW_EXIT%"=="0" echo Reviewed setup stopped. Check the message above.
if /I not "%~1"=="-ValidateOnly" pause
exit /b %REVIEW_EXIT%
