[CmdletBinding()]
param(
    [ValidateSet('Development','Locked','August')]
    [string]$Stage='Development',
    [int]$TimeoutSeconds=1800
)

Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$researchRoot=$PSScriptRoot
$packageRoot=Split-Path -Parent $researchRoot
$testerRoot=Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'
$terminal=Join-Path $testerRoot 'terminal64.exe'
$expertFolder='AAA Research\XAU M1 OCO Reel 20260901'
$expertRoot=Join-Path $testerRoot ('MQL5\Experts\'+$expertFolder)
$setRoot=Join-Path $testerRoot 'MQL5\Profiles\Tester'
$localSetRoot=Join-Path $researchRoot 'Sets'
$runSlug='xau-m1-oco-reel-'+$Stage.ToLowerInvariant()
$configRoot=Join-Path $testerRoot ('backtest-configs\'+$runSlug)
$testerReportRoot=Join-Path $testerRoot ('reports\'+$runSlug)
$outputRoot=Join-Path $researchRoot ('Backtest Reports\'+$Stage)
$activeConfigRoot='C:\Users\hama101\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\config'
$isolatedConfigRoot=Join-Path $testerRoot 'Config'
foreach($path in @($expertRoot,$setRoot,$localSetRoot,$configRoot,$testerReportRoot,$outputRoot,$isolatedConfigRoot)){
    [void](New-Item -ItemType Directory -Path $path -Force)
}
foreach($name in @('accounts.dat','servers.dat','common.ini')){
    Copy-Item -LiteralPath (Join-Path $activeConfigRoot $name) -Destination (Join-Path $isolatedConfigRoot $name) -Force
}
Copy-Item -LiteralPath (Join-Path $researchRoot 'EA\XAU M1 OCO Core.mqh') -Destination $expertRoot -Force
foreach($name in @('XAU M1 Current Price OCO EA','XAU M1 Previous Candle OCO EA')){
    Copy-Item -LiteralPath (Join-Path $researchRoot ('EA\'+$name+'.ex5')) -Destination $expertRoot -Force
}

$variants=@(
    [pscustomobject]@{Mode='current';Id='literal-fixed';Expert='XAU M1 Current Price OCO EA';ATR=$false;Offset=.40;Stop=.50;Start=.80;Trail=.45;OffsetATR=.25;StopATR=.75;StartATR=1.0;TrailATR=.45;RangeStop=$false;RangeMult=1.0;MinRange=0.0;Volume=0.0;Session=$false},
    [pscustomobject]@{Mode='current';Id='balanced-fixed';Expert='XAU M1 Current Price OCO EA';ATR=$false;Offset=.60;Stop=.80;Start=1.20;Trail=.60;OffsetATR=.25;StopATR=.75;StartATR=1.0;TrailATR=.45;RangeStop=$false;RangeMult=1.0;MinRange=0.0;Volume=0.0;Session=$false},
    [pscustomobject]@{Mode='current';Id='atr-adaptive';Expert='XAU M1 Current Price OCO EA';ATR=$true;Offset=.40;Stop=.50;Start=.80;Trail=.45;OffsetATR=.25;StopATR=.75;StartATR=1.0;TrailATR=.45;RangeStop=$false;RangeMult=1.0;MinRange=0.0;Volume=0.0;Session=$false},
    [pscustomobject]@{Mode='current';Id='atr-impulse-volume';Expert='XAU M1 Current Price OCO EA';ATR=$true;Offset=.40;Stop=.50;Start=.80;Trail=.45;OffsetATR=.25;StopATR=.75;StartATR=1.0;TrailATR=.45;RangeStop=$false;RangeMult=1.0;MinRange=.75;Volume=1.10;Session=$false},
    [pscustomobject]@{Mode='current';Id='atr-liquid-session';Expert='XAU M1 Current Price OCO EA';ATR=$true;Offset=.40;Stop=.50;Start=.80;Trail=.45;OffsetATR=.25;StopATR=.75;StartATR=1.0;TrailATR=.45;RangeStop=$false;RangeMult=1.0;MinRange=0.0;Volume=0.0;Session=$true},
    [pscustomobject]@{Mode='previous';Id='fixed-dollar';Expert='XAU M1 Previous Candle OCO EA';ATR=$false;Offset=.05;Stop=.80;Start=1.20;Trail=.60;OffsetATR=.10;StopATR=.85;StartATR=1.1;TrailATR=.50;RangeStop=$false;RangeMult=1.0;MinRange=0.0;Volume=0.0;Session=$false},
    [pscustomobject]@{Mode='previous';Id='candle-range-stop';Expert='XAU M1 Previous Candle OCO EA';ATR=$false;Offset=.05;Stop=.80;Start=1.20;Trail=.60;OffsetATR=.10;StopATR=.85;StartATR=1.1;TrailATR=.50;RangeStop=$true;RangeMult=1.0;MinRange=0.0;Volume=0.0;Session=$false},
    [pscustomobject]@{Mode='previous';Id='atr-adaptive';Expert='XAU M1 Previous Candle OCO EA';ATR=$true;Offset=.05;Stop=.80;Start=1.20;Trail=.60;OffsetATR=.10;StopATR=.85;StartATR=1.1;TrailATR=.50;RangeStop=$false;RangeMult=1.0;MinRange=0.0;Volume=0.0;Session=$false},
    [pscustomobject]@{Mode='previous';Id='atr-impulse-volume';Expert='XAU M1 Previous Candle OCO EA';ATR=$true;Offset=.05;Stop=.80;Start=1.20;Trail=.60;OffsetATR=.10;StopATR=.85;StartATR=1.1;TrailATR=.50;RangeStop=$false;RangeMult=1.0;MinRange=.75;Volume=1.10;Session=$false},
    [pscustomobject]@{Mode='previous';Id='atr-liquid-session';Expert='XAU M1 Previous Candle OCO EA';ATR=$true;Offset=.05;Stop=.80;Start=1.20;Trail=.60;OffsetATR=.10;StopATR=.85;StartATR=1.1;TrailATR=.50;RangeStop=$false;RangeMult=1.0;MinRange=0.0;Volume=0.0;Session=$true}
)

if($Stage -eq 'Development'){
    # Keep selection separate from the requested July-August audit while
    # avoiding an unnecessary year-long tick replay for this M1 order-churn EA.
    $period=@{From='2026.04.01';To='2026.06.30'}
    $cases=$variants
}else{
    $period=if($Stage -eq 'Locked'){@{From='2026.07.01';To='2026.08.31'}}else{@{From='2026.08.01';To='2026.08.31'}}
    $selectionPath=Join-Path $researchRoot 'selection.json'
    if(-not (Test-Path -LiteralPath $selectionPath)){throw 'Development selection is missing.'}
    $selection=Get-Content -Raw -LiteralPath $selectionPath | ConvertFrom-Json
    $cases=foreach($pick in $selection){
        $match=$variants | Where-Object {$_.Mode -eq $pick.mode -and $_.Id -eq $pick.variant} | Select-Object -First 1
        if($null -eq $match){throw "Unknown selected case $($pick.mode)/$($pick.variant)"}
        $match
    }
}

function BoolText([bool]$value){if($value){'true'}else{'false'}}
function New-SetText($v,[int]$magic){
@"
InpUseATRDistances=$(BoolText $v.ATR)
InpATRPeriod=14
InpEntryOffsetPrice=$($v.Offset)
InpStopDistancePrice=$($v.Stop)
InpTrailStartPrice=$($v.Start)
InpTrailDistancePrice=$($v.Trail)
InpEntryOffsetATR=$($v.OffsetATR)
InpStopDistanceATR=$($v.StopATR)
InpTrailStartATR=$($v.StartATR)
InpTrailDistanceATR=$($v.TrailATR)
InpUsePreviousRangeForStop=$(BoolText $v.RangeStop)
InpPreviousRangeStopMultiplier=$($v.RangeMult)
InpMinimumStopPrice=0.25
InpMaximumStopPrice=3.00
InpMinimumPreviousRangeATR=$($v.MinRange)
InpVolumeAverageBars=20
InpMinimumVolumeRatio=$($v.Volume)
InpMaximumSpreadPrice=0.50
InpUseSessionFilter=$(BoolText $v.Session)
InpSessionStartHour=12
InpSessionEndHour=18
InpAllowLong=true
InpAllowShort=true
InpMaximumHoldingMinutes=180
InpReplacePendingEachNewBar=true
InpMaximumDeviationPoints=50
InpBaseLot=0.04
InpReferenceBalance=10000.0
InpScaleLotWithEquity=true
InpMinimumConfiguredLot=0.01
InpMaximumConfiguredLot=1.00
InpMagic=$magic
"@
}

$manifest=[Collections.Generic.List[object]]::new()
$index=0
foreach($v in $cases){
    $index++
    $caseId=($v.Mode+'__'+$v.Id).ToLowerInvariant()
    $setName=('XAU M1 OCO {0} {1} {2}.set' -f $Stage.ToUpperInvariant(),$v.Mode,$v.Id)
    $setText=New-SetText $v (864010+$index)
    [IO.File]::WriteAllText((Join-Path $setRoot $setName),$setText,[Text.UTF8Encoding]::new($false))
    [IO.File]::WriteAllText((Join-Path $localSetRoot $setName),$setText,[Text.UTF8Encoding]::new($false))
    $configPath=Join-Path $configRoot ($caseId+'.ini')
    $reportPath=Join-Path $testerReportRoot ($caseId+'.htm')
    $relativeReport='reports\{0}\{1}.htm' -f $runSlug,$caseId
    $config=@"
[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=$expertFolder\$($v.Expert)
ExpertParameters=$setName
Symbol=XAUUSD
Period=M1
Login=472334559
Deposit=10000
Currency=USD
Leverage=1:2000
Model=0
ExecutionMode=1
Optimization=0
FromDate=$($period.From)
ToDate=$($period.To)
ForwardMode=0
Report=$relativeReport
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"@
    [IO.File]::WriteAllText($configPath,$config,[Text.UTF8Encoding]::new($true))
    Get-ChildItem -LiteralPath $testerReportRoot -Filter ($caseId+'*') -ErrorAction SilentlyContinue | Remove-Item -Force
    Write-Host ('START {0} {1} to {2}' -f $caseId,$period.From,$period.To) -ForegroundColor Cyan
    $process=Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"'+$configPath+'"')) -PassThru -WindowStyle Hidden
    try{Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop}
    catch{Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue;throw "TIMEOUT $caseId"}
    if(-not (Test-Path -LiteralPath $reportPath)){throw "NO REPORT $caseId"}
    Get-ChildItem -LiteralPath $testerReportRoot -Filter ($caseId+'*') | Copy-Item -Destination $outputRoot -Force
    $manifest.Add([pscustomobject]@{Mode=$v.Mode;Variant=$v.Id;Stage=$Stage;From=$period.From;To=$period.To;Report=(Join-Path $outputRoot ($caseId+'.htm'))})
    # MT5 releases its portable-instance mutex a moment after the process exits.
    # Without this pause a rapid second launch can emit an empty M0/1970 report.
    Start-Sleep -Seconds 3
}
$manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $outputRoot 'manifest.json') -Encoding utf8
& (Get-Command python.exe -ErrorAction Stop).Source (Join-Path $researchRoot 'Analyze-Reports.py') $outputRoot (Join-Path $researchRoot ($Stage.ToLowerInvariant()+'-results'))
if($LASTEXITCODE -ne 0){throw 'Report analysis failed.'}
Write-Host ('Completed '+$Stage+' tests.') -ForegroundColor Green
