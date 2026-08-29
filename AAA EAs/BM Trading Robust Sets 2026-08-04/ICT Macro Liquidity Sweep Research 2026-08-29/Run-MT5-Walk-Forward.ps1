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
$expertFolder = 'AAA Research\ICT Macro Liquidity Sweep'
$expertRoot = Join-Path (Join-Path $testerRoot 'MQL5\Experts') $expertFolder
$testerSetRoot = Join-Path $testerRoot 'MQL5\Profiles\Tester'
$configRoot = Join-Path $testerRoot 'backtest-configs\ict-macro-20260829'
$testerReportRoot = Join-Path $testerRoot 'reports\ict-macro-20260829'
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

$compiledSource = Join-Path $researchRoot 'EA\ICT Macro Liquidity Sweep EA.ex5'
if (-not (Test-Path -LiteralPath $compiledSource)) { throw "Compile the EA first: $compiledSource" }
Copy-Item -LiteralPath $compiledSource -Destination (Join-Path $expertRoot 'ICT Macro Liquidity Sweep EA.ex5') -Force

$symbols = @(
    [pscustomobject]@{ Symbol='XAUUSD'; Slug='xauusd' },
    [pscustomobject]@{ Symbol='USTEC'; Slug='ustec' },
    [pscustomobject]@{ Symbol='BTCUSD'; Slug='btcusd' }
)

$variants = @(
    [pscustomobject]@{ Id='h0850-l60-either'; Hour=8; Lookback=60; Confirm=2; Displacement=0.35; MinRR=1.00; BreakEven=$true },
    [pscustomobject]@{ Id='h0950-l30-either'; Hour=9; Lookback=30; Confirm=2; Displacement=0.35; MinRR=1.00; BreakEven=$true },
    [pscustomobject]@{ Id='h0950-l60-either'; Hour=9; Lookback=60; Confirm=2; Displacement=0.35; MinRR=1.00; BreakEven=$true },
    [pscustomobject]@{ Id='h0950-l90-ob'; Hour=9; Lookback=90; Confirm=1; Displacement=0.50; MinRR=1.25; BreakEven=$true },
    [pscustomobject]@{ Id='h0950-l120-fvg'; Hour=9; Lookback=120; Confirm=0; Displacement=0.50; MinRR=1.25; BreakEven=$false },
    [pscustomobject]@{ Id='h1050-l60-either'; Hour=10; Lookback=60; Confirm=2; Displacement=0.35; MinRR=1.00; BreakEven=$true },
    [pscustomobject]@{ Id='h1150-l60-either'; Hour=11; Lookback=60; Confirm=2; Displacement=0.35; MinRR=1.00; BreakEven=$true }
)

function Write-SetFile([object]$Variant,[string]$Path,[long]$Magic) {
    $breakEven = if ($Variant.BreakEven) { 'true' } else { 'false' }
    $text = @"
InpMacroHourNY=$($Variant.Hour)
InpMacroStartMinute=50
InpMacroEndMinute=10
InpServerUTCOffsetHours=0
InpTradeMonday=true
InpTradeTuesday=true
InpTradeWednesday=true
InpTradeThursday=true
InpTradeFriday=true
InpLiquidityLookbackBars=$($Variant.Lookback)
InpATRPeriod=14
InpMinimumRangeATR=1.5
InpMaximumRangeATR=8.0
InpMinimumSweepATR=0.05
InpMaximumSweepATR=2.5
InpConfirmationMode=$($Variant.Confirm)
InpOrderBlockLookbackBars=8
InpMinimumDisplacementATR=$($Variant.Displacement)
InpRequireCloseBackInside=true
InpAllowLong=true
InpAllowShort=true
InpRiskPercent=1.0
InpStopBufferATR=0.1
InpMinimumRewardRisk=$($Variant.MinRR)
InpMaximumRewardRisk=5.0
InpMaximumSpreadATR=0.12
InpMaximumHoldingMinutes=180
InpMoveToBreakEven=$breakEven
InpBreakEvenAtR=1.0
InpMaximumDeviationPoints=50
InpMagic=$Magic
"@
    [IO.File]::WriteAllText($Path,$text.TrimStart(),[Text.UTF8Encoding]::new($false))
}

function Run-Case([string]$Phase,[object]$SymbolCase,[object]$Variant,[string]$From,[string]$To,[string]$Destination,[int]$Sequence) {
    $caseId = "$($SymbolCase.Slug)--$($Variant.Id)--$Phase"
    $setName = "ICT-Macro-$caseId.set"
    $setPath = Join-Path $testerSetRoot $setName
    Write-SetFile $Variant $setPath (862908 + $Sequence)
    $configPath = Join-Path $configRoot ($caseId + '.ini')
    $reportRelative = 'reports\ict-macro-20260829\' + $caseId + '.htm'
    $reportPath = Join-Path $testerReportRoot ($caseId + '.htm')
    $config = @"
[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=$expertFolder\ICT Macro Liquidity Sweep EA
ExpertParameters=$setName
Symbol=$($SymbolCase.Symbol)
Period=M1
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
    $winnerId = [string]$selected.$($symbolCase.Slug).variant
    $variant = $variants | Where-Object Id -eq $winnerId | Select-Object -First 1
    if (-not $variant) { throw "No selected variant for $($symbolCase.Symbol)" }
    $sequence++
    Run-Case 'locked' $symbolCase $variant $LockedFrom $LockedTo $lockedOutput $sequence
}

& $python (Join-Path $researchRoot 'Build-Report.py') --development $developmentOutput --locked $lockedOutput --selected (Join-Path $outputRoot 'selected.json') --output $researchRoot
if ($LASTEXITCODE -ne 0) { throw 'Report build failed.' }
Write-Host 'Completed development screen, locked tests, statistics and equity graphs.' -ForegroundColor Green
