@echo off
setlocal
title Calyx - Prop ready - Core 4 + five ORBs 0.5R
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\Start-LiveProfile.ps1" -Portfolio "prop-ready" %*
set "CALYX_EXIT=%ERRORLEVEL%"
if /I not "%~1"=="-ValidateOnly" pause
exit /b %CALYX_EXIT%
