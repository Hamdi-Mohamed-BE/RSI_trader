[CmdletBinding()]
param(
    [string]$DevelopmentFrom = '2024.08.29',
    [string]$DevelopmentTo = '2025.08.28',
    [string]$LockedFrom = '2025.08.29',
    [string]$LockedTo = '2026.08.28',
    [int]$TimeoutSeconds = 1200
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$researchRoot = $PSScriptRoot
$packageRoot = Split-Path -Parent $researchRoot
$testerRoot = Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'
$terminal = Join-Path $testerRoot 'terminal64.exe'
$expertFolder = 'AAA Research\LCE Volume Profile Proxy'
$expertRoot = Join-Path (Join-Path $testerRoot 'MQL5\Experts') $expertFolder
$testerSetRoot = Join-Path $testerRoot 'MQL5\Profiles\Tester'
$configRoot = Join-Path $testerRoot 'backtest-configs\lce-vp-20260830'
$testerReportRoot = Join-Path $testerRoot 'reports\lce-vp-20260830'
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
$compiledSource = Join-Path $researchRoot 'EA\LCE Volume Profile Level Breakout EA.ex5'
if (-not (Test-Path -LiteralPath $compiledSource)) { throw "Compile the EA first: $compiledSource" }
Copy-Item -LiteralPath $compiledSource -Destination (Join-Path $expertRoot 'LCE Volume Profile Level Breakout EA.ex5') -Force

$symbols = @(
    [pscustomobject]@{ Symbol='US500'; Slug='us500' },
    [pscustomobject]@{ Symbol='USTEC'; Slug='ustec' },
    [pscustomobject]@{ Symbol='XAUUSD'; Slug='xauusd' },
    [pscustomobject]@{ Symbol='BTCUSD'; Slug='btcusd' }
)
$variants = @(
    [pscustomobject]@{ Id='literal-20d-neutral-rth'; Days=20; Rows=160; Spacing=0.75; Zone=0.15; Penetration=0.50; Cloud=0; End=16; MinR=0.75 },
    [pscustomobject]@{ Id='early-20d-neutral'; Days=20; Rows=160; Spacing=0.75; Zone=0.15; Penetration=0.50; Cloud=0; End=12; MinR=0.75 },
    [pscustomobject]@{ Id='early-20d-score1'; Days=20; Rows=160; Spacing=0.75; Zone=0.15; Penetration=0.50; Cloud=1; End=12; MinR=0.75 },
    [pscustomobject]@{ Id='early-20d-score2'; Days=20; Rows=160; Spacing=0.75; Zone=0.15; Penetration=0.50; Cloud=2; End=12; MinR=0.75 },
    [pscustomobject]@{ Id='deep-20d-score1'; Days=20; Rows=160; Spacing=0.75; Zone=0.15; Penetration=0.75; Cloud=1; End=12; MinR=0.75 },
    [pscustomobject]@{ Id='robust-40d-score1'; Days=40; Rows=200; Spacing=1.00; Zone=0.15; Penetration=0.50; Cloud=1; End=12; MinR=0.75 },
    [pscustomobject]@{ Id='quick-10d-score1'; Days=10; Rows=120; Spacing=0.60; Zone=0.15; Penetration=0.50; Cloud=1; End=12; MinR=0.75 },
    [pscustomobject]@{ Id='quality-20d-score1-r125'; Days=20; Rows=160; Spacing=0.75; Zone=0.15; Penetration=0.50; Cloud=1; End=12; MinR=1.25 }
)

function Write-SetFile([object]$Variant,[string]$Path,[long]$Magic) {
    $text = @"
InpExecutionTimeframe=5
InpServerUTCOffsetHours=0
InpEntryStartHourNY=9
InpEntryStartMinuteNY=30
InpEntryEndHourNY=$($Variant.End)
InpForcedCloseHourNY=16
InpMaximumTradesPerDay=2
InpStopAfterFirstWinner=true
InpProfileLookbackDays=$($Variant.Days)
InpProfileTimeframe=15
InpProfileRows=$($Variant.Rows)
InpMinimumNodeVolumeFactor=1.0
InpMinimumNodeSpacingH1ATR=$($Variant.Spacing)
InpZoneHalfWidthSpacingFraction=$($Variant.Zone)
InpLevelPenetration=$($Variant.Penetration)
InpMaximumProfileNodes=24
InpFastEMAPeriod=20
InpSlowEMAPeriod=50
InpATRPeriod=14
InpCloudFlatATR=0.05
InpMinimumCloudScore=$($Variant.Cloud)
InpUseH1Cloud=true
InpUseM30Cloud=true
InpUseM15Cloud=true
InpUseM5Cloud=true
InpStructureLookbackBars=6
InpStopBufferATR=0.10
InpMinimumTargetR=$($Variant.MinR)
InpRiskPercent=1.0
InpMoveToBreakEven=true
InpBreakEvenTargetFraction=0.50
InpMaximumSpreadATR=0.10
InpMaximumDeviationPoints=50
InpAllowLong=true
InpAllowShort=true
InpMagic=$Magic
"@
    [IO.File]::WriteAllText($Path,$text.TrimStart(),[Text.UTF8Encoding]::new($false))
}

function Run-Case([string]$Phase,[object]$SymbolCase,[object]$Variant,[string]$From,[string]$To,[string]$Destination,[int]$Sequence) {
    $caseId = "$($SymbolCase.Slug)--$($Variant.Id)--$Phase"
    $setName = "LCE-$caseId.set"
    Write-SetFile $Variant (Join-Path $testerSetRoot $setName) (86320000 + $Sequence)
    $configPath = Join-Path $configRoot ($caseId + '.ini')
    $reportRelative = 'reports\lce-vp-20260830\' + $caseId + '.htm'
    $reportPath = Join-Path $testerReportRoot ($caseId + '.htm')
    $config = @"
[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=$expertFolder\LCE Volume Profile Level Breakout EA
ExpertParameters=$setName
Symbol=$($SymbolCase.Symbol)
Period=M5
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
    try { Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop }
    catch { Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue; throw "MT5 timed out: $caseId" }
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
$python = (Get-Command python.exe -ErrorAction Stop).Source
& $python (Join-Path $researchRoot 'Select-Winners.py') --reports $developmentOutput --output (Join-Path $outputRoot 'selected.json')
if ($LASTEXITCODE -ne 0) { throw 'Winner selection failed.' }
$selected = Get-Content -LiteralPath (Join-Path $outputRoot 'selected.json') -Raw | ConvertFrom-Json
foreach ($symbolCase in $symbols) {
    $winnerId = [string]$selected.$($SymbolCase.Slug).variant
    $variant = $variants | Where-Object Id -eq $winnerId | Select-Object -First 1
    if (-not $variant) { throw "No selected variant for $($SymbolCase.Symbol)" }
    $sequence++
    Run-Case 'locked' $symbolCase $variant $LockedFrom $LockedTo $lockedOutput $sequence
}
& $python (Join-Path $researchRoot 'Build-Report.py') --development $developmentOutput --locked $lockedOutput --selected (Join-Path $outputRoot 'selected.json') --output $researchRoot
if ($LASTEXITCODE -ne 0) { throw 'Report build failed.' }
Write-Host 'Completed LCE proxy development selection, locked MT5 tests, reports and charts.' -ForegroundColor Green

