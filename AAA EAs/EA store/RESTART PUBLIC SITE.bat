@echo off
setlocal
title Calyx - restart public website
echo.
echo  Run this ON THE VPS (as Administrator) after "git pull", so the website loads the new code.
echo  It restarts only the "Calyx EA Store" site task; Caddy, MT5 and trading are not touched.
echo.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\Restart-PublicSite.ps1"
set "CALYX_EXIT=%ERRORLEVEL%"
pause
exit /b %CALYX_EXIT%
