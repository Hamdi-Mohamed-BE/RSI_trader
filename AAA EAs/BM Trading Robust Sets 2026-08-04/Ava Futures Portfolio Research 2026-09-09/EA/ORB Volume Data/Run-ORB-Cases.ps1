[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$ManifestPath,
    [int]$TimeoutSeconds = 600
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$packageRoot = Split-Path -Parent $PSScriptRoot
$testerRoot = Join-Path $packageRoot '_Backtests\MT5-Isolated-20260805'
$terminal = Join-Path $testerRoot 'terminal64.exe'
$reportRoot = Join-Path $testerRoot 'reports\orb-volume-data'
$cases = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json

foreach ($case in $cases) {
    $report = Join-Path $reportRoot ($case.case + '.htm')
    Remove-Item -LiteralPath $report -Force -ErrorAction SilentlyContinue
    Write-Host ("Testing {0}" -f $case.case) -ForegroundColor Cyan
    $process = Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"' + $case.config + '"')) -PassThru -WindowStyle Hidden
    try {
        Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop
        $process.Refresh()
    } catch {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        throw "Timed out: $($case.case)"
    }
    if (-not (Test-Path -LiteralPath $report)) {
        throw "MT5 did not create $report"
    }
}

Write-Host ("Completed {0} cases" -f $cases.Count) -ForegroundColor Green
