[CmdletBinding()]
param([int]$TimeoutSeconds = 1200)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$researchRoot = $PSScriptRoot
$packageRoot = Split-Path -Parent $researchRoot
$testerRoot = Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'
$terminal = Join-Path $testerRoot 'terminal64.exe'
$expertRoot = Join-Path $testerRoot 'MQL5\Experts\AAA Research\Nasdaq 5M Open EMA ATR'
$setRoot = Join-Path $testerRoot 'MQL5\Profiles\Tester'
$configRoot = Join-Path $testerRoot 'backtest-configs\n5ema-982-safe-20260829'
$testerReportRoot = Join-Path $testerRoot 'reports\n5ema-982-safe-20260829'
$outputRoot = Join-Path $researchRoot 'Backtest Reports\982 Claim Recheck\Safe Filter'
$activeConfigRoot = 'C:\Users\hama101\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\config'
$isolatedConfigRoot = Join-Path $testerRoot 'Config'
$setName = 'FULL SAFE - USTEC M5 - 982 claim recheck - 1pct.set'

foreach ($path in @($expertRoot, $setRoot, $configRoot, $testerReportRoot, $outputRoot, $isolatedConfigRoot)) {
    [void](New-Item -ItemType Directory -Path $path -Force)
}
foreach ($name in @('accounts.dat', 'servers.dat', 'common.ini')) {
    Copy-Item -LiteralPath (Join-Path $activeConfigRoot $name) -Destination (Join-Path $isolatedConfigRoot $name) -Force
}
Copy-Item -LiteralPath (Join-Path $researchRoot 'EA\Nasdaq 5M Open EMA ATR EA.ex5') -Destination (Join-Path $expertRoot 'Nasdaq 5M Open EMA ATR EA.ex5') -Force
Copy-Item -LiteralPath (Join-Path $researchRoot ('Sets\' + $setName)) -Destination (Join-Path $setRoot $setName) -Force

$configPath = Join-Path $configRoot 'last-year-full-safe.ini'
$reportPath = Join-Path $testerReportRoot 'last-year-full-safe.htm'
$config = @"
[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=AAA Research\Nasdaq 5M Open EMA ATR\Nasdaq 5M Open EMA ATR EA
ExpertParameters=$setName
Symbol=USTEC
Period=M5
Login=472334559
Deposit=10000
Currency=USD
Leverage=1:2000
Model=0
ExecutionMode=1
Optimization=0
FromDate=2025.08.28
ToDate=2026.08.27
ForwardMode=0
Report=reports\n5ema-982-safe-20260829\last-year-full-safe.htm
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"@
[IO.File]::WriteAllText($configPath, $config, [Text.UTF8Encoding]::new($true))
Get-ChildItem -LiteralPath $testerReportRoot -Filter 'last-year-full-safe*' -ErrorAction SilentlyContinue | Remove-Item -Force

Write-Host 'START last-year Full Safe Every Tick' -ForegroundColor Cyan
$process = Start-Process -FilePath $terminal -ArgumentList @('/portable', ('/config:"' + $configPath + '"')) -PassThru -WindowStyle Hidden
try {
    Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop
}
catch {
    Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
    throw 'TIMEOUT last-year-full-safe'
}
if (-not (Test-Path -LiteralPath $reportPath)) { throw 'NO REPORT last-year-full-safe' }
Get-ChildItem -LiteralPath $testerReportRoot -Filter 'last-year-full-safe*' | Copy-Item -Destination $outputRoot -Force

& (Get-Command python.exe -ErrorAction Stop).Source (Join-Path $researchRoot 'Analyze-Nasdaq-5M-Reports.py') $outputRoot (Join-Path $researchRoot 'claim-982-safe-results')
if ($LASTEXITCODE -ne 0) { throw 'Safe report analysis failed.' }
Write-Host 'Completed the last-year Full Safe Every Tick test.' -ForegroundColor Green
