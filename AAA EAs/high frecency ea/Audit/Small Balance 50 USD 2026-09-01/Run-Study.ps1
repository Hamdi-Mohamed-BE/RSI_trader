[CmdletBinding()]
param(
    [ValidateSet('Development','Locked','Final')]
    [string]$Stage='Development',
    [string]$CandidateId='',
    [int]$TimeoutSeconds=900
)

Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$studyRoot=$PSScriptRoot
$packageRoot=Split-Path -Parent (Split-Path -Parent $studyRoot)
$portfolioRoot=Split-Path -Parent $packageRoot
$testerRoot=Join-Path $portfolioRoot 'BM Trading Robust Sets 2026-08-04\_Backtests\MT5-DMC-20260811'
$terminal=Join-Path $testerRoot 'terminal64.exe'
$login='472334559'
$server='Exness-MT5Trial16'
$expertFolder='AAA Research\OCO 50 USD Study 20260901'
$expertRoot=Join-Path $testerRoot ('MQL5\Experts\'+$expertFolder)
$setRoot=Join-Path $testerRoot 'MQL5\Profiles\Tester'
$configRoot=Join-Path $testerRoot ('backtest-configs\oco-50-'+$Stage.ToLowerInvariant())
$reportRoot=Join-Path $testerRoot ('reports\oco-50-'+$Stage.ToLowerInvariant())
$outputRoot=Join-Path $studyRoot ('Reports\'+$Stage)
foreach($path in @($expertRoot,$setRoot,$configRoot,$reportRoot,$outputRoot)){
    [void](New-Item -ItemType Directory -Path $path -Force)
}
foreach($name in @('XAU M1 Current Price OCO EA.ex5','XAU M1 Current Price OCO EA.mq5','XAU M1 OCO Core.mqh')){
    Copy-Item -LiteralPath (Join-Path $packageRoot ('EA\'+$name)) -Destination $expertRoot -Force
}

$cores=@(
 [pscustomobject]@{Id='literal';Offset=.40;Stop=.50;Start=.80;Trail=.45},
 [pscustomobject]@{Id='balanced';Offset=.40;Stop=.60;Start=.90;Trail=.45},
 [pscustomobject]@{Id='protected';Offset=.50;Stop=.80;Start=1.20;Trail=.60},
 [pscustomobject]@{Id='wide';Offset=.60;Stop=1.00;Start=1.50;Trail=.75}
)
$sessions=@(
 [pscustomobject]@{Id='all';Use=$false;From=0;To=0},
 [pscustomobject]@{Id='asia';Use=$true;From=0;To=8},
 [pscustomobject]@{Id='london';Use=$true;From=7;To=12},
 [pscustomobject]@{Id='ny-open';Use=$true;From=13;To=18},
 [pscustomobject]@{Id='ny-full';Use=$true;From=13;To=21},
 [pscustomobject]@{Id='overlap';Use=$true;From=13;To=16}
)
$candidates=[Collections.Generic.List[object]]::new()
foreach($core in $cores){foreach($session in $sessions){
    $candidates.Add([pscustomobject]@{Id=($core.Id+'-'+$session.Id);Core=$core.Id;Offset=$core.Offset;Stop=$core.Stop;Start=$core.Start;Trail=$core.Trail;UseSession=$session.Use;From=$session.From;To=$session.To;Long=$true;Short=$true;Spread=.50;Volume=.00;Range=.00})
}}
$candidates.Add([pscustomobject]@{Id='literal-all-long';Core='literal';Offset=.40;Stop=.50;Start=.80;Trail=.45;UseSession=$false;From=0;To=0;Long=$true;Short=$false;Spread=.50;Volume=.00;Range=.00})
$candidates.Add([pscustomobject]@{Id='literal-all-short';Core='literal';Offset=.40;Stop=.50;Start=.80;Trail=.45;UseSession=$false;From=0;To=0;Long=$false;Short=$true;Spread=.50;Volume=.00;Range=.00})
$candidates.Add([pscustomobject]@{Id='balanced-ny-long';Core='balanced';Offset=.40;Stop=.60;Start=.90;Trail=.45;UseSession=$true;From=13;To=18;Long=$true;Short=$false;Spread=.50;Volume=.00;Range=.00})
$candidates.Add([pscustomobject]@{Id='balanced-ny-short';Core='balanced';Offset=.40;Stop=.60;Start=.90;Trail=.45;UseSession=$true;From=13;To=18;Long=$false;Short=$true;Spread=.50;Volume=.00;Range=.00})
$candidates.Add([pscustomobject]@{Id='balanced-ny-volume08';Core='balanced';Offset=.40;Stop=.60;Start=.90;Trail=.45;UseSession=$true;From=13;To=18;Long=$true;Short=$true;Spread=.50;Volume=.80;Range=.00})
$candidates.Add([pscustomobject]@{Id='balanced-ny-spread035';Core='balanced';Offset=.40;Stop=.60;Start=.90;Trail=.45;UseSession=$true;From=13;To=18;Long=$true;Short=$true;Spread=.35;Volume=.00;Range=.00})
$candidates.Add([pscustomobject]@{Id='balanced-ny-range05';Core='balanced';Offset=.40;Stop=.60;Start=.90;Trail=.45;UseSession=$true;From=13;To=18;Long=$true;Short=$true;Spread=.50;Volume=.00;Range=.50})

if($Stage -eq 'Development'){
    $period=@{From='2026.07.01';To='2026.07.31'}
    $cases=$candidates
}elseif($Stage -eq 'Locked'){
    $period=@{From='2026.08.01';To='2026.08.31'}
    $selection=Get-Content -Raw -LiteralPath (Join-Path $studyRoot 'development-selection.json') | ConvertFrom-Json
    $cases=foreach($pick in $selection){$candidates | Where-Object Id -eq $pick.id | Select-Object -First 1}
}else{
    $period=@{From='2026.07.01';To='2026.08.31'}
    if([string]::IsNullOrWhiteSpace($CandidateId)){
        $winner=Get-Content -Raw -LiteralPath (Join-Path $studyRoot 'winner.json') | ConvertFrom-Json
        $CandidateId=$winner.id
    }
    $cases=@($candidates | Where-Object Id -eq $CandidateId | Select-Object -First 1)
}

function BoolText([bool]$value){if($value){'true'}else{'false'}}
function Upsert([string]$text,[string]$key,[string]$value){
    $pattern='(?m)^'+[regex]::Escape($key)+'=.*$'
    if([regex]::IsMatch($text,$pattern)){return [regex]::Replace($text,$pattern,($key+'='+$value))}
    return $text.TrimEnd()+"`r`n"+$key+'='+$value+"`r`n"
}

$baseSet=Get-Content -Raw -LiteralPath (Join-Path $packageRoot 'Settings\DEFAULT - XAUUSD M1 - Current Price OCO.set')
$manifest=[Collections.Generic.List[object]]::new()
foreach($case in $cases){
    if($null -eq $case){continue}
    $set=$baseSet
    $values=[ordered]@{
      InpUseATRDistances='false'; InpEntryOffsetPrice=([string]$case.Offset); InpStopDistancePrice=([string]$case.Stop)
      InpTrailStartPrice=([string]$case.Start); InpTrailDistancePrice=([string]$case.Trail)
      InpMinimumPreviousRangeATR=([string]$case.Range); InpMinimumVolumeRatio=([string]$case.Volume)
      InpMaximumSpreadPrice=([string]$case.Spread); InpUseSessionFilter=(BoolText $case.UseSession)
      InpSessionStartHour=([string]$case.From); InpSessionEndHour=([string]$case.To)
      InpAllowLong=(BoolText $case.Long); InpAllowShort=(BoolText $case.Short)
      InpBaseLot='0.01'; InpReferenceBalance='50'; InpScaleLotWithEquity='false'
      InpMinimumConfiguredLot='0.01'; InpMaximumConfiguredLot='0.01'; InpMagic='864050'
    }
    foreach($entry in $values.GetEnumerator()){$set=Upsert $set $entry.Key $entry.Value}
    $setName=('OCO50-{0}-{1}.set' -f $Stage.ToLowerInvariant(),$case.Id)
    [IO.File]::WriteAllText((Join-Path $setRoot $setName),$set,[Text.UTF8Encoding]::new($false))
    $caseId=([string]$case.Id).ToLowerInvariant()
    $configPath=Join-Path $configRoot ($caseId+'.ini')
    $reportPath=Join-Path $reportRoot ($caseId+'.htm')
    $relative='reports\oco-50-{0}\{1}.htm' -f $Stage.ToLowerInvariant(),$caseId
    $config=@"
[Common]
Login=$login
Server=$server

[Tester]
Expert=$expertFolder\XAU M1 Current Price OCO EA
ExpertParameters=$setName
Symbol=XAUUSD
Period=M1
Login=$login
Deposit=50
Currency=USD
Leverage=1:2000
Model=0
ExecutionMode=1
Optimization=0
FromDate=$($period.From)
ToDate=$($period.To)
ForwardMode=0
Report=$relative
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"@
    [IO.File]::WriteAllText($configPath,$config,[Text.UTF8Encoding]::new($true))
    Get-ChildItem -LiteralPath $reportRoot -Filter ($caseId+'*') -ErrorAction SilentlyContinue | Remove-Item -Force
    Write-Host ('START '+$case.Id) -ForegroundColor Cyan
    $process=Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"'+$configPath+'"')) -PassThru -WindowStyle Hidden
    try{Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop}
    catch{Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue;throw "TIMEOUT $caseId"}
    if(-not(Test-Path -LiteralPath $reportPath)){throw "NO REPORT $caseId"}
    Get-ChildItem -LiteralPath $reportRoot -Filter ($caseId+'*') | Copy-Item -Destination $outputRoot -Force
    $manifest.Add([pscustomobject]@{id=$case.Id;core=$case.Core;offset=$case.Offset;stop=$case.Stop;trail_start=$case.Start;trail_distance=$case.Trail;use_session=$case.UseSession;session_start=$case.From;session_end=$case.To;long=$case.Long;short=$case.Short;max_spread=$case.Spread;volume_ratio=$case.Volume;range_atr=$case.Range;stage=$Stage;from=$period.From;to=$period.To;report=(Join-Path $outputRoot ($caseId+'.htm'))})
    Start-Sleep -Milliseconds 500
}
$manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $outputRoot 'manifest.json') -Encoding utf8
& python.exe (Join-Path $studyRoot 'Analyze-Study.py') $Stage
if($LASTEXITCODE -ne 0){throw 'Analysis failed.'}
