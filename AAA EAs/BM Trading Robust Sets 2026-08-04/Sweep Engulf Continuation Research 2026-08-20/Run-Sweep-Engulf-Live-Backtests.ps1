[CmdletBinding()]
param(
    [string]$FromDate = '2025.08.20',
    [string]$ToDate = '2026.08.19',
    [int]$TimeoutSeconds = 900,
    [int]$Model = 0
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$researchRoot = $PSScriptRoot
$packageRoot = Split-Path -Parent $researchRoot
$testerRoot = Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'
$terminal = Join-Path $testerRoot 'terminal64.exe'
$expertRoot = Join-Path $testerRoot 'MQL5\Experts\AAA Research\Sweep Engulf Continuation'
$setRoot = Join-Path $testerRoot 'MQL5\Profiles\Tester'
$configRoot = Join-Path $testerRoot 'backtest-configs\sweep-engulf-live-20260820'
$testerReportRoot = Join-Path $testerRoot 'reports\sweep-engulf-live-20260820'
$outputRoot = Join-Path $researchRoot 'Backtest Reports\MT5 Exness Live 1Y'
$activeConfigRoot = 'C:\Users\hama101\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\config'
$isolatedConfigRoot = Join-Path $testerRoot 'Config'

foreach ($path in @($expertRoot,$setRoot,$configRoot,$testerReportRoot,$outputRoot,$isolatedConfigRoot)) {
    [void](New-Item -ItemType Directory -Path $path -Force)
}

foreach ($name in @('accounts.dat','servers.dat','common.ini')) {
    Copy-Item -LiteralPath (Join-Path $activeConfigRoot $name) -Destination (Join-Path $isolatedConfigRoot $name) -Force
}

$expertSource = Join-Path $researchRoot 'EA\Sweep Engulf Continuation EA.ex5'
$expertTarget = Join-Path $expertRoot 'Sweep Engulf Continuation EA.ex5'
Copy-Item -LiteralPath $expertSource -Destination $expertTarget -Force

$baseSet = Join-Path $researchRoot 'Sets\BASE - Sweep Engulf - H1 - 0.50pct.set'
$setName = 'SEC LIVE H1 050.set'
Copy-Item -LiteralPath $baseSet -Destination (Join-Path $setRoot $setName) -Force

$cases = @(
    [pscustomobject]@{ Symbol='XAUUSD'; Slug='xauusd' },
    [pscustomobject]@{ Symbol='XAGUSD'; Slug='xagusd' },
    [pscustomobject]@{ Symbol='BTCUSD'; Slug='btcusd' },
    [pscustomobject]@{ Symbol='ETHUSD'; Slug='ethusd' },
    [pscustomobject]@{ Symbol='US30'; Slug='us30' },
    [pscustomobject]@{ Symbol='USTEC'; Slug='ustec' },
    [pscustomobject]@{ Symbol='EURUSD'; Slug='eurusd' },
    [pscustomobject]@{ Symbol='GBPUSD'; Slug='gbpusd' },
    [pscustomobject]@{ Symbol='USDJPY'; Slug='usdjpy' },
    [pscustomobject]@{ Symbol='USDCAD'; Slug='usdcad' },
    [pscustomobject]@{ Symbol='USDCHF'; Slug='usdchf' },
    [pscustomobject]@{ Symbol='AUDUSD'; Slug='audusd' },
    [pscustomobject]@{ Symbol='NZDUSD'; Slug='nzdusd' },
    [pscustomobject]@{ Symbol='GBPJPY'; Slug='gbpjpy' }
)

$manifest = New-Object System.Collections.Generic.List[object]
foreach ($case in $cases) {
    $configPath = Join-Path $configRoot ($case.Slug + '.ini')
    $reportPath = Join-Path $testerReportRoot ($case.Slug + '.htm')
    $relativeReport = 'reports\sweep-engulf-live-20260820\' + $case.Slug + '.htm'
    $config = @"
[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=AAA Research\Sweep Engulf Continuation\Sweep Engulf Continuation EA
ExpertParameters=$setName
Symbol=$($case.Symbol)
Period=H1
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
    Get-ChildItem -LiteralPath $testerReportRoot -Filter ($case.Slug + '*') -ErrorAction SilentlyContinue | Remove-Item -Force

    Write-Host ("START {0} H1 | {1} to {2} | MT5 model {3}" -f $case.Symbol,$FromDate,$ToDate,$Model) -ForegroundColor Cyan
    $process = Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"' + $configPath + '"')) -PassThru -WindowStyle Hidden
    try {
        Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop
    } catch {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        Write-Warning ("TIMEOUT {0}" -f $case.Symbol)
        $manifest.Add([pscustomobject]@{Symbol=$case.Symbol;Slug=$case.Slug;Status='timeout';Report=$null})
        continue
    }

    if (-not (Test-Path -LiteralPath $reportPath)) {
        Write-Warning ("NO REPORT {0}" -f $case.Symbol)
        $manifest.Add([pscustomobject]@{Symbol=$case.Symbol;Slug=$case.Slug;Status='no-report';Report=$null})
        continue
    }

    Get-ChildItem -LiteralPath $testerReportRoot -Filter ($case.Slug + '*') | Copy-Item -Destination $outputRoot -Force
    $manifest.Add([pscustomobject]@{Symbol=$case.Symbol;Slug=$case.Slug;Status='complete';Report=(Join-Path $outputRoot ($case.Slug + '.htm'))})
    Write-Host ("DONE  {0}" -f $case.Symbol) -ForegroundColor Green
}

$manifest | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $outputRoot 'manifest.json') -Encoding utf8
Write-Host ("Completed {0} native MT5 tests." -f (($manifest | Where-Object Status -eq 'complete').Count)) -ForegroundColor Green
