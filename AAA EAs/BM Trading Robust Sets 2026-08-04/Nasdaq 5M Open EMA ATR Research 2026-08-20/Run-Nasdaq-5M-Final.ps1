[CmdletBinding()]
param(
    [ValidateSet('FullHistory', 'RecentRealTicks')]
    [string]$Run = 'FullHistory',
    [int]$TimeoutSeconds = 3600
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$researchRoot = $PSScriptRoot
$packageRoot = Split-Path -Parent $researchRoot
$testerRoot = Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'
$terminal = Join-Path $testerRoot 'terminal64.exe'
$expertRoot = Join-Path $testerRoot 'MQL5\Experts\AAA Research\Nasdaq 5M Open EMA ATR'
$setRoot = Join-Path $testerRoot 'MQL5\Profiles\Tester'
$activeConfigRoot = 'C:\Users\hama101\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\config'
$isolatedConfigRoot = Join-Path $testerRoot 'Config'

if ($Run -eq 'FullHistory') {
    $slug = 'best-sl4-tr5-full-history'
    $fromDate = '2019.07.16'
    $toDate = '2026.08.19'
    $model = 0
    $runFolder = 'n5ema-final-full-20260820'
    $outputRoot = Join-Path $researchRoot 'Backtest Reports\Final Full History'
} else {
    $slug = 'best-sl4-tr5-recent-real-ticks'
    $fromDate = '2026.04.01'
    $toDate = '2026.08.19'
    $model = 4
    $runFolder = 'n5ema-final-real-ticks-20260820'
    $outputRoot = Join-Path $researchRoot 'Backtest Reports\Recent Real Tick Cross-Check'
}

$configRoot = Join-Path $testerRoot ('backtest-configs\' + $runFolder)
$testerReportRoot = Join-Path $testerRoot ('reports\' + $runFolder)
foreach ($path in @($expertRoot, $setRoot, $configRoot, $testerReportRoot, $outputRoot, $isolatedConfigRoot)) {
    [void](New-Item -ItemType Directory -Path $path -Force)
}
foreach ($name in @('accounts.dat', 'servers.dat', 'common.ini')) {
    Copy-Item -LiteralPath (Join-Path $activeConfigRoot $name) -Destination (Join-Path $isolatedConfigRoot $name) -Force
}
Copy-Item -LiteralPath (Join-Path $researchRoot 'EA\Nasdaq 5M Open EMA ATR EA.ex5') -Destination (Join-Path $expertRoot 'Nasdaq 5M Open EMA ATR EA.ex5') -Force

function Set-InputValue {
    param([string]$Text, [string]$Name, [object]$Value)
    $pattern = '(?m)^' + [regex]::Escape($Name) + '=[^\r\n]*$'
    if (-not [regex]::IsMatch($Text, $pattern)) { throw "Input $Name was not found." }
    return [regex]::Replace($Text, $pattern, ($Name + '=' + [string]$Value), 1)
}

$setText = Get-Content -Raw -LiteralPath (Join-Path $researchRoot 'Sets\BASE - USTEC M5 - 1pct.set')
foreach ($pair in @(
    @('InpInitialStopATR', 4.0),
    @('InpTrailingATR', 5.0),
    @('InpTrailStartR', 0.0),
    @('InpCloseAtSessionEnd', 'true'),
    @('InpAllowLong', 'true'),
    @('InpAllowShort', 'true'),
    @('InpMaximumSpreadATR', 0.0)
)) { $setText = Set-InputValue $setText $pair[0] $pair[1] }

$setName = 'BEST - USTEC M5 - 1pct - EMA12 ATR4 Trail5.set'
[IO.File]::WriteAllText((Join-Path $setRoot $setName), $setText, [Text.UTF8Encoding]::new($false))
[IO.File]::WriteAllText((Join-Path $researchRoot ('Sets\' + $setName)), $setText, [Text.UTF8Encoding]::new($false))

$configPath = Join-Path $configRoot ($slug + '.ini')
$reportPath = Join-Path $testerReportRoot ($slug + '.htm')
$relativeReport = 'reports\' + $runFolder + '\' + $slug + '.htm'
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
Model=$model
ExecutionMode=1
Optimization=0
FromDate=$fromDate
ToDate=$toDate
ForwardMode=0
Report=$relativeReport
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"@
[IO.File]::WriteAllText($configPath, $config, [Text.UTF8Encoding]::new($true))
Get-ChildItem -LiteralPath $testerReportRoot -Filter ($slug + '*') -ErrorAction SilentlyContinue | Remove-Item -Force
Write-Host ("START {0}: {1} to {2}, model {3}" -f $Run, $fromDate, $toDate, $model) -ForegroundColor Cyan
$process = Start-Process -FilePath $terminal -ArgumentList @('/portable', ('/config:"' + $configPath + '"')) -PassThru -WindowStyle Hidden
try {
    Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop
} catch {
    Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
    throw "Timed out running $Run."
}
if (-not (Test-Path -LiteralPath $reportPath)) { throw "No report was created for $Run." }
Get-ChildItem -LiteralPath $testerReportRoot -Filter ($slug + '*') | Copy-Item -Destination $outputRoot -Force
Write-Host ("DONE {0}" -f $Run) -ForegroundColor Green
