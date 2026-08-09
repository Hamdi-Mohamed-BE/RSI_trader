[CmdletBinding()]
param(
    [int]$TimeoutSeconds = 1800,
    [string]$ManifestPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$packageRoot = Split-Path -Parent $PSScriptRoot
$testerRoot = Join-Path $packageRoot '_Backtests\MT5-Isolated-20260805'
$terminal = Join-Path $testerRoot 'terminal64.exe'
if (-not $ManifestPath) {
    $ManifestPath = Join-Path $testerRoot 'backtest-configs\bat-portfolio-20260809\manifest.json'
}
$cases = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json

foreach ($case in $cases) {
    Remove-Item -LiteralPath $case.report -Force -ErrorAction SilentlyContinue
    $reportDirectory = Split-Path -Parent $case.report
    Get-ChildItem -LiteralPath $reportDirectory -Filter ($case.id + '*.png') -ErrorAction SilentlyContinue | Remove-Item -Force
    Write-Host ("Testing {0}/{1}: {2} on {3}" -f ([array]::IndexOf($cases, $case) + 1), $cases.Count, $case.label, $case.chart) -ForegroundColor Cyan
    $process = Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"' + $case.config + '"')) -PassThru -WindowStyle Hidden
    try {
        Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop
    } catch {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        throw "Timed out: $($case.label)"
    }
    if (-not (Test-Path -LiteralPath $case.report)) {
        throw "Missing report after test: $($case.report)"
    }
}
Write-Host ("Completed {0} BAT portfolio EA tests." -f $cases.Count) -ForegroundColor Green
