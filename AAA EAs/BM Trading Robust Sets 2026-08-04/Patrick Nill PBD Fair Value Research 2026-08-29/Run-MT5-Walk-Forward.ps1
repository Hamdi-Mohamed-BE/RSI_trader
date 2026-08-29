[CmdletBinding()]
param(
    [string]$DevelopmentFrom = '2024.08.28',
    [string]$DevelopmentTo = '2025.08.27',
    [string]$LockedFrom = '2025.08.28',
    [string]$LockedTo = '2026.08.27',
    [int]$TimeoutSeconds = 900
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$researchRoot = $PSScriptRoot
$packageRoot = Split-Path -Parent $researchRoot
$testerRoot = Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'
$terminal = Join-Path $testerRoot 'terminal64.exe'
$expertFolder = 'AAA Research\PBD Fair Value Range Proxy'
$expertRoot = Join-Path (Join-Path $testerRoot 'MQL5\Experts') $expertFolder
$testerSetRoot = Join-Path $testerRoot 'MQL5\Profiles\Tester'
$configRoot = Join-Path $testerRoot 'backtest-configs\pbd-fair-value-20260829'
$testerReportRoot = Join-Path $testerRoot 'reports\pbd-fair-value-20260829'
$outputRoot = Join-Path $researchRoot 'Backtest Reports'
$developmentOutput = Join-Path $outputRoot 'Development 2024-2025'
$lockedOutput = Join-Path $outputRoot 'Locked 2025-2026'
$activeConfigRoot = 'C:\Users\hama101\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\config'
$isolatedConfigRoot = Join-Path $testerRoot 'Config'

foreach ($path in @($expertRoot,$testerSetRoot,$configRoot,$testerReportRoot,$developmentOutput,$lockedOutput,$isolatedConfigRoot)) {
    [void](New-Item -ItemType Directory -Path $path -Force)
}

foreach ($name in @('accounts.dat','servers.dat','common.ini')) {
    Copy-Item -LiteralPath (Join-Path $activeConfigRoot $name) -Destination (Join-Path $isolatedConfigRoot $name) -Force
}

$compiledSource = Join-Path $researchRoot 'EA\PBD Fair Value Range Proxy EA.ex5'
if (-not (Test-Path -LiteralPath $compiledSource)) { throw "Compile the EA first: $compiledSource" }
Copy-Item -LiteralPath $compiledSource -Destination (Join-Path $expertRoot 'PBD Fair Value Range Proxy EA.ex5') -Force

$symbols = @(
    [pscustomobject]@{ Symbol='XAUUSD'; Slug='xauusd' },
    [pscustomobject]@{ Symbol='BTCUSD'; Slug='btcusd' },
    [pscustomobject]@{ Symbol='USTEC'; Slug='ustec' },
    [pscustomobject]@{ Symbol='EURUSD'; Slug='eurusd' }
)

$variants = @(
    [pscustomobject]@{ Id='reclaim-r12-rr3'; Mode=0; RangeBars=12; ImpulseBars=4; MinImpulse=1.25; MaxRange=2.50; RequireRetest=$true; Follow=$false; H4=$false; Session=$false; RR=3.0; Measured=$false },
    [pscustomobject]@{ Id='reclaim-r20-rr3'; Mode=0; RangeBars=20; ImpulseBars=6; MinImpulse=1.50; MaxRange=3.00; RequireRetest=$true; Follow=$false; H4=$false; Session=$false; RR=3.0; Measured=$false },
    [pscustomobject]@{ Id='break-r12-direct-rr3'; Mode=1; RangeBars=12; ImpulseBars=4; MinImpulse=1.25; MaxRange=2.50; RequireRetest=$false; Follow=$true; H4=$false; Session=$false; RR=3.0; Measured=$false },
    [pscustomobject]@{ Id='break-r20-retest-rr3'; Mode=1; RangeBars=20; ImpulseBars=6; MinImpulse=1.50; MaxRange=3.00; RequireRetest=$true; Follow=$true; H4=$false; Session=$false; RR=3.0; Measured=$false },
    [pscustomobject]@{ Id='both-r20-rr3'; Mode=2; RangeBars=20; ImpulseBars=6; MinImpulse=1.50; MaxRange=3.00; RequireRetest=$true; Follow=$false; H4=$false; Session=$false; RR=3.0; Measured=$false },
    [pscustomobject]@{ Id='both-r20-h4-rr3'; Mode=2; RangeBars=20; ImpulseBars=6; MinImpulse=1.50; MaxRange=3.00; RequireRetest=$true; Follow=$false; H4=$true; Session=$false; RR=3.0; Measured=$false },
    [pscustomobject]@{ Id='both-r20-rr4'; Mode=2; RangeBars=20; ImpulseBars=6; MinImpulse=1.50; MaxRange=3.00; RequireRetest=$true; Follow=$false; H4=$false; Session=$false; RR=4.0; Measured=$true },
    [pscustomobject]@{ Id='both-r32-day-rr3'; Mode=2; RangeBars=32; ImpulseBars=8; MinImpulse=1.50; MaxRange=3.50; RequireRetest=$true; Follow=$false; H4=$false; Session=$true; RR=3.0; Measured=$false }
)

function BoolText([bool]$Value) {
    if ($Value) { return 'true' }
    return 'false'
}

function Write-SetFile([object]$Variant,[string]$Path,[long]$Magic) {
    $text = @"
InpSignalTimeframe=15
InpATRPeriod=14
InpRangeBars=$($Variant.RangeBars)
InpImpulseBars=$($Variant.ImpulseBars)
InpMinimumImpulseATR=$($Variant.MinImpulse)
InpMinimumRangeATR=0.75
InpMaximumRangeATR=$($Variant.MaxRange)
InpMinimumAlternatingTouches=3
InpTouchToleranceFraction=0.15
InpAllowDProfile=false
InpZoneMaximumBars=192
InpSetupMode=$($Variant.Mode)
InpMinimumSweepATR=0.05
InpBreakoutBufferATR=0.05
InpRetestToleranceATR=0.20
InpMaximumRetestDepthFraction=0.35
InpConfirmationBars=3
InpRequireBreakoutRetest=$(BoolText $Variant.RequireRetest)
InpFollowImpulseOnly=$(BoolText $Variant.Follow)
InpAllowLong=true
InpAllowShort=true
InpUseH4TrendFilter=$(BoolText $Variant.H4)
InpH4EMAPeriod=50
InpUseNewYorkSession=$(BoolText $Variant.Session)
InpNewYorkStartHour=2
InpNewYorkEndHour=16
InpServerUTCOffsetHours=0
InpRiskPercent=1.0
InpStopBufferATR=0.10
InpRewardRisk=$($Variant.RR)
InpUseMeasuredImpulseTarget=$(BoolText $Variant.Measured)
InpMaximumTargetR=6.0
InpMoveToBreakEven=true
InpBreakEvenAtR=1.0
InpUseStructureTrail=true
InpTrailStartR=2.0
InpTrailBufferATR=0.10
InpMaximumHoldingHours=72
InpMaximumSpreadATR=0.12
InpMaximumDeviationPoints=50
InpMagic=$Magic
"@
    [IO.File]::WriteAllText($Path,$text.TrimStart(),[Text.UTF8Encoding]::new($false))
}

function Run-Case([string]$Phase,[object]$SymbolCase,[object]$Variant,[string]$From,[string]$To,[string]$Destination,[int]$Sequence) {
    $caseId = "$($SymbolCase.Slug)--$($Variant.Id)--$Phase"
    $setName = "PBD-$caseId.set"
    Write-SetFile $Variant (Join-Path $testerSetRoot $setName) (86292900 + $Sequence)
    $configPath = Join-Path $configRoot ($caseId + '.ini')
    $reportRelative = 'reports\pbd-fair-value-20260829\' + $caseId + '.htm'
    $reportPath = Join-Path $testerReportRoot ($caseId + '.htm')
    $config = @"
[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=$expertFolder\PBD Fair Value Range Proxy EA
ExpertParameters=$setName
Symbol=$($SymbolCase.Symbol)
Period=M15
Login=472334559
Deposit=10000
Currency=USD
Leverage=1:2000
Model=0
ExecutionMode=1
Optimization=0
FromDate=$From
ToDate=$To
ForwardMode=0
Report=$reportRelative
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"@
    [IO.File]::WriteAllText($configPath,$config,[Text.UTF8Encoding]::new($true))
    Get-ChildItem -LiteralPath $testerReportRoot -Filter ($caseId + '*') -ErrorAction SilentlyContinue | Remove-Item -Force
    Write-Host ("START {0} {1} {2} | {3} to {4}" -f $Phase,$SymbolCase.Symbol,$Variant.Id,$From,$To) -ForegroundColor Cyan
    $process = Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"' + $configPath + '"')) -PassThru -WindowStyle Hidden
    try {
        Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop
    } catch {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        throw "MT5 timed out: $caseId"
    }
    if (-not (Test-Path -LiteralPath $reportPath)) { throw "MT5 did not create report: $reportPath" }
    Get-ChildItem -LiteralPath $testerReportRoot -Filter ($caseId + '*') | Copy-Item -Destination $Destination -Force
}

$sequence = 0
foreach ($symbolCase in $symbols) {
    foreach ($variant in $variants) {
        $sequence++
        Run-Case 'development' $symbolCase $variant $DevelopmentFrom $DevelopmentTo $developmentOutput $sequence
    }
}

$python = 'C:\Users\hama101\Desktop\geek\ai trader\AAA EAs\EA store\.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { $python = (Get-Command python.exe -ErrorAction Stop).Source }
& $python (Join-Path $researchRoot 'Select-Winners.py') --reports $developmentOutput --output (Join-Path $outputRoot 'selected.json')
if ($LASTEXITCODE -ne 0) { throw 'Winner selection failed.' }
$selected = Get-Content -LiteralPath (Join-Path $outputRoot 'selected.json') -Raw | ConvertFrom-Json

foreach ($symbolCase in $symbols) {
    $winnerId = [string]$selected.$($SymbolCase.Slug).variant
    $variant = $variants | Where-Object Id -eq $winnerId | Select-Object -First 1
    if (-not $variant) { throw "No selected variant for $($symbolCase.Symbol)" }
    $sequence++
    Run-Case 'locked' $symbolCase $variant $LockedFrom $LockedTo $lockedOutput $sequence
}

& $python (Join-Path $researchRoot 'Build-Report.py') --development $developmentOutput --locked $lockedOutput --selected (Join-Path $outputRoot 'selected.json') --output $researchRoot
if ($LASTEXITCODE -ne 0) { throw 'Report build failed.' }
Write-Host 'Completed development selection, locked MT5 tests, statistics and equity graphs.' -ForegroundColor Green
