@echo off
setlocal
title Calyx News Guard - update the news calendar
echo.
echo  Downloads this week's economic calendar (ForexFactory public feed) into
echo  %%APPDATA%%\MetaQuotes\Terminal\Common\Files\CalyxNewsCalendar.csv for the Calyx News Guard chart.
echo  Run it once a day (or schedule it with Windows Task Scheduler). It never touches MT5 or any account.
echo.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Update-NewsCalendar.ps1" %*
set "CALYX_EXIT=%ERRORLEVEL%"
if /I not "%~1"=="-Quiet" pause
exit /b %CALYX_EXIT%
