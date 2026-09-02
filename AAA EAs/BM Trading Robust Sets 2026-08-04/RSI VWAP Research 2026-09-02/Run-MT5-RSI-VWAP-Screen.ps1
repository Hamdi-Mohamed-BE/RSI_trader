[CmdletBinding()]
param(
    [string]$FromDate='2023.09.01',
    [string]$ToDate='2025.08.31',
    [int]$TimeoutSeconds=900
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'

$researchRoot=$PSScriptRoot
$packageRoot=Split-Path -Parent $researchRoot
$testerRoot=Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'
$terminal=Join-Path $testerRoot 'terminal64.exe'
$expertFolder='AAA Research\RSI VWAP'
$expertRoot=Join-Path (Join-Path $testerRoot 'MQL5\Experts') $expertFolder
$testerSetRoot=Join-Path $testerRoot 'MQL5\Profiles\Tester'
$configRoot=Join-Path $testerRoot 'backtest-configs\rsi-vwap-20260902'
$testerReportRoot=Join-Path $testerRoot 'reports\rsi-vwap-20260902'
$outputRoot=Join-Path $researchRoot 'Backtest Reports\Development Screen 2023-2025'
$isolatedConfigRoot=Join-Path $testerRoot 'Config'
$activeConfigRoot='C:\Users\hama101\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\config'
foreach($path in @($expertRoot,$testerSetRoot,$configRoot,$testerReportRoot,$outputRoot,$isolatedConfigRoot)){
    [void](New-Item -ItemType Directory -Path $path -Force)
}
Get-ChildItem -LiteralPath $outputRoot -File -ErrorAction SilentlyContinue | Remove-Item -Force
foreach($name in @('accounts.dat','servers.dat','common.ini')){
    $source=Join-Path $activeConfigRoot $name
    if(Test-Path -LiteralPath $source){Copy-Item -LiteralPath $source -Destination (Join-Path $isolatedConfigRoot $name) -Force}
}
$compiled=Join-Path $researchRoot 'EA\RSI VWAP Managed EA.ex5'
if(-not (Test-Path -LiteralPath $compiled)){throw "Missing compiled EA: $compiled"}
Copy-Item -LiteralPath $compiled -Destination (Join-Path $expertRoot 'RSI VWAP Managed EA.ex5') -Force

$symbols=@(
    [pscustomobject]@{Symbol='BTCUSD';Slug='btcusd'},
    [pscustomobject]@{Symbol='ETHUSD';Slug='ethusd'},
    [pscustomobject]@{Symbol='XAUUSD';Slug='xauusd'},
    [pscustomobject]@{Symbol='XAGUSD';Slug='xagusd'},
    [pscustomobject]@{Symbol='GBPJPY';Slug='gbpjpy'},
    [pscustomobject]@{Symbol='US30';Slug='us30'},
    [pscustomobject]@{Symbol='USTEC';Slug='ustec'}
)
$timeframes=@('M5','M15','M30','H1','H4')

function Write-Set([string]$Path,[long]$Magic){
    $text=@"
InpRSILength=16
InpOversold=18.0
InpOverbought=80.0
InpRiskPercent=1.0
InpExitMode=1
InpStopMode=0
InpATRPeriod=14
InpStopATR=2.0
InpSwingLookback=5
InpStopBufferATR=0.10
InpRewardRisk=1.0
InpSignalClosePercent=100.0
InpUseBreakEven=false
InpBreakEvenAtR=0.75
InpBreakEvenLockR=0.05
InpUseATRTrailing=false
InpTrailStartR=1.0
InpTrailATR=2.0
InpMaximumHoldingBars=0
InpSession=0
InpMaximumSpreadPoints=0
InpMaximumDeviationPoints=80
InpMagic=$Magic
"@
    [IO.File]::WriteAllText($Path,$text.TrimStart(),[Text.UTF8Encoding]::new($false))
}

function Run-Case([object]$SymbolCase,[string]$Timeframe,[int]$Sequence){
    $caseId="$($SymbolCase.Slug)--$($Timeframe.ToLower())--baseline--development"
    $setName="RSIVWAP-$caseId.set"
    Write-Set (Join-Path $testerSetRoot $setName) (926090000+$Sequence)
    $configPath=Join-Path $configRoot ($caseId+'.ini')
    $reportRelative='reports\rsi-vwap-20260902\'+$caseId+'.htm'
    $reportPath=Join-Path $testerReportRoot ($caseId+'.htm')
    $config=@"
[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=$expertFolder\RSI VWAP Managed EA
ExpertParameters=$setName
Symbol=$($SymbolCase.Symbol)
Period=$Timeframe
Login=472334559
Deposit=10000
Currency=USD
Leverage=1:2000
Model=0
ExecutionMode=1
Optimization=0
FromDate=$FromDate
ToDate=$ToDate
ForwardMode=0
Report=$reportRelative
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"@
    [IO.File]::WriteAllText($configPath,$config,[Text.UTF8Encoding]::new($true))
    Get-ChildItem -LiteralPath $testerReportRoot -Filter ($caseId+'*') -ErrorAction SilentlyContinue | Remove-Item -Force
    Write-Host ("START {0} {1}" -f $SymbolCase.Symbol,$Timeframe) -ForegroundColor Cyan
    $process=Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"'+$configPath+'"')) -PassThru -WindowStyle Hidden
    try{Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop}
    catch{Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue;throw "MT5 timed out: $caseId"}
    if(-not (Test-Path -LiteralPath $reportPath)){throw "Missing MT5 report: $reportPath"}
    Get-ChildItem -LiteralPath $testerReportRoot -Filter ($caseId+'*') | Copy-Item -Destination $outputRoot -Force
}

$sequence=0
foreach($symbolCase in $symbols){
    foreach($timeframe in $timeframes){
        $sequence++
        Run-Case $symbolCase $timeframe $sequence
    }
}
Write-Host "Completed $sequence native MT5 baseline screens." -ForegroundColor Green
