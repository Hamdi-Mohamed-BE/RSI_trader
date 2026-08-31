[CmdletBinding()]
param(
    [string]$DevelopmentFrom='2024.08.29',
    [string]$DevelopmentTo='2025.08.28',
    [string]$LockedFrom='2025.08.29',
    [string]$LockedTo='2026.08.28',
    [int]$TimeoutSeconds=1200
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'

$researchRoot=$PSScriptRoot
$packageRoot=Split-Path -Parent $researchRoot
$testerRoot=Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'
$terminal=Join-Path $testerRoot 'terminal64.exe'
$expertFolder='AAA Research\CRT Parent Range'
$expertRoot=Join-Path (Join-Path $testerRoot 'MQL5\Experts') $expertFolder
$testerSetRoot=Join-Path $testerRoot 'MQL5\Profiles\Tester'
$configRoot=Join-Path $testerRoot 'backtest-configs\crt-parent-20260830'
$testerReportRoot=Join-Path $testerRoot 'reports\crt-parent-20260830'
$outputRoot=Join-Path $researchRoot 'Backtest Reports'
$developmentOutput=Join-Path $outputRoot 'Development 2024-2025'
$lockedOutput=Join-Path $outputRoot 'Locked 2025-2026'
$selectedSetRoot=Join-Path $researchRoot 'Sets'
$selectionPath=Join-Path $outputRoot 'selected-universal.json'
$activeConfigRoot='C:\Users\hama101\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\config'
$isolatedConfigRoot=Join-Path $testerRoot 'Config'
foreach($path in @($expertRoot,$testerSetRoot,$configRoot,$testerReportRoot,$developmentOutput,$lockedOutput,$selectedSetRoot,$isolatedConfigRoot)){
    [void](New-Item -ItemType Directory -Path $path -Force)
}
foreach($path in @($developmentOutput,$lockedOutput)){
    Get-ChildItem -LiteralPath $path -File -ErrorAction SilentlyContinue | Remove-Item -Force
}
foreach($name in @('accounts.dat','servers.dat','common.ini')){
    Copy-Item -LiteralPath (Join-Path $activeConfigRoot $name) -Destination (Join-Path $isolatedConfigRoot $name) -Force
}
$compiledSource=Join-Path $researchRoot 'EA\CRT Parent Range EA.ex5'
if(-not (Test-Path -LiteralPath $compiledSource)){throw "Compile the EA first: $compiledSource"}
Copy-Item -LiteralPath $compiledSource -Destination (Join-Path $expertRoot 'CRT Parent Range EA.ex5') -Force

$symbols=@(
    [pscustomobject]@{Symbol='BTCUSD';Slug='btcusd';Group='Crypto'},
    [pscustomobject]@{Symbol='XAUUSD';Slug='xauusd';Group='Metal'},
    [pscustomobject]@{Symbol='US500';Slug='us500';Group='Index'},
    [pscustomobject]@{Symbol='USTEC';Slug='ustec';Group='Index'},
    [pscustomobject]@{Symbol='EURUSD';Slug='eurusd';Group='Forex'},
    [pscustomobject]@{Symbol='GBPUSD';Slug='gbpusd';Group='Forex'},
    [pscustomobject]@{Symbol='USDJPY';Slug='usdjpy';Group='Forex'},
    [pscustomobject]@{Symbol='AUDUSD';Slug='audusd';Group='Forex'},
    [pscustomobject]@{Symbol='USDCAD';Slug='usdcad';Group='Forex'},
    [pscustomobject]@{Symbol='USDCHF';Slug='usdchf';Group='Forex'},
    [pscustomobject]@{Symbol='NZDUSD';Slug='nzdusd';Group='Forex'}
)
$variants=@(
    [pscustomobject]@{Id='h1-core';TF=16385;Trend=$false;Hold=16},
    [pscustomobject]@{Id='h1-daily-bias';TF=16385;Trend=$true;Hold=16},
    [pscustomobject]@{Id='h4-core';TF=16388;Trend=$false;Hold=8},
    [pscustomobject]@{Id='h4-daily-bias';TF=16388;Trend=$true;Hold=8}
)

function BoolText([bool]$Value){
    if($Value){return 'true'}
    return 'false'
}
function Find-Variant([string]$Id){
    return $variants | Where-Object Id -eq $Id | Select-Object -First 1
}
function Write-SetFile([object]$Variant,[string]$Path,[long]$Magic){
    $text=@"
InpAnchorTimeframe=$($Variant.TF)
InpATRPeriod=14
InpMinimumParentRangeATR=0.50
InpMaximumParentRangeATR=2.50
InpSweepBufferATR=0.01
InpMaximumSweepDepthATR=0.75
InpStopBufferATR=0.05
InpExcludeDoubleSweep=true
InpRequireDirectionalClose=false
InpUseDailyTrendFilter=$(BoolText $Variant.Trend)
InpTrendFastEMA=20
InpTrendSlowEMA=50
InpMinimumRewardRisk=0.50
InpMaximumRewardRisk=5.00
InpMaximumHoldingAnchorBars=$($Variant.Hold)
InpMaximumTradesPerDay=2
InpRiskPercent=1.00
InpMaximumSpreadATR=0.08
InpMaximumDeviationPoints=80
InpAllowLong=true
InpAllowShort=true
InpMagic=$Magic
"@
    [IO.File]::WriteAllText($Path,$text.TrimStart(),[Text.UTF8Encoding]::new($false))
}
function Run-Case([string]$Phase,[object]$SymbolCase,[object]$Variant,[string]$From,[string]$To,[string]$Destination,[int]$Sequence){
    $caseId="$($SymbolCase.Slug)--$($Variant.Id)--$Phase"
    $setName="CRT-$caseId.set"
    Write-SetFile $Variant (Join-Path $testerSetRoot $setName) (86500000+$Sequence)
    $configPath=Join-Path $configRoot ($caseId+'.ini')
    $reportRelative='reports\crt-parent-20260830\'+$caseId+'.htm'
    $reportPath=Join-Path $testerReportRoot ($caseId+'.htm')
    $config=@"
[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=$expertFolder\CRT Parent Range EA
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
    Get-ChildItem -LiteralPath $testerReportRoot -Filter ($caseId+'*') -ErrorAction SilentlyContinue | Remove-Item -Force
    Write-Host ("START {0} {1} {2} | {3} to {4}" -f $Phase,$SymbolCase.Symbol,$Variant.Id,$From,$To) -ForegroundColor Cyan
    $process=Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"'+$configPath+'"')) -PassThru -WindowStyle Hidden
    try{
        Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop
    } catch {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        throw "MT5 timed out: $caseId"
    }
    if(-not (Test-Path -LiteralPath $reportPath)){throw "MT5 did not create report: $reportPath"}
    Get-ChildItem -LiteralPath $testerReportRoot -Filter ($caseId+'*') | Copy-Item -Destination $Destination -Force
}

$sequence=0
foreach($symbolCase in $symbols){
    foreach($variant in $variants){
        $sequence++
        Run-Case 'development' $symbolCase $variant $DevelopmentFrom $DevelopmentTo $developmentOutput $sequence
    }
}
$python=(Get-Command python.exe -ErrorAction Stop).Source
& $python (Join-Path $researchRoot 'Analyze-CRT.py') select --development $developmentOutput --output $selectionPath
if($LASTEXITCODE -ne 0){throw 'Universal CRT selection failed'}
$selection=Get-Content -LiteralPath $selectionPath -Raw | ConvertFrom-Json
$winnerId=[string]$selection.winner
$winner=Find-Variant $winnerId
if(-not $winner){throw "Selected CRT variant is missing: $winnerId"}
foreach($symbolCase in $symbols){
    $sourceSet=Join-Path $testerSetRoot "CRT-$($symbolCase.Slug)--$winnerId--development.set"
    Copy-Item -LiteralPath $sourceSet -Destination (Join-Path $selectedSetRoot "$($symbolCase.Symbol) - universal $winnerId.set") -Force
    $sequence++
    Run-Case 'locked' $symbolCase $winner $LockedFrom $LockedTo $lockedOutput $sequence
}
& $python (Join-Path $researchRoot 'Analyze-CRT.py') report --development $developmentOutput --locked $lockedOutput --selection $selectionPath --output $researchRoot
if($LASTEXITCODE -ne 0){throw 'CRT report build failed'}
Write-Host 'Completed universal CRT development selection and locked multi-market audit.' -ForegroundColor Green
