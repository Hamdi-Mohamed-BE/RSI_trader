param(
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$workerPattern = "asia-breakout\.exe|amd-bot\.exe|dmc-bot\.exe|ema3-live\.exe|nasdaq-weakness\.exe|news-pulse\.exe|weekend-direction\.exe|run_live\.bat|run_live_bot\.bat"

$targets = @(
    Get-CimInstance Win32_Process | Where-Object {
        $_.ProcessId -ne $PID -and
        $_.CommandLine -and
        $_.CommandLine.Contains($Root) -and
        $_.CommandLine -match $workerPattern
    }
)

if ($targets.Count -eq 0) {
    if (-not $Quiet) {
        Write-Host "No AAA Final bot workers are running." -ForegroundColor DarkYellow
    }
    exit 0
}

$ids = @($targets | Select-Object -ExpandProperty ProcessId -Unique)
$names = @($targets | Select-Object -ExpandProperty Name -Unique | Sort-Object)

# Stop only processes whose command lines belong to this AAA Final folder.
# MetaTrader 5 and its positions/orders are deliberately left untouched.
Stop-Process -Id $ids -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 500

$remaining = @(
    Get-CimInstance Win32_Process | Where-Object {
        $_.CommandLine -and
        $_.CommandLine.Contains($Root) -and
        $_.CommandLine -match $workerPattern
    }
)

if ($remaining.Count -gt 0) {
    $remainingIds = ($remaining | Select-Object -ExpandProperty ProcessId -Unique) -join ", "
    throw "Some AAA Final worker processes could not be stopped: $remainingIds"
}

if (-not $Quiet) {
    Write-Host "Stopped all AAA Final bot workers." -ForegroundColor Green
    Write-Host ("Closed worker processes: {0}" -f ($names -join ", "))
    Write-Host "MetaTrader 5 and all existing trades/orders were left untouched." -ForegroundColor Cyan
}
