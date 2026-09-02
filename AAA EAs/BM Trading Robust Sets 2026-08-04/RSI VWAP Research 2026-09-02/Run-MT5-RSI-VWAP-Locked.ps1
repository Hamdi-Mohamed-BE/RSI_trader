[CmdletBinding()]
param(
    [string]$FromDate='2025.09.01',
    [string]$ToDate='2026.09.01',
    [int]$TimeoutSeconds=1800
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
$setsRoot=Join-Path $researchRoot 'Sets'
$configRoot=Join-Path $testerRoot 'backtest-configs\rsi-vwap-20260902-locked'
$testerReportRoot=Join-Path $testerRoot 'reports\rsi-vwap-20260902-locked'
$outputRoot=Join-Path $researchRoot 'Backtest Reports\Locked Last Year Every Tick 2025-2026'
foreach($path in @($expertRoot,$testerSetRoot,$setsRoot,$configRoot,$testerReportRoot,$outputRoot)){[void](New-Item -ItemType Directory -Path $path -Force)}
Get-ChildItem -LiteralPath $outputRoot -File -ErrorAction SilentlyContinue | Remove-Item -Force
Get-ChildItem -LiteralPath $setsRoot -File -ErrorAction SilentlyContinue | Remove-Item -Force
Copy-Item -LiteralPath (Join-Path $researchRoot 'EA\RSI VWAP Managed EA.ex5') -Destination (Join-Path $expertRoot 'RSI VWAP Managed EA.ex5') -Force
$stopSelection=Get-Content -LiteralPath (Join-Path $researchRoot 'stoprr-selection.json') -Raw | ConvertFrom-Json
$trailSelection=Get-Content -LiteralPath (Join-Path $researchRoot 'trailing-selection.json') -Raw | ConvertFrom-Json
$sessionSelection=Get-Content -LiteralPath (Join-Path $researchRoot 'session-selection.json') -Raw | ConvertFrom-Json
$symbolMap=@{btcusd='BTCUSD';ethusd='ETHUSD';xauusd='XAUUSD';xagusd='XAGUSD';gbpjpy='GBPJPY';us30='US30';ustec='USTEC'}
function Decode-StopRR([string]$Id){
    if($Id -match '^atr(15|20|30)-rr(05|07|10|15|20|30)$'){
        return [pscustomobject]@{StopMode=0;StopATR=([double]$Matches[1]/10.0);RR=([double]$Matches[2]/10.0);Id=$Id}
    }
    if($Id -match '^(swing|vwap)-rr(05|10|15|20)$'){
        $mode=if($Matches[1] -eq 'swing'){1}else{2}
        return [pscustomobject]@{StopMode=$mode;StopATR=2.0;RR=([double]$Matches[2]/10.0);Id=$Id}
    }
    throw "Unknown stop/RR variant: $Id"
}
function Decode-Trail([string]$Id){
    switch($Id){
        'none' {return [pscustomobject]@{BreakEven=$false;BEAt=1.0;BELock=0.0;Trail=$false;TrailStart=1.0;TrailATR=2.0;Id=$Id}}
        'be075' {return [pscustomobject]@{BreakEven=$true;BEAt=0.75;BELock=0.05;Trail=$false;TrailStart=1.0;TrailATR=2.0;Id=$Id}}
        'be100' {return [pscustomobject]@{BreakEven=$true;BEAt=1.0;BELock=0.05;Trail=$false;TrailStart=1.0;TrailATR=2.0;Id=$Id}}
        'trail05-atr15' {return [pscustomobject]@{BreakEven=$false;BEAt=1.0;BELock=0.0;Trail=$true;TrailStart=0.5;TrailATR=1.5;Id=$Id}}
        'trail10-atr20' {return [pscustomobject]@{BreakEven=$false;BEAt=1.0;BELock=0.0;Trail=$true;TrailStart=1.0;TrailATR=2.0;Id=$Id}}
        'be075-trail10-atr15' {return [pscustomobject]@{BreakEven=$true;BEAt=0.75;BELock=0.05;Trail=$true;TrailStart=1.0;TrailATR=1.5;Id=$Id}}
        default {throw "Unknown trailing variant: $Id"}
    }
}
function Decode-Session([string]$Id){
    $value=switch($Id){'all'{0};'asia'{1};'london'{2};'newyork'{3};'overlap'{4};default{throw "Unknown session: $Id"}}
    return [pscustomobject]@{Value=$value;Id=$Id}
}
function Write-Set([string]$Path,[object]$Base,[object]$Trail,[object]$Session,[long]$Magic){
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
InpSession=$($Session.Value)
InpMaximumSpreadPoints=0
InpMaximumDeviationPoints=80
InpMagic=$Magic
"@
    [IO.File]::WriteAllText($Path,$text.TrimStart(),[Text.UTF8Encoding]::new($false))
}
function Run-Case([string]$Slug,[string]$Symbol,[string]$TF,[string]$Variant,[object]$Base,[object]$Trail,[object]$Session,[int]$Sequence){
    $caseId="$Slug--$($TF.ToLower())--$Variant--locked"
    $setName="RSIVWAP-$caseId.set"
    $savedSet=Join-Path $setsRoot $setName
    Write-Set $savedSet $Base $Trail $Session (926400000+$Sequence)
    Copy-Item -LiteralPath $savedSet -Destination (Join-Path $testerSetRoot $setName) -Force
    $configPath=Join-Path $configRoot ($caseId+'.ini')
    $reportRelative='reports\rsi-vwap-20260902-locked\'+$caseId+'.htm'
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
    Write-Host ("START {0} {1} {2}" -f $Symbol,$TF,$Variant) -ForegroundColor Cyan
    $process=Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"'+$configPath+'"')) -PassThru -WindowStyle Hidden
    try{Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop}
    catch{Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue;throw "MT5 timed out: $caseId"}
    if(-not (Test-Path -LiteralPath $reportPath)){throw "Missing MT5 report: $reportPath"}
    Get-ChildItem -LiteralPath $testerReportRoot -Filter ($caseId+'*') | Copy-Item -Destination $outputRoot -Force
}
$sequence=0
foreach($property in $stopSelection.winners.PSObject.Properties){
    $slug=$property.Name
    $stopWinner=$property.Value
    $tf=[string]$stopWinner.timeframe
    $symbol=$symbolMap[$slug]
    $baselineBase=[pscustomobject]@{StopMode=0;StopATR=2.0;RR=1.0;Id='atr20-rr10'}
    $baselineTrail=Decode-Trail 'none'
    $baselineSession=Decode-Session 'all'
    $optimizedBase=Decode-StopRR ([string]$stopWinner.variant)
    $optimizedTrail=Decode-Trail ([string]$trailSelection.winners.$slug.variant)
    $optimizedSession=Decode-Session ([string]$sessionSelection.winners.$slug.variant)
    $sequence++;Run-Case $slug $symbol $tf 'baseline' $baselineBase $baselineTrail $baselineSession $sequence
    $sequence++;Run-Case $slug $symbol $tf 'optimized' $optimizedBase $optimizedTrail $optimizedSession $sequence
}
Write-Host "Completed $sequence locked native MT5 Every Tick tests." -ForegroundColor Green
