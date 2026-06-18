@echo off
setlocal

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -eq 'C:\Users\hama101\Desktop\geek\LTA\.venv\Scripts\python.exe' -and $_.CommandLine -like '*-m app.automation*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }; Remove-Item -LiteralPath 'C:\Users\hama101\Desktop\geek\LTA\reports\automation\automation.lock','C:\Users\hama101\Desktop\geek\LTA\reports\automation\automation_heartbeat.json' -Force -ErrorAction SilentlyContinue"

echo LTA automation worker stopped.
pause
