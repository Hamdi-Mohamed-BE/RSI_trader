$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

function Stop-ExistingWorkers {
    $processes = Get-CimInstance Win32_Process | Where-Object {
        $_.ProcessId -ne $PID -and $_.CommandLine -and (
            $_.CommandLine.Contains("naw_lta.celery_app:celery_app") -or
            ($_.CommandLine.Contains($root) -and (
                $_.CommandLine.Contains("worker.bat") -or
                $_.CommandLine.Contains("beat.bat")
            ))
        )
    }
    foreach ($process in ($processes | Sort-Object ProcessId -Descending)) {
        Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
    }
}

function Start-VisibleWorker([string]$scriptName) {
    $script = Join-Path $PSScriptRoot $scriptName
    Start-Process -FilePath $env:ComSpec -ArgumentList "/k", "call `"$script`"" -WorkingDirectory $root -WindowStyle Normal
}

Write-Host "Restarting NAW LTA workers so they use the current code..."
Stop-ExistingWorkers
Start-Sleep -Milliseconds 500
Start-VisibleWorker "worker.bat"
Start-VisibleWorker "beat.bat"
