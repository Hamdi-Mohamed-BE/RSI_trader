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
$expertRoot=Join-Path $testerRoot 'MQL5\Experts\AAA Research\RSI VWAP'
$testerSetRoot=Join-Path $testerRoot 'MQL5\Profiles\Tester'
$configRoot=Join-Path $testerRoot 'backtest-configs\rsi-vwap-20260902-trailing'
$testerReportRoot=Join-Path $testerRoot 'reports\rsi-vwap-20260902-trailing'
$outputRoot=Join-Path $researchRoot 'Backtest Reports\Development Trailing 2023-2025'
foreach($path in @($expertRoot,$testerSetRoot,$configRoot,$testerReportRoot,$outputRoot)){[void](New-Item -ItemType Directory -Path $path -Force)}
Get-ChildItem -LiteralPath $outputRoot -File -ErrorAction SilentlyContinue | Remove-Item -Force
Copy-Item -LiteralPath (Join-Path $researchRoot 'EA\RSI VWAP Managed EA.ex5') -Destination (Join-Path $expertRoot 'RSI VWAP Managed EA.ex5') -Force
$selection=Get-Content -LiteralPath (Join-Path $researchRoot 'stoprr-selection.json') -Raw | ConvertFrom-Json
$symbolMap=@{btcusd='BTCUSD';ethusd='ETHUSD';xauusd='XAUUSD';xagusd='XAGUSD';gbpjpy='GBPJPY';us30='US30';ustec='USTEC'}
$trailVariants=@(
    [pscustomobject]@{Id='none';BreakEven=$false;BEAt=1.0;BELock=0.0;Trail=$false;TrailStart=1.0;TrailATR=2.0},
    [pscustomobject]@{Id='be075';BreakEven=$true;BEAt=0.75;BELock=0.05;Trail=$false;TrailStart=1.0;TrailATR=2.0},
    [pscustomobject]@{Id='be100';BreakEven=$true;BEAt=1.0;BELock=0.05;Trail=$false;TrailStart=1.0;TrailATR=2.0},
    [pscustomobject]@{Id='trail05-atr15';BreakEven=$false;BEAt=1.0;BELock=0.0;Trail=$true;TrailStart=0.5;TrailATR=1.5},
    [pscustomobject]@{Id='trail10-atr20';BreakEven=$false;BEAt=1.0;BELock=0.0;Trail=$true;TrailStart=1.0;TrailATR=2.0},
    [pscustomobject]@{Id='be075-trail10-atr15';BreakEven=$true;BEAt=0.75;BELock=0.05;Trail=$true;TrailStart=1.0;TrailATR=1.5}
)
function Decode-StopRR([string]$Id){
    if($Id -match '^atr(15|20|30)-rr(05|07|10|15|20|30)$'){
        return [pscustomobject]@{StopMode=0;StopATR=([double]$Matches[1]/10.0);RR=([double]$Matches[2]/10.0)}
    }
    if($Id -match '^(swing|vwap)-rr(05|10|15|20)$'){
        $mode=if($Matches[1] -eq 'swing'){1}else{2}
        return [pscustomobject]@{StopMode=$mode;StopATR=2.0;RR=([double]$Matches[2]/10.0)}
    }
    throw "Unknown stop/RR variant: $Id"
}
function Write-Set([string]$Path,[object]$Base,[object]$Trail,[long]$Magic){
    $text=@"
InpRSILength=16
InpOversold=18.0
InpOverbought=80.0
InpRiskPercent=1.0
InpExitMode=2
InpStopMode=$($Base.StopMode)
InpATRPeriod=14
InpStopATR=$($Base.StopATR)
InpSwingLookback=5
InpStopBufferATR=0.10
InpRewardRisk=$($Base.RR)
InpSignalClosePercent=100.0
InpUseBreakEven=$($Trail.BreakEven.ToString().ToLower())
InpBreakEvenAtR=$($Trail.BEAt)
InpBreakEvenLockR=$($Trail.BELock)
InpUseATRTrailing=$($Trail.Trail.ToString().ToLower())
InpTrailStartR=$($Trail.TrailStart)
InpTrailATR=$($Trail.TrailATR)
InpMaximumHoldingBars=0
InpSession=0
InpMaximumSpreadPoints=0
InpMaximumDeviationPoints=80
InpMagic=$Magic
"@
    [IO.File]::WriteAllText($Path,$text.TrimStart(),[Text.UTF8Encoding]::new($false))
}
function Run-Case([string]$Slug,[string]$Symbol,[string]$TF,[object]$Base,[object]$Trail,[int]$Sequence){
    $caseId="$Slug--$($TF.ToLower())--$($Trail.Id)--development"
    $setName="RSIVWAP-$caseId.set"
    Write-Set (Join-Path $testerSetRoot $setName) $Base $Trail (926200000+$Sequence)
    $configPath=Join-Path $configRoot ($caseId+'.ini')
    $reportRelative='reports\rsi-vwap-20260902-trailing\'+$caseId+'.htm'
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
    Write-Host ("START {0} {1} {2}" -f $Symbol,$TF,$Trail.Id) -ForegroundColor Cyan
    $process=Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"'+$configPath+'"')) -PassThru -WindowStyle Hidden
    try{Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop}
    catch{Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue;throw "MT5 timed out: $caseId"}
    if(-not (Test-Path -LiteralPath $reportPath)){throw "Missing MT5 report: $reportPath"}
    Get-ChildItem -LiteralPath $testerReportRoot -Filter ($caseId+'*') | Copy-Item -Destination $outputRoot -Force
}
$sequence=0
foreach($property in $selection.winners.PSObject.Properties){
    $slug=$property.Name
    $winner=$property.Value
    $tf=[string]$winner.timeframe
    $symbol=$symbolMap[$slug]
    $base=Decode-StopRR ([string]$winner.variant)
    foreach($trail in $trailVariants){$sequence++;Run-Case $slug $symbol $tf $base $trail $sequence}
}
Write-Host "Completed $sequence native MT5 trailing development tests." -ForegroundColor Green
