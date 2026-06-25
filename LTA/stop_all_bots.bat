@echo off
setlocal

cd /d "%~dp0"
title LTA Stop All Bots

echo Stopping all known LTA bot workers...

set "LTA_ROOT=%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$root = $env:LTA_ROOT.TrimEnd('\');" ^
  "$patterns = @('*-m app.automation*','*-m app.orb_bot*','*-m app.challenge_20pip*','*-m app.bpr_bot*','*-m app.strategy_bot_worker*','*sniper_entry_bot.py*--loop*','*run_automation.bat*','*run_lta_bot.bat*','*run_orb_bot.bat*','*run_20pip_bot.bat*','*run_20pip_challenge.bat*','*run_bpr_bot.bat*','*run_grid_bot.bat*','*run_trend_bot.bat*','*run_mean_reversion_bot.bat*','*run_dca_bot.bat*','*run_news_bot.bat*','*run_arbitrage_bot.bat*','*run_sniper_bot.bat*');" ^
  "$stopped = @();" ^
  "Get-CimInstance Win32_Process | Where-Object { $cmd = $_.CommandLine; $_.Name -match 'python|cmd' -and (($patterns | Where-Object { $cmd -like $_ }).Count -gt 0) } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue; $stopped += $_.ProcessId };" ^
  "Remove-Item -LiteralPath (Join-Path $root 'reports\automation\automation.lock'),(Join-Path $root 'reports\automation\automation_heartbeat.json'),(Join-Path $root 'reports\orb_bot\orb.lock'),(Join-Path $root 'reports\orb_bot\orb_heartbeat.json'),(Join-Path $root 'reports\20pip_challenge\challenge.lock'),(Join-Path $root 'reports\20pip_challenge\challenge_heartbeat.json'),(Join-Path $root 'reports\bpr_bot\bpr.lock'),(Join-Path $root 'reports\bpr_bot\bpr_heartbeat.json') -Force -ErrorAction SilentlyContinue;" ^
  "$heartbeats = Get-ChildItem -LiteralPath (Join-Path $root 'reports\strategy_workers') -Filter '*_heartbeat.json' -ErrorAction SilentlyContinue; if ($heartbeats) { Remove-Item -LiteralPath $heartbeats.FullName -Force -ErrorAction SilentlyContinue };" ^
  "Write-Host ('Stopped process count: ' + $stopped.Count)"

echo.
echo Stop requests sent.
pause
