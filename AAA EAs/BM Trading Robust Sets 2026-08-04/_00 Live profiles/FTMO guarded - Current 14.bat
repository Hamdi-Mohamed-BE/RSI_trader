@echo off
setlocal
title Calyx - FTMO guarded - Current 14
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-LiveProfile.ps1" -Portfolio "ftmo" %*
set "CALYX_EXIT=%ERRORLEVEL%"
if /I not "%~1"=="-ValidateOnly" pause
exit /b %CALYX_EXIT%
