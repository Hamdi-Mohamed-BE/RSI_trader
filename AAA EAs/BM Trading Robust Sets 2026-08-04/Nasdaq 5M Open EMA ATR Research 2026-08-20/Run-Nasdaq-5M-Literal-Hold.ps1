[CmdletBinding()]
param(
    [ValidateSet('All', 'LockedValidation', 'FullHistory', 'WebsiteOneYear')]
    [string]$Run = 'All',
    [int]$TimeoutSeconds = 5400
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
$outputRoot = Join-Path $researchRoot 'Backtest Reports\Literal Hold'
$configRoot = Join-Path $testerRoot 'backtest-configs\n5ema-literal-hold-20260823'
$testerReportRoot = Join-Path $testerRoot 'reports\n5ema-literal-hold-20260823'
$setName = 'LITERAL - USTEC M5 - 1pct - EMA12 ATR3 Trail4 HOLD.set'

foreach ($required in @(
    $terminal,
    (Join-Path $researchRoot 'EA\Nasdaq 5M Open EMA ATR EA.ex5'),
    (Join-Path $researchRoot ('Sets\' + $setName))
)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw "Required file is missing: $required"
    }
}

foreach ($path in @($expertRoot, $setRoot, $configRoot, $testerReportRoot, $outputRoot, $isolatedConfigRoot)) {
    [void](New-Item -ItemType Directory -Path $path -Force)
}
foreach ($name in @('accounts.dat', 'servers.dat', 'common.ini')) {
    $source = Join-Path $activeConfigRoot $name
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
        throw "Active Exness configuration is missing: $source"
    }
    Copy-Item -LiteralPath $source -Destination (Join-Path $isolatedConfigRoot $name) -Force
}
Copy-Item -LiteralPath (Join-Path $researchRoot 'EA\Nasdaq 5M Open EMA ATR EA.ex5') -Destination (Join-Path $expertRoot 'Nasdaq 5M Open EMA ATR EA.ex5') -Force
Copy-Item -LiteralPath (Join-Path $researchRoot ('Sets\' + $setName)) -Destination (Join-Path $setRoot $setName) -Force

$cases = @()
if ($Run -in @('All', 'LockedValidation')) {
    $cases += [pscustomobject]@{
        Slug = 'literal-hold-locked-2025-2026'
        FromDate = '2025.01.01'
        ToDate = '2026.08.22'
    }
}
if ($Run -in @('All', 'FullHistory')) {
    $cases += [pscustomobject]@{
        Slug = 'literal-hold-full-2019-2026'
        FromDate = '2019.07.16'
        ToDate = '2026.08.22'
    }
}
if ($Run -in @('All', 'WebsiteOneYear')) {
    $cases += [pscustomobject]@{
        Slug = 'literal-hold-website-one-year'
        FromDate = '2025.08.11'
        ToDate = '2026.08.10'
    }
}

foreach ($case in $cases) {
    $configPath = Join-Path $configRoot ($case.Slug + '.ini')
    $reportPath = Join-Path $testerReportRoot ($case.Slug + '.htm')
    $relativeReport = 'reports\n5ema-literal-hold-20260823\' + $case.Slug + '.htm'
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
FromDate=$($case.FromDate)
ToDate=$($case.ToDate)
ForwardMode=0
Report=$relativeReport
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"@
    [IO.File]::WriteAllText($configPath, $config, [Text.UTF8Encoding]::new($true))
    Get-ChildItem -LiteralPath $testerReportRoot -Filter ($case.Slug + '*') -ErrorAction SilentlyContinue | Remove-Item -Force

    Write-Host ("START {0}: {1} to {2}, synchronized Every Tick" -f $case.Slug, $case.FromDate, $case.ToDate) -ForegroundColor Cyan
    $process = Start-Process -FilePath $terminal -ArgumentList @('/portable', ('/config:"' + $configPath + '"')) -PassThru -WindowStyle Hidden
    try {
        Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop
    } catch {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        throw "Timed out running $($case.Slug)."
    }
    if (-not (Test-Path -LiteralPath $reportPath -PathType Leaf)) {
        throw "No MT5 report was created for $($case.Slug)."
    }
    Get-ChildItem -LiteralPath $testerReportRoot -Filter ($case.Slug + '*') | Copy-Item -Destination $outputRoot -Force
    Write-Host ("DONE {0}" -f $case.Slug) -ForegroundColor Green
}

$python = Get-Command python -ErrorAction Stop
& $python.Source (Join-Path $researchRoot 'Analyze-Nasdaq-5M-Reports.py') $outputRoot (Join-Path $researchRoot 'literal-hold-results')
if ($LASTEXITCODE -ne 0) {
    throw 'Report analysis failed.'
}
