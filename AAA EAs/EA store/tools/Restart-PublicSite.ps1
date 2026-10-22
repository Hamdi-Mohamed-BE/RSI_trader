# Restarts the public Calyx website on the VPS after a git pull, so the running process loads the new code.
# Only stops the uvicorn process serving app.main:app and restarts the 'Calyx EA Store' scheduled task created by
# Configure-DnsHttps.ps1. Does not pull, does not touch Caddy, MT5 or any trading terminal.
$ErrorActionPreference = 'Stop'
$task = 'Calyx EA Store'
$store = Split-Path -Parent $PSScriptRoot
if (-not (Get-ScheduledTask -TaskName $task -ErrorAction SilentlyContinue)) {
    throw "Scheduled task '$task' not found. Run this on the VPS that serves calyx.duckdns.org (set up by Configure-DnsHttps.ps1)."
}
Write-Host ('Code on disk: ' + (& git -C $store log -1 --format='%h %s')) -ForegroundColor Cyan
Stop-ScheduledTask -TaskName $task -ErrorAction SilentlyContinue
$old = @(Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'uvicorn.+app\.main:app' })
foreach ($p in $old) { Write-Host "Stopping old site process PID $($p.ProcessId)"; Stop-Process -Id $p.ProcessId -Force }
Start-Sleep -Seconds 2
Start-ScheduledTask -TaskName $task
foreach ($path in '/api/health', '/portfolios') {
    $ok = $false
    for ($i = 0; $i -lt 30 -and -not $ok; $i++) {
        Start-Sleep -Seconds 2
        try { $ok = (Invoke-WebRequest -Uri ('http://127.0.0.1:8080' + $path) -UseBasicParsing -TimeoutSec 10).StatusCode -eq 200 } catch { }
    }
    if (-not $ok) { throw "Site did not answer 200 on $path. Check C:\Calyx-Caddy\calyx-site.log." }
    Write-Host "OK 200 $path" -ForegroundColor Green
}
Write-Host 'Public site restarted on the new code.' -ForegroundColor Green
