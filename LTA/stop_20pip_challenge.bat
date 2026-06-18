@echo off
setlocal

set "LTA_ROOT=%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$root = $env:LTA_ROOT.TrimEnd('\'); $python = Join-Path $root '.venv\Scripts\python.exe'; Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -eq $python -and $_.CommandLine -like '*-m app.challenge_20pip*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }; Remove-Item -LiteralPath (Join-Path $root 'reports\20pip_challenge\challenge.lock'),(Join-Path $root 'reports\20pip_challenge\challenge_heartbeat.json') -Force -ErrorAction SilentlyContinue"

echo 20 Pip Challenge worker stopped.
pause
