[CmdletBinding()]
param(
    [int]$TimeoutSeconds = 1800,
    [string]$FromDate = '2023.08.10',
    [string]$ToDate = '2026.08.10',
    [int]$Model = 4
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$researchRoot = $PSScriptRoot
$packageRoot = Split-Path -Parent $researchRoot
$testerRoot = Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'
$terminal = Join-Path $testerRoot 'terminal64.exe'
$expertTargetRoot = Join-Path $testerRoot 'MQL5\Experts\Online Research 2026-08-11'
$setTargetRoot = Join-Path $testerRoot 'MQL5\Profiles\Tester'
$configRoot = Join-Path $testerRoot 'backtest-configs\online-research-20260811'
$reportTargetRoot = Join-Path $testerRoot 'reports\online-research-20260811'
$reportOutputRoot = Join-Path $researchRoot 'Backtest Reports\Baseline'

foreach ($path in @($expertTargetRoot,$setTargetRoot,$configRoot,$reportTargetRoot,$reportOutputRoot)) {
    [void](New-Item -ItemType Directory -Path $path -Force)
}

Copy-Item -LiteralPath (Join-Path $researchRoot 'Source\Research_Common.mqh') -Destination $expertTargetRoot -Force
Get-ChildItem -LiteralPath (Join-Path $researchRoot 'Source') -Filter '*.ex5' | Copy-Item -Destination $expertTargetRoot -Force
Get-ChildItem -LiteralPath (Join-Path $researchRoot 'Sets') -Filter '*.set' | Copy-Item -Destination $setTargetRoot -Force

$cases = @(
    [pscustomobject]@{ Slug='xau-pullback'; Label='XAU Pullback'; Expert='Research XAU Pullback Window EA'; Set='BASELINE - XAU Pullback M5 - 1pct.set'; Symbol='XAUUSD'; Period='M5' },
    [pscustomobject]@{ Slug='keltner-eurusd'; Label='Keltner EURUSD'; Expert='Research FX Keltner Breakout EA'; Set='BASELINE - FX Keltner D1 - 1pct.set'; Symbol='EURUSD'; Period='D1' },
    [pscustomobject]@{ Slug='keltner-gbpusd'; Label='Keltner GBPUSD'; Expert='Research FX Keltner Breakout EA'; Set='BASELINE - FX Keltner D1 - 1pct.set'; Symbol='GBPUSD'; Period='D1' },
    [pscustomobject]@{ Slug='keltner-usdcad'; Label='Keltner USDCAD'; Expert='Research FX Keltner Breakout EA'; Set='BASELINE - FX Keltner D1 - 1pct.set'; Symbol='USDCAD'; Period='D1' },
    [pscustomobject]@{ Slug='keltner-nzdusd'; Label='Keltner NZDUSD'; Expert='Research FX Keltner Breakout EA'; Set='BASELINE - FX Keltner D1 - 1pct.set'; Symbol='NZDUSD'; Period='D1' },
    [pscustomobject]@{ Slug='ustec-alt22'; Label='USTEC Alt22'; Expert='Research Donchian Index EA'; Set='BASELINE - USTEC Alt22 D1 - 1pct per unit.set'; Symbol='USTEC'; Period='D1' },
    [pscustomobject]@{ Slug='us500-alt31'; Label='US500 Alt31'; Expert='Research Donchian Index EA'; Set='BASELINE - US500 Alt31 D1 - fractional.set'; Symbol='US500'; Period='D1' },
    [pscustomobject]@{ Slug='btc-four-sma'; Label='BTC Four SMA'; Expert='Research BTC Four SMA EA'; Set='BASELINE - BTC Four SMA M5 - 1pct.set'; Symbol='BTCUSD'; Period='M5' },
    [pscustomobject]@{ Slug='us30-supply-demand'; Label='US30 Supply Demand'; Expert='Research US30 Supply Demand ATR EA'; Set='BASELINE - US30 Supply Demand H1 - 1pct.set'; Symbol='US30'; Period='H1' }
)

foreach ($case in $cases) {
    $configPath = Join-Path $configRoot ($case.Slug + '.ini')
    $relativeReport = 'reports\online-research-20260811\' + $case.Slug + '.htm'
    $testerReport = Join-Path $reportTargetRoot ($case.Slug + '.htm')
    $config = @"
[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=Online Research 2026-08-11\$($case.Expert)
ExpertParameters=$($case.Set)
Symbol=$($case.Symbol)
Period=$($case.Period)
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
    [IO.File]::WriteAllText($configPath,$config,[Text.UTF8Encoding]::new($true))
    Remove-Item -LiteralPath $testerReport -Force -ErrorAction SilentlyContinue
    Write-Host ("START {0}" -f $case.Label) -ForegroundColor Cyan
    $process = Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"' + $configPath + '"')) -PassThru -WindowStyle Hidden
    try {
        Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop
    } catch {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        throw "$($case.Label) exceeded $TimeoutSeconds seconds."
    }
    if (-not (Test-Path -LiteralPath $testerReport)) { throw "$($case.Label) did not create a report." }
    Copy-Item -LiteralPath $testerReport -Destination (Join-Path $reportOutputRoot ($case.Slug + '.htm')) -Force
    $chartSource = [IO.Path]::ChangeExtension($testerReport,'.png')
    if (Test-Path -LiteralPath $chartSource) {
        Copy-Item -LiteralPath $chartSource -Destination (Join-Path $reportOutputRoot ($case.Slug + '.png')) -Force
    }
    Write-Host ("DONE  {0}" -f $case.Label) -ForegroundColor Green
}

$cases | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath (Join-Path $reportOutputRoot 'manifest.json') -Encoding utf8
Write-Host "All research baselines completed." -ForegroundColor Green
