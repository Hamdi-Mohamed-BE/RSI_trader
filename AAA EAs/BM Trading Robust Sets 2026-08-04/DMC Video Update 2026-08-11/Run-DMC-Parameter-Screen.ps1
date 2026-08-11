[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('XAUUSD','USTEC','US30')]
    [string]$Symbol,
    [int]$TimeoutSeconds = 600
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$packageRoot = Split-Path -Parent $PSScriptRoot
$btRoot = Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'
$terminal = Join-Path $btRoot 'terminal64.exe'
$expertRoot = Join-Path $btRoot 'MQL5\Experts'
$setRoot = Join-Path $btRoot 'MQL5\Profiles\Tester'
$configRoot = Join-Path $btRoot ('backtest-configs\dmc-video-20260811-screen-' + $Symbol.ToLowerInvariant())
$reportRoot = Join-Path $btRoot ('reports\dmc-video-20260811-screen-' + $Symbol.ToLowerInvariant())
$isolatedConfigRoot = Join-Path $btRoot 'Config'
$exnessConfigRoot = Join-Path $env:APPDATA 'MetaQuotes\Terminal\03EE49753890DF4365DAB4F329CD1335\config'

foreach ($path in @($expertRoot,$setRoot,$configRoot,$reportRoot,$isolatedConfigRoot)) {
    [void](New-Item -ItemType Directory -Path $path -Force)
}
foreach ($name in @('accounts.dat','servers.dat','common.ini')) {
    Copy-Item -LiteralPath (Join-Path $exnessConfigRoot $name) -Destination (Join-Path $isolatedConfigRoot $name) -Force
}

$expertSource = Join-Path $packageRoot 'AAA Final EAs\AAA Final DmC Video EA\AAA Final DmC Video EA.ex5'
$expertTarget = Join-Path $expertRoot 'BM Trading\AAA Final\AAA Final DmC Video EA\AAA Final DmC Video EA.ex5'
[void](New-Item -ItemType Directory -Path (Split-Path -Parent $expertTarget) -Force)
Copy-Item -LiteralPath $expertSource -Destination $expertTarget -Force
$baseline = Get-Content -Raw -LiteralPath (Join-Path $packageRoot 'AAA Final EAs\AAA Final DmC Video EA\VIDEO BASELINE - 1pct.set')

function Set-Value {
    param([string]$Text,[string]$Name,[string]$Value)
    $pattern = '(?m)^' + [regex]::Escape($Name) + '=[^\r\n]*$'
    if (-not [regex]::IsMatch($Text,$pattern)) { throw "Input $Name was not found." }
    return [regex]::Replace($Text,$pattern,($Name + '=' + $Value),1)
}

$variants = @(
    [pscustomobject]@{ Slug='v00-baseline'; Label='Baseline D/W/M, close, both'; Values=@{} },
    [pscustomobject]@{ Slug='v01-first-only'; Label='D/W/M, close, first touch only'; Values=@{ InpAllowQuickRegain='false' } },
    [pscustomobject]@{ Slug='v02-retest-first'; Label='D/W/M, retest, first touch only'; Values=@{ InpEntryMode='1'; InpAllowQuickRegain='false' } },
    [pscustomobject]@{ Slug='v03-dw-both'; Label='D/W, close, both, min 1.25R'; Values=@{ InpUseMonthlyLevels='false'; InpMinimumRR='1.25' } },
    [pscustomobject]@{ Slug='v04-dw-first'; Label='D/W, close, first only, min 1.5R'; Values=@{ InpUseMonthlyLevels='false'; InpAllowQuickRegain='false'; InpMinimumRR='1.5' } },
    [pscustomobject]@{ Slug='v05-daily-both'; Label='Daily, close, both, min 1.25R'; Values=@{ InpUseWeeklyLevels='false'; InpUseMonthlyLevels='false'; InpMinimumRR='1.25' } },
    [pscustomobject]@{ Slug='v06-retest-both'; Label='D/W/M, retest, both'; Values=@{ InpEntryMode='1' } }
)

foreach ($variant in $variants) {
    $setText = $baseline
    foreach ($key in $variant.Values.Keys) { $setText = Set-Value -Text $setText -Name $key -Value ([string]$variant.Values[$key]) }
    $setName = 'DMC SCREEN ' + $Symbol + ' ' + $variant.Slug + '.set'
    [IO.File]::WriteAllText((Join-Path $setRoot $setName),$setText,[Text.UTF8Encoding]::new($false))
    $configPath = Join-Path $configRoot ($variant.Slug + '.ini')
    $reportPath = Join-Path $reportRoot ($variant.Slug + '.htm')
    $relativeReport = 'reports\' + (Split-Path -Leaf $reportRoot) + '\' + $variant.Slug + '.htm'
    $config = @"
[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=BM Trading\AAA Final\AAA Final DmC Video EA\AAA Final DmC Video EA
ExpertParameters=$setName
Symbol=$Symbol
Period=H1
Login=472334559
Deposit=10000
Currency=USD
Leverage=1:2000
Model=1
ExecutionMode=1
Optimization=0
FromDate=2025.08.07
ToDate=2026.04.06
ForwardMode=0
Report=$relativeReport
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"@
    [IO.File]::WriteAllText($configPath,$config,[Text.UTF8Encoding]::new($true))
    Remove-Item -LiteralPath $reportPath -Force -ErrorAction SilentlyContinue
    Write-Host ("START {0} {1}" -f $Symbol,$variant.Slug) -ForegroundColor Cyan
    $process = Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"' + $configPath + '"')) -PassThru -WindowStyle Hidden
    try {
        Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop
        $process.Refresh()
    } catch {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        throw "$Symbol $($variant.Slug) exceeded $TimeoutSeconds seconds."
    }
    if (-not (Test-Path -LiteralPath $reportPath)) { throw "$Symbol $($variant.Slug) did not create a report." }
}

$variants | Select-Object Slug,Label | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $reportRoot 'manifest.json') -Encoding utf8
Write-Host ("Completed {0} development screens for {1}." -f $variants.Count,$Symbol) -ForegroundColor Green
