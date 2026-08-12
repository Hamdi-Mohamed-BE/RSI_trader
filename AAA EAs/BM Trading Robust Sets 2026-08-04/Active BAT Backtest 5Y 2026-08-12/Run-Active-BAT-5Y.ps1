[CmdletBinding()]
param([int]$TimeoutSeconds=3600)

Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$packageRoot=Split-Path -Parent $root
$testerRoot=Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'
$terminal=Join-Path $testerRoot 'terminal64.exe'
$manifestPath=Join-Path $testerRoot 'backtest-configs\active-bat-5y-20260812\manifest.json'
$outputRoot=Join-Path $root 'MT5 Reports'
$cases=Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
foreach($case in $cases){
    Remove-Item -LiteralPath $case.report -Force -ErrorAction SilentlyContinue
    Get-ChildItem -LiteralPath (Split-Path -Parent $case.report) -Filter ($case.id+'*.png') -ErrorAction SilentlyContinue | Remove-Item -Force
    Write-Host ("Testing {0}/{1}: {2} on {3}" -f ([array]::IndexOf($cases,$case)+1),$cases.Count,$case.label,$case.chart) -ForegroundColor Cyan
    $process=Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"'+$case.config+'"')) -PassThru -WindowStyle Hidden
    try{Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop}catch{Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue;throw "Timed out: $($case.label)"}
    if(-not (Test-Path -LiteralPath $case.report)){throw "Missing report after test: $($case.report)"}
    Get-ChildItem -LiteralPath (Split-Path -Parent $case.report) -Filter ($case.id+'*') | Copy-Item -Destination $outputRoot -Force
}
Write-Host ("Completed {0} five-year active-BAT tests." -f $cases.Count) -ForegroundColor Green
