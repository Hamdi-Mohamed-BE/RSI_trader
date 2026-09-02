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
$testerSetRoot=Join-Path $testerRoot 'MQL5\Profiles\Tester'
$configRoot=Join-Path $testerRoot 'backtest-configs\rsi-vwap-20260902-stoprr'
$testerReportRoot=Join-Path $testerRoot 'reports\rsi-vwap-20260902-stoprr'
$outputRoot=Join-Path $researchRoot 'Backtest Reports\Development Stop RR 2023-2025'
foreach($path in @($testerSetRoot,$configRoot,$testerReportRoot,$outputRoot)){[void](New-Item -ItemType Directory -Path $path -Force)}
Get-ChildItem -LiteralPath $outputRoot -File -ErrorAction SilentlyContinue | Remove-Item -Force
$screen=Get-Content -LiteralPath (Join-Path $researchRoot 'timeframe-screen.json') -Raw | ConvertFrom-Json
$symbolMap=@{btcusd='BTCUSD';ethusd='ETHUSD';xauusd='XAUUSD';xagusd='XAGUSD';gbpjpy='GBPJPY';us30='US30';ustec='USTEC'}
$variants=@()
foreach($stop in @(1.5,2.0,3.0)){
    foreach($rr in @(0.5,0.7,1.0,1.5,2.0,3.0)){
        $variants += [pscustomobject]@{Id=('atr'+($stop.ToString('0.0').Replace('.',''))+'-rr'+($rr.ToString('0.0').Replace('.','')));StopMode=0;StopATR=$stop;RR=$rr}
    }
}
foreach($mode in @([pscustomobject]@{Name='swing';Value=1},[pscustomobject]@{Name='vwap';Value=2})){
    foreach($rr in @(0.5,1.0,1.5,2.0)){
        $variants += [pscustomobject]@{Id=($mode.Name+'-rr'+($rr.ToString('0.0').Replace('.','')));StopMode=$mode.Value;StopATR=2.0;RR=$rr}
    }
}
function Write-Set([string]$Path,[object]$Variant,[long]$Magic){
    $text=@"
InpRSILength=16
InpOversold=18.0
InpOverbought=80.0
InpRiskPercent=1.0
InpExitMode=1
InpStopMode=$($Variant.StopMode)
InpATRPeriod=14
InpStopATR=$($Variant.StopATR)
InpSwingLookback=5
InpStopBufferATR=0.10
InpRewardRisk=$($Variant.RR)
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
function Run-Case([string]$Slug,[string]$Symbol,[string]$TF,[object]$Variant,[int]$Sequence){
    $caseId="$Slug--$($TF.ToLower())--$($Variant.Id)--development"
    $setName="RSIVWAP-$caseId.set"
    Write-Set (Join-Path $testerSetRoot $setName) $Variant (926100000+$Sequence)
    $configPath=Join-Path $configRoot ($caseId+'.ini')
    $reportRelative='reports\rsi-vwap-20260902-stoprr\'+$caseId+'.htm'
    $reportPath=Join-Path $testerReportRoot ($caseId+'.htm')
    $config=@"
[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=$expertFolder\RSI VWAP Managed EA
ExpertParameters=$setName
Symbol=$Symbol
Period=$TF
Login=472334559
Deposit=10000
Currency=USD
Leverage=1:2000
Model=1
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
    Write-Host ("START {0} {1} {2}" -f $Symbol,$TF,$Variant.Id) -ForegroundColor Cyan
    $process=Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"'+$configPath+'"')) -PassThru -WindowStyle Hidden
    try{Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop}
    catch{Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue;throw "MT5 timed out: $caseId"}
    if(-not (Test-Path -LiteralPath $reportPath)){throw "Missing MT5 report: $reportPath"}
    Get-ChildItem -LiteralPath $testerReportRoot -Filter ($caseId+'*') | Copy-Item -Destination $outputRoot -Force
}
$sequence=0
foreach($property in $screen.winners.PSObject.Properties){
    $slug=$property.Name
    $tf=[string]$property.Value.timeframe
    $symbol=$symbolMap[$slug]
    foreach($variant in $variants){$sequence++;Run-Case $slug $symbol $tf $variant $sequence}
}
Write-Host "Completed $sequence native MT5 stop/RR development tests." -ForegroundColor Green
