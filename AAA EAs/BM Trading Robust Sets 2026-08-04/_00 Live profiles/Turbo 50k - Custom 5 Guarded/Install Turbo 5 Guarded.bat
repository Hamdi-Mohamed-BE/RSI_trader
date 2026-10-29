@echo off
setlocal
title Calyx - Turbo 50k - Custom 5 Guarded
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\Packages\Turbo5\Install-Turbo5.ps1" %*
set "CALYX_EXIT=%ERRORLEVEL%"
if /I not "%~1"=="-ValidateOnly" pause
exit /b %CALYX_EXIT%
