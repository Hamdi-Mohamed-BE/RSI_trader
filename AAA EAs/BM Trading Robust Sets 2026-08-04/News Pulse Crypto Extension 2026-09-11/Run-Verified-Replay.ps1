[CmdletBinding()]
param([int]$TimeoutSeconds=1200)

Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$researchRoot=$PSScriptRoot
$packageRoot=Split-Path -Parent $researchRoot
$testerRoot=Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'
$terminal=Join-Path $testerRoot 'terminal64.exe'
$expertFolder='AAA Research\News Pulse FXMacroData 20260910'
$expert=Join-Path $testerRoot ('MQL5\Experts\'+$expertFolder+'\News Pulse FXMacroData.ex5')
$setRoot=Join-Path $testerRoot 'MQL5\Profiles\Tester'
$configRoot=Join-Path $testerRoot 'backtest-configs\news-pulse-crypto-verified'
$reportRoot=Join-Path $testerRoot 'reports\news-pulse-crypto-verified'
$outputRoot=Join-Path $researchRoot 'Backtest Reports\Verified'
$baseSet=Join-Path $packageRoot 'Selected Portfolio Settings 2026-09-01\12A News Pulse XAU Two Sided - HARD 1.5 TOTAL.set'
foreach($path in @($setRoot,$configRoot,$reportRoot,$outputRoot)){[void](New-Item -ItemType Directory -Path $path -Force)}
foreach($path in @($terminal,$expert,$baseSet)){if(-not(Test-Path -LiteralPath $path)){throw "Missing $path"}}

function Upsert([string]$text,[string]$key,[string]$value){
    $pattern='(?m)^'+[regex]::Escape($key)+'=.*$'
    if([regex]::IsMatch($text,$pattern)){return [regex]::Replace($text,$pattern,($key+'='+$value))}
    return $text.TrimEnd()+"`r`n"+$key+'='+$value+"`r`n"
}
$selected=Get-Content -Raw -LiteralPath (Join-Path $researchRoot 'DEVELOPMENT SELECTION.json') | ConvertFrom-Json
$manifest=[Collections.Generic.List[object]]::new()
foreach($pick in $selected){
    $setName='News Pulse Crypto Verified '+$pick.asset+'.set'
    $setText=Get-Content -Raw -LiteralPath $baseSet
    $setText=Upsert $setText 'InpEnableBuySide' ($(if($pick.direction -in @('buy-only','two-sided')){'true'}else{'false'}))
    $setText=Upsert $setText 'InpEnableSellSide' ($(if($pick.direction -in @('sell-only','two-sided')){'true'}else{'false'}))
    $setText=Upsert $setText 'InpRiskPercent' '0.75'
    $setText=Upsert $setText 'InpMagic' ($(if($pick.asset -eq 'btcusd'){'861305'}else{'861306'}))
    $setText=Upsert $setText 'InpPlacementLeadSeconds' ([string]$pick.placement_lead_seconds)
    $setText=Upsert $setText 'InpEntryOffsetPrice' ([string]$pick.entry_offset)
    $setText=Upsert $setText 'InpStopLossPrice' ([string]$pick.stop_distance)
    $setText=Upsert $setText 'InpTrailDistancePrice' ([string]$pick.trail_distance)
    $setText=Upsert $setText 'InpForceCloseSecondsAfterEvent' ([string]$pick.close_seconds)
    $setText=Upsert $setText 'InpUseDynamicTrailingSL' ($(if($pick.dynamic){'true'}else{'false'}))
    $setText=Upsert $setText 'InpTesterFromDateUTC' '20260612'
    $setText=Upsert $setText 'InpTesterToDateUTC' '20260910'
    [IO.File]::WriteAllText((Join-Path $setRoot $setName),$setText,[Text.UTF8Encoding]::new($false))
    $caseId=$pick.asset+'__verified-fxmacrodata'
    $relativeReport='reports\news-pulse-crypto-verified\'+$caseId+'.htm'
    $reportPath=Join-Path $reportRoot ($caseId+'.htm')
    $copiedReport=Join-Path $outputRoot ($caseId+'.htm')
    $configPath=Join-Path $configRoot ($caseId+'.ini')
    $config=@"
[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=$expertFolder\News Pulse FXMacroData
ExpertParameters=$setName
Symbol=$($pick.symbol)
Period=M1
Login=472334559
Deposit=10000
Currency=USD
Leverage=1:2000
Model=0
ExecutionMode=1
Optimization=0
FromDate=2026.06.12
ToDate=2026.09.10
ForwardMode=0
Report=$relativeReport
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"@
    [IO.File]::WriteAllText($configPath,$config,[Text.UTF8Encoding]::new($true))
    Remove-Item -LiteralPath $reportPath -Force -ErrorAction SilentlyContinue
    $process=Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"'+$configPath+'"')) -PassThru -WindowStyle Hidden
    try{Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop}catch{Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue;throw "Timeout $caseId"}
    if(-not(Test-Path -LiteralPath $reportPath)){throw "No report for $caseId"}
    Copy-Item -LiteralPath $reportPath -Destination $copiedReport -Force
    $manifest.Add([pscustomobject]@{
        case_id=$caseId;stage='Verified';asset=$pick.asset;symbol=$pick.symbol;period='M1';direction=$pick.direction;
        geometry=$pick.geometry;entry_offset=[double]$pick.entry_offset;stop_distance=[double]$pick.stop_distance;
        trail_distance=[double]$pick.trail_distance;management=$pick.management;
        placement_lead_seconds=[int]$pick.placement_lead_seconds;close_seconds=[int]$pick.close_seconds;
        dynamic=[bool]$pick.dynamic;buy=$true;sell=$true;risk_per_enabled_side_pct=0.75;
        total_planned_event_risk_pct=1.5;from='2026.06.12';to='2026.09.10';execution_mode=1;report=$copiedReport
    })
}
$manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $outputRoot 'manifest.json') -Encoding utf8
python (Join-Path $researchRoot 'Analyze-News-Pulse-Crypto.py') --stage Verified
if($LASTEXITCODE -ne 0){throw 'Verified replay analysis failed.'}
