[CmdletBinding()]
param(
    [ValidateSet('Development','Locked')]
    [string]$Stage='Development',
    [int]$TimeoutSeconds=1800
)

Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$researchRoot=$PSScriptRoot
$packageRoot=Split-Path -Parent $researchRoot
$testerRoot=Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'
$testerLogin='472334559'
$testerServer='Exness-MT5Trial16'
$terminal=Join-Path $testerRoot 'terminal64.exe'
$expertFolder='AAA Research\Dynamic Trailing Session 20260901'
$expertRoot=Join-Path $testerRoot ('MQL5\Experts\'+$expertFolder)
$setRoot=Join-Path $testerRoot 'MQL5\Profiles\Tester'
$localSetRoot=Join-Path $researchRoot 'Sets'
$runSlug='dynamic-trailing-session-'+$Stage.ToLowerInvariant()
$configRoot=Join-Path $testerRoot ('backtest-configs\'+$runSlug)
$testerReportRoot=Join-Path $testerRoot ('reports\'+$runSlug)
$outputRoot=Join-Path $researchRoot ('Backtest Reports\'+$Stage)
foreach($path in @($expertRoot,$setRoot,$localSetRoot,$configRoot,$testerReportRoot,$outputRoot)){
    [void](New-Item -ItemType Directory -Path $path -Force)
}

$items=@(
 [pscustomobject]@{Id='lta-xau';Label='LTA Volume Profile';Symbol='XAUUSD';Period='M15';Expert='LTA_Concepts_EA';Research='lta\LTA_Concepts_EA.ex5';Set='LTA volume profile\Best Settings\RETEST PASSED 2026-08-07 - LTA - XAUUSD M15 - 1pct.set'},
 [pscustomobject]@{Id='topdown-btc';Label='BTC Top Down FVG Liquidity';Symbol='BTCUSD';Period='M15';Expert='Top Down FVG Liquidity EA';Research='top-down-fvg\Top Down FVG Liquidity EA.ex5';Set='Top Down FVG Liquidity Research 2026-08-27\Sets\SELECTED - BTCUSD M15 - Top Down FVG Liquidity - 1pct.set'},
 [pscustomobject]@{Id='topdown-eth';Label='ETH Top Down FVG Liquidity';Symbol='ETHUSD';Period='M15';Expert='Top Down FVG Liquidity EA';Research='top-down-fvg\Top Down FVG Liquidity EA.ex5';Set='Top Down FVG Liquidity Research 2026-08-27\Sets\SELECTED - ETHUSD M15 - Top Down FVG Liquidity - 1pct.set'},
 [pscustomobject]@{Id='engineered-xau';Label='Engineered Liquidity XAU';Symbol='XAUUSD';Period='H1';Expert='Engineered Liquidity Sweep EA';Research='engineered-liquidity\Engineered Liquidity Sweep EA.ex5';Set='Engineered Liquidity Sweep Research 2026-08-30\Sets\XAUUSD - h1-d1-reclaim - locked.set'},
 [pscustomobject]@{Id='engineered-btc';Label='Engineered Liquidity BTC';Symbol='BTCUSD';Period='M30';Expert='Engineered Liquidity Sweep EA';Research='engineered-liquidity\Engineered Liquidity Sweep EA.ex5';Set='Engineered Liquidity Sweep Research 2026-08-30\Sets\BTCUSD - m30-h4-reclaim - locked.set'},
 [pscustomobject]@{Id='orb-volume-xau';Label='ORB Volume Profile';Symbol='XAUUSD';Period='M5';Expert='ORB Volume Data EA';Research='orb-volume\ORB Volume Data EA.ex5';Set='ORB Volume Data EA\Volume Profile Settings\VISUAL PROFILE - XAUUSD M5 - validated baseline.set'},
 [pscustomobject]@{Id='fabio-ustec';Label='US100 Fabio ORB 1R';Symbol='USTEC';Period='M5';Expert='US100 Fabio ORB Volatility Target EA';Research='fabio-orb\US100 Fabio ORB Volatility Target EA.ex5';Set='US100 Fabio ORB Volatility Target Research 2026-08-26\Sets\LITERAL - USTEC M5 - ORB30 direct long RR1 - 1pct.set'},
 [pscustomobject]@{Id='markov-xau';Label='XAU Markov Regime';Symbol='XAUUSD';Period='D1';Expert='XAU Markov Regime EA';Research='markov\XAU Markov Regime EA.ex5';Set='XAU Markov Regime EA\LOCKED - XAUUSD D1 - Markov40 Gate005 ATR4 RR3 - 1pct.set'},
 [pscustomobject]@{Id='asia-xau';Label='AAA Final Asia Breakout';Symbol='XAUUSD';Period='H1';Expert='AAA Final Asia Breakout EA';Research='asia-breakout\AAA Final Asia Breakout EA.ex5';Set='AAA Final EAs\AAA Final Asia Breakout EA\RETEST PASSED 2026-08-07 - Asia Breakout - XAUUSD H1 - 1pct.set'},
 [pscustomobject]@{Id='dmc-xau';Label='AAA Final DmC';Symbol='XAUUSD';Period='H1';Expert='AAA Final DmC EA';Research='dmc\AAA Final DmC EA.ex5';Set='AAA Final EAs\AAA Final DmC EA\RETEST PASSED 2026-08-07 - DmC - XAUUSD H1 - 1pct.set'},
 [pscustomobject]@{Id='ema3-xau';Label='AAA Final EMA3';Symbol='XAUUSD';Period='H4';Expert='AAA Final EMA3 EA';Research='ema3\AAA Final EMA3 EA.ex5';Set='AAA Final EAs\AAA Final EMA3 EA\RETEST INCLUDED 2026-08-07 - EMA3 - XAUUSD H4 - 1pct.set'},
 [pscustomobject]@{Id='weakness-xau';Label='AAA Final XAU Weakness';Symbol='XAUUSD';Period='M15';Expert='AAA Final XAU Weakness EA';Research='xau-weakness\AAA Final XAU Weakness EA.ex5';Set='AAA Final EAs\AAA Final XAU Weakness EA\RETEST INCLUDED 2026-08-07 - XAU Weakness - XAUUSD M15 - 1pct.set'},
 [pscustomobject]@{Id='overnight-ustec';Label='Nasdaq Overnight';Symbol='USTEC';Period='M1';Expert='Nasdaq Overnight Negative Day EA';Research='nasdaq-overnight\Nasdaq Overnight Negative Day EA.ex5';Set='Nasdaq Overnight Negative Day EA\RETEST INCLUDED 2026-08-07 - Nasdaq Overnight - USTEC M1 - 1pct.set'},
 [pscustomobject]@{Id='momentum-ustec';Label='Nasdaq 5M Candle Momentum';Symbol='USTEC';Period='M5';Expert='Nasdaq 5M Open EMA ATR EA';Research='nasdaq-momentum\Nasdaq 5M Open EMA ATR EA.ex5';Set='Nasdaq 5M Open EMA ATR Research 2026-08-20\Sets\SELECTED - USTEC M5 - 982 claim recheck - 1pct.set'},
 [pscustomobject]@{Id='news-xau';Label='News Pulse LONG ONLY';Symbol='XAUUSD';Period='M1';Expert='AAA Final News Pulse EA';Research='news-pulse\AAA Final News Pulse EA.ex5';Set='AAA Final EAs\AAA Final News Pulse EA\BEST ROBUST LONG ONLY 2026-08-09 - News Pulse - XAUUSD M1 - 1pct - 60sec.set'}
)
$sessions=@(
 [pscustomobject]@{Id='all';Value=0},
 [pscustomobject]@{Id='asia';Value=1},
 [pscustomobject]@{Id='london';Value=2},
 [pscustomobject]@{Id='new-york';Value=3},
 [pscustomobject]@{Id='overlap';Value=4}
)

foreach($item in $items){
    $source=Join-Path $researchRoot ('EA\'+$item.Research)
    $baseSet=Join-Path $packageRoot $item.Set
    if(-not(Test-Path -LiteralPath $source)){throw "Missing research EA: $source"}
    if(-not(Test-Path -LiteralPath $baseSet)){throw "Missing baseline set: $baseSet"}
    Copy-Item -LiteralPath $source -Destination (Join-Path $expertRoot ($item.Expert+'.ex5')) -Force
}

if($Stage -eq 'Development'){
    $period=@{From='2024.09.01';To='2025.08.31';Model=1}
    $cases=foreach($item in $items){foreach($session in $sessions){
        [pscustomobject]@{Item=$item;Variant=$session.Id;Session=$session.Value;Dynamic=$false}
    }}
}else{
    $period=@{From='2025.09.01';To='2026.08.31';Model=0}
    $selectionPath=Join-Path $researchRoot 'selection.json'
    if(-not(Test-Path -LiteralPath $selectionPath)){throw 'Run Development first; selection.json is missing.'}
    $selection=Get-Content -Raw -LiteralPath $selectionPath | ConvertFrom-Json
    $cases=foreach($item in $items){
        $pick=$selection | Where-Object ea_id -eq $item.Id | Select-Object -First 1
        if($null -eq $pick){throw "No session selection for $($item.Id)"}
        @(
          [pscustomobject]@{Item=$item;Variant='current';Session=0;Dynamic=$false},
          [pscustomobject]@{Item=$item;Variant='dynamic-only';Session=0;Dynamic=$true},
          [pscustomobject]@{Item=$item;Variant=('session-'+$pick.session);Session=[int]$pick.session_value;Dynamic=$false},
          [pscustomobject]@{Item=$item;Variant=('session-'+$pick.session+'-dynamic');Session=[int]$pick.session_value;Dynamic=$true}
        )
    }
}

function BoolText([bool]$value){if($value){'true'}else{'false'}}
function Upsert-Input([string]$text,[string]$key,[string]$value){
    $pattern='(?m)^'+[regex]::Escape($key)+'=.*$'
    if([regex]::IsMatch($text,$pattern)){return [regex]::Replace($text,$pattern,($key+'='+$value))}
    return $text.TrimEnd()+"`r`n"+$key+'='+$value+"`r`n"
}

$manifest=[Collections.Generic.List[object]]::new()
$index=0
foreach($case in $cases){
    $index++
    $item=$case.Item
    $caseId=($item.Id+'__'+$case.Variant).ToLowerInvariant()
    $setName=('DTS {0} {1} {2}.set' -f $Stage.ToUpperInvariant(),$item.Id,$case.Variant)
    $setText=Get-Content -Raw -LiteralPath (Join-Path $packageRoot $item.Set)
    $setText=Upsert-Input $setText 'InpUseDynamicTrailingSL' (BoolText $case.Dynamic)
    $setText=Upsert-Input $setText 'InpDynamicTriggerFraction' '0.50'
    $setText=Upsert-Input $setText 'InpDynamicLockFraction' '0.20'
    $setText=Upsert-Input $setText 'InpResearchSession' ([string]$case.Session)
    # Exness tester bars in this synchronized history are UTC.
    $setText=Upsert-Input $setText 'InpResearchBrokerUtcOffsetMinutes' '0'
    [IO.File]::WriteAllText((Join-Path $setRoot $setName),$setText,[Text.UTF8Encoding]::new($false))
    [IO.File]::WriteAllText((Join-Path $localSetRoot $setName),$setText,[Text.UTF8Encoding]::new($false))

    $configPath=Join-Path $configRoot ($caseId+'.ini')
    $reportPath=Join-Path $testerReportRoot ($caseId+'.htm')
    $completedReportPath=Join-Path $outputRoot ($caseId+'.htm')
    $relativeReport='reports\{0}\{1}.htm' -f $runSlug,$caseId
    $config=@"
[Common]
Login=$testerLogin
Server=$testerServer

[Tester]
Expert=$expertFolder\$($item.Expert)
ExpertParameters=$setName
Symbol=$($item.Symbol)
Period=$($item.Period)
Login=$testerLogin
Deposit=10000
Currency=USD
Leverage=1:2000
Model=$($period.Model)
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
    if(Test-Path -LiteralPath $completedReportPath){
        Write-Host ('SKIP COMPLETED {0} / {1} / {2}' -f $item.Label,$item.Symbol,$case.Variant) -ForegroundColor DarkGray
        $manifest.Add([pscustomobject]@{CaseId=$caseId;EaId=$item.Id;Label=$item.Label;Symbol=$item.Symbol;Period=$item.Period;Variant=$case.Variant;SessionValue=$case.Session;Dynamic=[bool]$case.Dynamic;Stage=$Stage;From=$period.From;To=$period.To;Model=$period.Model;Report=$completedReportPath})
        continue
    }
    Get-ChildItem -LiteralPath $testerReportRoot -Filter ($caseId+'*') -ErrorAction SilentlyContinue | Remove-Item -Force
    Write-Host ('START {0} / {1} / {2}' -f $item.Label,$item.Symbol,$case.Variant) -ForegroundColor Cyan
    $process=Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"'+$configPath+'"')) -PassThru -WindowStyle Hidden
    try{Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop}
    catch{Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue;throw "TIMEOUT $caseId"}
    if(-not(Test-Path -LiteralPath $reportPath)){throw "NO REPORT $caseId"}
    Get-ChildItem -LiteralPath $testerReportRoot -Filter ($caseId+'*') | Copy-Item -Destination $outputRoot -Force
    $manifest.Add([pscustomobject]@{CaseId=$caseId;EaId=$item.Id;Label=$item.Label;Symbol=$item.Symbol;Period=$item.Period;Variant=$case.Variant;SessionValue=$case.Session;Dynamic=[bool]$case.Dynamic;Stage=$Stage;From=$period.From;To=$period.To;Model=$period.Model;Report=(Join-Path $outputRoot ($caseId+'.htm'))})
    Start-Sleep -Milliseconds 750
}
$manifest | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $outputRoot 'manifest.json') -Encoding utf8
$python=(Get-Command python.exe -ErrorAction Stop).Source
& $python (Join-Path $researchRoot 'Analyze-Reports.py') $Stage
if($LASTEXITCODE -ne 0){throw 'Report analysis failed.'}
Write-Host ('Completed '+$Stage+' tests.') -ForegroundColor Green
