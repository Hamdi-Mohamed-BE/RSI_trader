@echo off
setlocal
title Calyx - FTMO guarded - Current 14 + ORB 0.5R - ANY BROKER TEST
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\Start-LiveProfile.ps1" -Portfolio "ftmo-any-broker" %*
set "CALYX_EXIT=%ERRORLEVEL%"
if /I not "%~1"=="-ValidateOnly" pause
exit /b %CALYX_EXIT%
