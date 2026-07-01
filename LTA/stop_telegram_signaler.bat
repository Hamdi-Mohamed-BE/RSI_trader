@echo off
setlocal

cd /d "%~dp0"
title Stop Telegram Trade Signaler
set "LTA_ROOT=%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$root = $env:LTA_ROOT.TrimEnd('\'); $python = Join-Path $root '.venv\Scripts\python.exe'; Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -eq $python -and $_.CommandLine -like '*-m app.telegram_signaler*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }; Remove-Item -LiteralPath (Join-Path $root 'reports\telegram_signaler\telegram_signaler.lock'),(Join-Path $root 'reports\telegram_signaler\heartbeat.json') -Force -ErrorAction SilentlyContinue"

echo Telegram signaler stop request sent.
pause
