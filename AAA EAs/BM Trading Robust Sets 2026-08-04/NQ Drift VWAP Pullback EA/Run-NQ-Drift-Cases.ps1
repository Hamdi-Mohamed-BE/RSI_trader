[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$ManifestPath,
    [int]$TimeoutSeconds = 1200
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$packageRoot = Split-Path -Parent $PSScriptRoot
$testerRoot = Join-Path $packageRoot '_Backtests\MT5-Isolated-20260805'
$terminal = Join-Path $testerRoot 'terminal64.exe'
$cases = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json

foreach ($case in $cases) {
    Remove-Item -LiteralPath $case.report -Force -ErrorAction SilentlyContinue
    Write-Host ("Testing {0}" -f $case.case) -ForegroundColor Cyan
    $process = Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"' + $case.config + '"')) -PassThru -WindowStyle Hidden
    try {
        Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop
        $process.Refresh()
    } catch {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        throw "Timed out: $($case.case)"
    }
    if (-not (Test-Path -LiteralPath $case.report)) { throw "Missing report: $($case.report)" }
}
Write-Host ("Completed {0} cases" -f $cases.Count) -ForegroundColor Green
