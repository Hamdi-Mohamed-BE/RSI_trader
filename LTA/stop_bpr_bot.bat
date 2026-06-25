@echo off
setlocal

set "LTA_ROOT=%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$root = $env:LTA_ROOT.TrimEnd('\'); $python = Join-Path $root '.venv\Scripts\python.exe'; Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -eq $python -and $_.CommandLine -like '*-m app.bpr_bot*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }; Remove-Item -LiteralPath (Join-Path $root 'reports\bpr_bot\bpr.lock'),(Join-Path $root 'reports\bpr_bot\bpr_heartbeat.json') -Force -ErrorAction SilentlyContinue"

echo BPR worker stopped.
pause
