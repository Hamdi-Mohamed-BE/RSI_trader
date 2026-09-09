Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$packageRoot = Split-Path -Parent $PSScriptRoot
$configRoot = Join-Path $packageRoot '_Backtests\MT5-Isolated-20260805\backtest-configs\orb-volume-data'
$runner = Join-Path $PSScriptRoot 'Run-ORB-Cases.ps1'
$names = @(
    'select-xau-manifest.json',
    'select-xau0820-manifest.json',
    'select-btc-manifest.json',
    'select-btc0800-manifest.json',
    'select-us30-manifest.json',
    'select-us30len-manifest.json',
    'select-ustec-manifest.json',
    'select-ustecor5-manifest.json',
    'select-ustecor10-manifest.json',
    'select-ustecor30-manifest.json',
    'select-us500-manifest.json',
    'select-us500or5-manifest.json',
    'select-us500or10-manifest.json',
    'select-us500or30-manifest.json'
)

foreach ($name in $names) {
    & $runner -ManifestPath (Join-Path $configRoot $name) -TimeoutSeconds 600
}

Write-Host 'All ORB selection cases completed.' -ForegroundColor Green
