@echo off
setlocal

set "LTA_ROOT=%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$root = $env:LTA_ROOT.TrimEnd('\'); $python = Join-Path $root '.venv\Scripts\python.exe'; Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -eq $python -and $_.CommandLine -like '*sniper_entry_bot.py*--loop*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"

echo Sniper Bot worker stopped.
pause
