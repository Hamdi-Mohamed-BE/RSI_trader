@echo off
rem Fix Python for MT5 (2026-11-25): makes the Calyx installers' account check work (Python + MetaTrader5 package). Asks before every change.
set PYTHONHOME=
set PYTHONPATH=
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Fix-PythonForMT5.ps1" %*
echo.
pause
