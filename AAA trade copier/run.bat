@echo off
setlocal EnableExtensions
cd /d "%~dp0"

rem Bind the web dashboard to every network interface for VPS access.
set "WEB_HOST=0.0.0.0"
set "DEMO_MODE=false"
set "AUTO_DETECT_MT5=true"
set "AAA_DATABASE_PATH=%CD:\=/%/storage/trade_copier.db"
set "DATABASE_URL=sqlite:///%AAA_DATABASE_PATH%"

if not exist ".env" (
  echo First run detected. Preparing AAA Trade Copier...
  call dev.bat setup || exit /b 1
)

if not exist ".venv\Scripts\aaa-trade-copier-web.exe" (
  echo Python environment is incomplete. Preparing AAA Trade Copier...
  call dev.bat setup || exit /b 1
)

echo Synchronizing application dependencies...
uv sync --extra dev --extra windows || exit /b 1

if not exist "src\trade_copier\static\css\app.css" (
  echo Compiled CSS is missing. Rebuilding the interface...
  where npm.cmd >nul 2>nul
  if errorlevel 1 (
    echo [ERROR] CSS is missing and Node.js is not installed. Pull the committed CSS file or install Node.js.
    exit /b 1
  )
  call npm.cmd install || exit /b 1
  call npm.cmd run build || exit /b 1
)

echo Stopping any older AAA Trade Copier processes from this folder...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$projectRoot = [System.IO.Path]::GetFullPath('%CD%');" ^
  "$webExe = [System.IO.Path]::GetFullPath((Join-Path $projectRoot '.venv\Scripts\aaa-trade-copier-web.exe'));" ^
  "$coreExe = [System.IO.Path]::GetFullPath((Join-Path $projectRoot '.venv\Scripts\aaa-trade-copier-core.exe'));" ^
  "$processes = @(Get-CimInstance Win32_Process);" ^
  "$escapedRoot = [Regex]::Escape($projectRoot);" ^
  "$roots = @($processes | Where-Object { ($_.ExecutablePath -and (([System.IO.Path]::GetFullPath($_.ExecutablePath) -eq $webExe) -or ([System.IO.Path]::GetFullPath($_.ExecutablePath) -eq $coreExe))) -or ($_.Name -eq 'cmd.exe' -and $_.CommandLine -match $escapedRoot -and $_.CommandLine -match 'dev\.bat.* (web|core)') });" ^
  "$ids = [System.Collections.Generic.HashSet[int]]::new();" ^
  "$queue = [System.Collections.Generic.Queue[int]]::new();" ^
  "foreach ($process in $roots) { [void]$ids.Add([int]$process.ProcessId); $queue.Enqueue([int]$process.ProcessId) };" ^
  "while ($queue.Count -gt 0) { $parentId = $queue.Dequeue(); foreach ($child in @($processes | Where-Object { $_.ParentProcessId -eq $parentId })) { if ($ids.Add([int]$child.ProcessId)) { $queue.Enqueue([int]$child.ProcessId) } } };" ^
  "foreach ($processId in @($ids)) { Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue }" || exit /b 1

echo Ensuring the default dashboard user is ready...
uv run aaa-trade-copier ensure-admin || exit /b 1

echo Starting AAA Trade Copier...
call dev.bat start || exit /b 1

timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:8100"
echo Local dashboard:  http://127.0.0.1:8100
echo Remote dashboard: http://YOUR-VPS-IP:8100
echo [SECURITY] Port 8100 is network-accessible. Change the default password and use a firewall or HTTPS reverse proxy.
exit /b 0
