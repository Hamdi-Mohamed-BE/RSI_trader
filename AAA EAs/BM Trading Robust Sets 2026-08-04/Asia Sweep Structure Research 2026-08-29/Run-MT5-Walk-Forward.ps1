[CmdletBinding()]
param(
    [string]$DevelopmentFrom = '2024.08.29',
    [string]$DevelopmentTo = '2025.08.28',
    [string]$LockedFrom = '2025.08.29',
    [string]$LockedTo = '2026.08.28',
    [int]$TimeoutSeconds = 900
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$researchRoot = $PSScriptRoot
$packageRoot = Split-Path -Parent $researchRoot
$testerRoot = Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'
$terminal = Join-Path $testerRoot 'terminal64.exe'
$expertFolder = 'AAA Research\Asia Sweep Structure Shift'
$expertRoot = Join-Path (Join-Path $testerRoot 'MQL5\Experts') $expertFolder
$testerSetRoot = Join-Path $testerRoot 'MQL5\Profiles\Tester'
$configRoot = Join-Path $testerRoot 'backtest-configs\asia-sweep-20260829'
$testerReportRoot = Join-Path $testerRoot 'reports\asia-sweep-20260829'
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

$compiledSource = Join-Path $researchRoot 'EA\Asia Sweep Structure Shift EA.ex5'
if (-not (Test-Path -LiteralPath $compiledSource)) { throw "Compile the EA first: $compiledSource" }
Copy-Item -LiteralPath $compiledSource -Destination (Join-Path $expertRoot 'Asia Sweep Structure Shift EA.ex5') -Force

$symbols = @(
    [pscustomobject]@{ Symbol='EURUSD'; Slug='eurusd' },
    [pscustomobject]@{ Symbol='USDJPY'; Slug='usdjpy' },
    [pscustomobject]@{ Symbol='GBPJPY'; Slug='gbpjpy' },
    [pscustomobject]@{ Symbol='AUDCHF'; Slug='audchf' },
    [pscustomobject]@{ Symbol='GBPUSD'; Slug='gbpusd' },
    [pscustomobject]@{ Symbol='USDCHF'; Slug='usdchf' },
    [pscustomobject]@{ Symbol='USDCAD'; Slug='usdcad' },
    [pscustomobject]@{ Symbol='AUDUSD'; Slug='audusd' },
    [pscustomobject]@{ Symbol='NZDUSD'; Slug='nzdusd' }
)

$variants = @(
    [pscustomobject]@{ Id='literal-20-00-max12-rr15'; AsiaStart=20; AsiaEnd=0; EntryStart=0; EntryEnd=5; MaxBars=12; Lookback=12; Swing=1; Sweep=0.03; MidR=0.0; RR=1.5; BE=$false },
    [pscustomobject]@{ Id='fast-20-00-max6-rr15'; AsiaStart=20; AsiaEnd=0; EntryStart=0; EntryEnd=5; MaxBars=6; Lookback=10; Swing=1; Sweep=0.03; MidR=0.0; RR=1.5; BE=$false },
    [pscustomobject]@{ Id='strict-20-00-mid1-rr15'; AsiaStart=20; AsiaEnd=0; EntryStart=0; EntryEnd=5; MaxBars=12; Lookback=12; Swing=1; Sweep=0.05; MidR=1.0; RR=1.5; BE=$false },
    [pscustomobject]@{ Id='strict-20-00-mid15-rr15'; AsiaStart=20; AsiaEnd=0; EntryStart=0; EntryEnd=5; MaxBars=12; Lookback=12; Swing=1; Sweep=0.05; MidR=1.5; RR=1.5; BE=$false },
    [pscustomobject]@{ Id='early-19-00-max12-rr15'; AsiaStart=19; AsiaEnd=0; EntryStart=0; EntryEnd=5; MaxBars=12; Lookback=12; Swing=1; Sweep=0.03; MidR=0.0; RR=1.5; BE=$false },
    [pscustomobject]@{ Id='late-20-01-max12-rr15'; AsiaStart=20; AsiaEnd=1; EntryStart=1; EntryEnd=6; MaxBars=12; Lookback=12; Swing=1; Sweep=0.03; MidR=0.0; RR=1.5; BE=$false },
    [pscustomobject]@{ Id='literal-20-00-max12-rr20'; AsiaStart=20; AsiaEnd=0; EntryStart=0; EntryEnd=5; MaxBars=12; Lookback=12; Swing=1; Sweep=0.03; MidR=0.0; RR=2.0; BE=$false },
    [pscustomobject]@{ Id='literal-20-00-be1-rr15'; AsiaStart=20; AsiaEnd=0; EntryStart=0; EntryEnd=5; MaxBars=12; Lookback=12; Swing=1; Sweep=0.03; MidR=0.0; RR=1.5; BE=$true }
)

function BoolText([bool]$Value) { if ($Value) { return 'true' }; return 'false' }

function Write-SetFile([object]$Variant,[string]$Path,[long]$Magic) {
    $minimumBars = if ($Variant.AsiaStart -eq 19) { 36 } else { 30 }
    $text = @"
InpSignalTimeframe=5
InpATRPeriod=14
InpAsiaStartHourNY=$($Variant.AsiaStart)
InpAsiaEndHourNY=$($Variant.AsiaEnd)
InpEntryStartHourNY=$($Variant.EntryStart)
InpEntryEndHourNY=$($Variant.EntryEnd)
InpServerUTCOffsetHours=0
InpMinimumAsiaBars=$minimumBars
InpMinimumAsiaRangeATR=1.0
InpMaximumAsiaRangeATR=8.0
InpMinimumSweepATR=$($Variant.Sweep)
InpMaximumBarsAfterSweep=$($Variant.MaxBars)
InpStructureLookbackBars=$($Variant.Lookback)
InpSwingStrength=$($Variant.Swing)
InpBOSBufferATR=0.0
InpRequireReclaimClose=true
InpRequireDirectionalBOSCandle=true
InpMinimumMidpointR=$($Variant.MidR)
InpAllowLong=true
InpAllowShort=true
InpOneTradePerDay=true
InpRiskPercent=1.0
InpStopBufferATR=0.05
InpRewardRisk=$($Variant.RR)
InpMoveToBreakEven=$(BoolText $Variant.BE)
InpBreakEvenAtR=1.0
InpCloseAtNewYorkHour=true
InpForcedCloseHourNY=12
InpMaximumSpreadATR=0.08
InpMaximumDeviationPoints=30
InpMagic=$Magic
"@
    [IO.File]::WriteAllText($Path,$text.TrimStart(),[Text.UTF8Encoding]::new($false))
}

function Run-Case([string]$Phase,[object]$SymbolCase,[object]$Variant,[string]$From,[string]$To,[string]$Destination,[int]$Sequence) {
    $caseId = "$($SymbolCase.Slug)--$($Variant.Id)--$Phase"
    $setName = "AsiaSweep-$caseId.set"
    Write-SetFile $Variant (Join-Path $testerSetRoot $setName) (86300000 + $Sequence)
    $configPath = Join-Path $configRoot ($caseId + '.ini')
    $reportRelative = 'reports\asia-sweep-20260829\' + $caseId + '.htm'
    $reportPath = Join-Path $testerReportRoot ($caseId + '.htm')
    $config = @"
[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=$expertFolder\Asia Sweep Structure Shift EA
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

$python = (Get-Command python.exe -ErrorAction Stop).Source
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
Write-Host 'Completed development selection, untouched locked MT5 tests, statistics and equity graphs.' -ForegroundColor Green

