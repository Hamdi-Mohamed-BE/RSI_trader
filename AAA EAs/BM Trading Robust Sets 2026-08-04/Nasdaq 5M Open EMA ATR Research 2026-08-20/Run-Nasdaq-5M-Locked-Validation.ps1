[CmdletBinding()]
param(
    [int]$TimeoutSeconds = 3600,
    [string]$FromDate = '2025.01.01',
    [string]$ToDate = '2026.08.19',
    [int]$Model = 4
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$researchRoot = $PSScriptRoot
$packageRoot = Split-Path -Parent $researchRoot
$testerRoot = Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'
$terminal = Join-Path $testerRoot 'terminal64.exe'
$expertRoot = Join-Path $testerRoot 'MQL5\Experts\AAA Research\Nasdaq 5M Open EMA ATR'
$setRoot = Join-Path $testerRoot 'MQL5\Profiles\Tester'
$configRoot = Join-Path $testerRoot 'backtest-configs\n5ema-validation-20260820'
$testerReportRoot = Join-Path $testerRoot 'reports\n5ema-validation-20260820'
$outputRoot = Join-Path $researchRoot 'Backtest Reports\Locked Validation'
$activeConfigRoot = 'C:\Users\hama101\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\config'
$isolatedConfigRoot = Join-Path $testerRoot 'Config'
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

$cases = @(
    [pscustomobject]@{ Slug = 'eod-sl3-tr5'; InitialStopATR = 3.0; TrailingATR = 5.0 },
    [pscustomobject]@{ Slug = 'eod-sl4-tr5'; InitialStopATR = 4.0; TrailingATR = 5.0 },
    [pscustomobject]@{ Slug = 'eod-sl4-tr4'; InitialStopATR = 4.0; TrailingATR = 4.0 },
    [pscustomobject]@{ Slug = 'eod-sl3-tr4'; InitialStopATR = 3.0; TrailingATR = 4.0 }
)
$modelLabel = if ($Model -eq 4) { 'real ticks' } elseif ($Model -eq 0) { 'generated every tick' } else { "model $Model" }

$baseSet = Get-Content -Raw -LiteralPath (Join-Path $researchRoot 'Sets\BASE - USTEC M5 - 1pct.set')
$manifest = New-Object System.Collections.Generic.List[object]
foreach ($case in $cases) {
    $setText = $baseSet
    foreach ($pair in @(
        @('InpInitialStopATR', $case.InitialStopATR),
        @('InpTrailingATR', $case.TrailingATR),
        @('InpTrailStartR', 0.0),
        @('InpCloseAtSessionEnd', 'true'),
        @('InpAllowLong', 'true'),
        @('InpAllowShort', 'true'),
        @('InpMaximumSpreadATR', 0.0)
    )) { $setText = Set-InputValue $setText $pair[0] $pair[1] }

    $setName = 'N5EMA VALIDATION ' + $case.Slug + '.set'
    [IO.File]::WriteAllText((Join-Path $setRoot $setName), $setText, [Text.UTF8Encoding]::new($false))
    [IO.File]::WriteAllText((Join-Path $outputRoot $setName), $setText, [Text.UTF8Encoding]::new($false))

    $configPath = Join-Path $configRoot ($case.Slug + '.ini')
    $reportPath = Join-Path $testerReportRoot ($case.Slug + '.htm')
    $relativeReport = 'reports\n5ema-validation-20260820\' + $case.Slug + '.htm'
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
Model=$Model
ExecutionMode=1
Optimization=0
FromDate=$FromDate
ToDate=$ToDate
ForwardMode=0
Report=$relativeReport
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"@
    [IO.File]::WriteAllText($configPath, $config, [Text.UTF8Encoding]::new($true))
    Get-ChildItem -LiteralPath $testerReportRoot -Filter ($case.Slug + '*') -ErrorAction SilentlyContinue | Remove-Item -Force
    Write-Host ("START {0} ({1})" -f $case.Slug, $modelLabel) -ForegroundColor Cyan
    $process = Start-Process -FilePath $terminal -ArgumentList @('/portable', ('/config:"' + $configPath + '"')) -PassThru -WindowStyle Hidden
    try {
        Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop
    } catch {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        Write-Warning ("TIMEOUT {0}" -f $case.Slug)
        $manifest.Add([pscustomobject]@{ Case = $case; Status = 'timeout'; Report = $null })
        continue
    }
    if (-not (Test-Path -LiteralPath $reportPath)) {
        Write-Warning ("NO REPORT {0}" -f $case.Slug)
        $manifest.Add([pscustomobject]@{ Case = $case; Status = 'no-report'; Report = $null })
        continue
    }
    Get-ChildItem -LiteralPath $testerReportRoot -Filter ($case.Slug + '*') | Copy-Item -Destination $outputRoot -Force
    $manifest.Add([pscustomobject]@{ Case = $case; Status = 'complete'; Report = (Join-Path $outputRoot ($case.Slug + '.htm')) })
    Write-Host ("DONE  {0}" -f $case.Slug) -ForegroundColor Green
}
$manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $outputRoot 'manifest.json') -Encoding utf8
Write-Host ("Completed {0} locked {1} validations." -f (($manifest | Where-Object Status -eq 'complete').Count), $modelLabel) -ForegroundColor Green
