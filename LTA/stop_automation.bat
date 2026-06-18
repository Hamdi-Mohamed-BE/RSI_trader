@echo off
setlocal

set "LTA_ROOT=%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$root = $env:LTA_ROOT.TrimEnd('\'); $python = Join-Path $root '.venv\Scripts\python.exe'; Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -eq $python -and $_.CommandLine -like '*-m app.automation*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }; Remove-Item -LiteralPath (Join-Path $root 'reports\automation\automation.lock'),(Join-Path $root 'reports\automation\automation_heartbeat.json') -Force -ErrorAction SilentlyContinue"

echo LTA automation worker stopped.
pause
