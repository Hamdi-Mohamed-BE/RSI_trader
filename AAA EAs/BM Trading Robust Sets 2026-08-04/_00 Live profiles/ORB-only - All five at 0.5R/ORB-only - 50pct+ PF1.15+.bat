@echo off
setlocal
title Calyx - ORB-only - All five at 0.5R
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\Start-LiveProfile.ps1" -Portfolio "orbs-only" %*
set "CALYX_EXIT=%ERRORLEVEL%"
if /I not "%~1"=="-ValidateOnly" pause
exit /b %CALYX_EXIT%
