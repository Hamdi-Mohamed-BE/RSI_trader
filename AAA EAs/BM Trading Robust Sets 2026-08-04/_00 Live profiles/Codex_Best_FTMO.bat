@echo off
setlocal
title Calyx - Codex_Best_FTMO
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-LiveProfile.ps1" -Portfolio "codex-best-ftmo" %*
set "CALYX_EXIT=%ERRORLEVEL%"
if /I not "%~1"=="-ValidateOnly" pause
exit /b %CALYX_EXIT%
