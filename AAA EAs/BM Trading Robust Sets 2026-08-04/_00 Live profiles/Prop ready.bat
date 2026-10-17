@echo off
setlocal
title Calyx - Prop ready
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-LiveProfile.ps1" -Portfolio "prop-ready" %*
set "CALYX_EXIT=%ERRORLEVEL%"
if /I not "%~1"=="-ValidateOnly" pause
exit /b %CALYX_EXIT%
