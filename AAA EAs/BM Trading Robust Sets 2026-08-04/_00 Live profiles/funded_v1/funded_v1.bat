@echo off
setlocal
title Calyx - funded_v1 (8 EAs, configurable funded-account guard)
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\Packages\FundedV1\Install-FundedV1.ps1" %*
set "CALYX_EXIT=%ERRORLEVEL%"
if /I not "%~1"=="-ValidateOnly" pause
exit /b %CALYX_EXIT%
