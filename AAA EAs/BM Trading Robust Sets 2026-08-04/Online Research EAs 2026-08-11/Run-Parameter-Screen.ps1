[CmdletBinding()]
param(
    [int]$TimeoutSeconds = 600,
    [string]$FromDate = '2023.08.10',
    [string]$ToDate = '2025.08.06',
    [int]$Model = 1
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$researchRoot=$PSScriptRoot
$packageRoot=Split-Path -Parent $researchRoot
$testerRoot=Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'
$terminal=Join-Path $testerRoot 'terminal64.exe'
$setRoot=Join-Path $testerRoot 'MQL5\Profiles\Tester'
$configRoot=Join-Path $testerRoot 'backtest-configs\online-research-screen-20260811'
$reportRoot=Join-Path $testerRoot 'reports\online-research-screen-20260811'
$outputRoot=Join-Path $researchRoot 'Backtest Reports\Training Screen'
foreach($path in @($setRoot,$configRoot,$reportRoot,$outputRoot)){[void](New-Item -ItemType Directory -Path $path -Force)}

function Set-InputValue {
    param([string]$Text,[string]$Name,[object]$Value)
    $pattern='(?m)^'+[regex]::Escape($Name)+'=[^\r\n]*$'
    if(-not [regex]::IsMatch($Text,$pattern)){throw "Input $Name not found."}
    return [regex]::Replace($Text,$pattern,($Name+'='+[string]$Value),1)
}

$cases=New-Object System.Collections.Generic.List[object]
function Add-ResearchCase {
    param([string]$Slug,[string]$Label,[string]$Expert,[string]$BaseSet,[string]$Symbol,[string]$Period,[hashtable]$Values)
    $cases.Add([pscustomobject]@{Slug=$Slug;Label=$Label;Expert=$Expert;BaseSet=$BaseSet;Symbol=$Symbol;Period=$Period;Values=$Values})
}

$xau=@(
 @('x00','published',@{}),
 @('x01','no ATR increment, PB3/W3',@{InpUseATRIncrementFilter='false';InpBreakoutWindowBars=3}),
 @('x02','no ATR increment, PB3/W6',@{InpUseATRIncrementFilter='false';InpBreakoutWindowBars=6}),
 @('x03','PB2/W3, SL3/TP5',@{InpUseATRIncrementFilter='false';InpBearishPullbackBars=2;InpBreakoutWindowBars=3;InpStopATRMultiplier=3;InpTargetATRMultiplier=5}),
 @('x04','PB2/W6, SL3/TP6',@{InpUseATRIncrementFilter='false';InpBearishPullbackBars=2;InpBreakoutWindowBars=6;InpStopATRMultiplier=3;InpTargetATRMultiplier=6}),
 @('x05','PB1/W3, SL2/TP4',@{InpUseATRIncrementFilter='false';InpBearishPullbackBars=1;InpBreakoutWindowBars=3;InpStopATRMultiplier=2;InpTargetATRMultiplier=4}),
 @('x06','PB1/W6, SL2.5/TP5',@{InpUseATRIncrementFilter='false';InpBearishPullbackBars=1;InpBreakoutWindowBars=6;InpStopATRMultiplier=2.5;InpTargetATRMultiplier=5}),
 @('x07','PB2/W3, mild ATR increment',@{InpBearishPullbackBars=2;InpBreakoutWindowBars=3;InpMinATRIncrement=0;InpMaxATRIncrement=0.8;InpStopATRMultiplier=3;InpTargetATRMultiplier=5}),
 @('x08','EMA10/30 trend100 PB2',@{InpUseATRIncrementFilter='false';InpFastEMAPeriod=10;InpSlowEMAPeriod=30;InpBearishPullbackBars=2;InpBreakoutWindowBars=3;InpStopATRMultiplier=3;InpTargetATRMultiplier=5}),
 @('x09','EMA20/50 trend100 PB2',@{InpUseATRIncrementFilter='false';InpFastEMAPeriod=20;InpSlowEMAPeriod=50;InpBearishPullbackBars=2;InpBreakoutWindowBars=3;InpStopATRMultiplier=3;InpTargetATRMultiplier=5}),
 @('x10','EMA10/24 trend50 PB2',@{InpUseATRIncrementFilter='false';InpFastEMAPeriod=10;InpSlowEMAPeriod=24;InpTrendEMAPeriod=50;InpBearishPullbackBars=2;InpBreakoutWindowBars=3;InpStopATRMultiplier=3;InpTargetATRMultiplier=5}),
 @('x11','EMA14/36 trend200 PB3',@{InpUseATRIncrementFilter='false';InpFastEMAPeriod=14;InpSlowEMAPeriod=36;InpTrendEMAPeriod=200;InpBreakoutWindowBars=6;InpStopATRMultiplier=4;InpTargetATRMultiplier=7})
)
foreach($v in $xau){Add-ResearchCase $v[0] ('XAU '+$v[1]) 'Research XAU Pullback Window EA' 'BASELINE - XAU Pullback M5 - 1pct.set' 'XAUUSD' 'M5' $v[2]}

$keltner=@(
 @('k00','250/2.5/175/2.0',@{}),
 @('k01','100/1.0/50/1.5',@{InpKeltnerMAPeriod=100;InpKeltnerATRMultiplier=1;InpExitMAPeriod=50;InpStopATRMultiplier=1.5}),
 @('k02','100/1.5/50/2.0',@{InpKeltnerMAPeriod=100;InpKeltnerATRMultiplier=1.5;InpExitMAPeriod=50}),
 @('k03','150/1.5/75/1.5',@{InpKeltnerMAPeriod=150;InpKeltnerATRMultiplier=1.5;InpExitMAPeriod=75;InpStopATRMultiplier=1.5}),
 @('k04','150/2.0/100/2.0',@{InpKeltnerMAPeriod=150;InpKeltnerATRMultiplier=2;InpExitMAPeriod=100}),
 @('k05','200/1.5/100/1.5',@{InpKeltnerMAPeriod=200;InpKeltnerATRMultiplier=1.5;InpExitMAPeriod=100;InpStopATRMultiplier=1.5}),
 @('k06','200/2.0/125/2.0',@{InpKeltnerMAPeriod=200;InpKeltnerATRMultiplier=2;InpExitMAPeriod=125}),
 @('k07','250/1.5/125/1.5',@{InpKeltnerATRMultiplier=1.5;InpExitMAPeriod=125;InpStopATRMultiplier=1.5}),
 @('k08','250/2.0/150/2.0',@{InpKeltnerATRMultiplier=2;InpExitMAPeriod=150}),
 @('k09','100/2.0/100/1.5',@{InpKeltnerMAPeriod=100;InpKeltnerATRMultiplier=2;InpExitMAPeriod=100;InpStopATRMultiplier=1.5}),
 @('k10','150/2.5/150/2.0',@{InpKeltnerMAPeriod=150;InpExitMAPeriod=150}),
 @('k11','published long-only',@{InpEnableShort='false'})
)
foreach($symbol in @('EURUSD','GBPUSD','USDCAD','NZDUSD')){
 foreach($v in $keltner){Add-ResearchCase (($symbol.ToLower())+'-'+$v[0]) ("Keltner $symbol "+$v[1]) 'Research FX Keltner Breakout EA' 'BASELINE - FX Keltner D1 - 1pct.set' $symbol 'D1' $v[2]}
}

$donchian=@(
 @('d00','published',@{}),
 @('d01','L20 both 1 unit',@{InpEntryLength=20;InpMaximumUnits=1}),
 @('d02','L20 long 4 units',@{InpEntryLength=20;InpEnableShort='false'}),
 @('d03','L40 long 4 units',@{InpEntryLength=40;InpEnableShort='false'}),
 @('d04','L55 long 1 unit',@{InpEnableShort='false';InpMaximumUnits=1}),
 @('d05','L70 long 4 units',@{InpEntryLength=70;InpEnableShort='false'}),
 @('d06','L40 both 2 units',@{InpEntryLength=40;InpMaximumUnits=2}),
 @('d07','L70 both 2 units',@{InpEntryLength=70;InpMaximumUnits=2}),
 @('d08','L40 long, stop3N/add1N',@{InpEntryLength=40;InpEnableShort='false';InpInitialStopATR=3;InpAddEveryATR=1}),
 @('d09','L20 long, stop1.5N',@{InpEntryLength=20;InpEnableShort='false';InpInitialStopATR=1.5;InpChandelierATR=2.5})
)
foreach($v in $donchian){
 Add-ResearchCase ('ustec-'+$v[0]) ('USTEC Alt22 '+$v[1]) 'Research Donchian Index EA' 'BASELINE - USTEC Alt22 D1 - 1pct per unit.set' 'USTEC' 'D1' $v[2]
 Add-ResearchCase ('us500-'+$v[0]) ('US500 Alt31 '+$v[1]) 'Research Donchian Index EA' 'BASELINE - US500 Alt31 D1 - fractional.set' 'US500' 'D1' $v[2]
}

$btc=@(
 @('b00','published seed',@{}),
 @('b01','long 5/20 TP3 SL3',@{InpEnableShort='false';InpLongFastSMA=5;InpLongSlowSMA=20}),
 @('b02','long 10/30 TP5 SL4',@{InpEnableShort='false';InpLongSlowSMA=30;InpLongTakeProfitFactor=1.05;InpLongStopLossFactor=0.96}),
 @('b03','long 10/50 TP8 SL6',@{InpEnableShort='false';InpLongSlowSMA=50;InpLongTakeProfitFactor=1.08;InpLongStopLossFactor=0.94}),
 @('b04','long 20/80 TP10 SL6',@{InpEnableShort='false';InpLongFastSMA=20;InpLongSlowSMA=80;InpLongTakeProfitFactor=1.10;InpLongStopLossFactor=0.94}),
 @('b05','both 5/30 and 10/50',@{InpLongFastSMA=5;InpLongSlowSMA=30;InpShortFastSMA=10;InpShortSlowSMA=50;InpLongTakeProfitFactor=1.05;InpLongStopLossFactor=0.96;InpShortTakeProfitFactor=0.96;InpShortStopLossFactor=1.05}),
 @('b06','both 10/50 and 20/80',@{InpLongSlowSMA=50;InpShortFastSMA=20;InpLongTakeProfitFactor=1.08;InpLongStopLossFactor=0.94;InpShortTakeProfitFactor=0.94;InpShortStopLossFactor=1.06}),
 @('b07','long 5/50 TP2 SL2',@{InpEnableShort='false';InpLongFastSMA=5;InpLongSlowSMA=50;InpLongTakeProfitFactor=1.02;InpLongStopLossFactor=0.98}),
 @('b08','long 20/100 TP15 SL10',@{InpEnableShort='false';InpLongFastSMA=20;InpLongSlowSMA=100;InpLongTakeProfitFactor=1.15;InpLongStopLossFactor=0.90}),
 @('b09','both 20/80 and 10/40',@{InpLongFastSMA=20;InpLongSlowSMA=80;InpShortFastSMA=10;InpShortSlowSMA=40;InpLongTakeProfitFactor=1.08;InpLongStopLossFactor=0.94;InpShortTakeProfitFactor=0.94;InpShortStopLossFactor=1.06}),
 @('b10','long 50/150 TP20 SL10',@{InpEnableShort='false';InpLongFastSMA=50;InpLongSlowSMA=150;InpLongTakeProfitFactor=1.20;InpLongStopLossFactor=0.90}),
 @('b11','both fast 5/15',@{InpLongFastSMA=5;InpLongSlowSMA=15;InpShortFastSMA=5;InpShortSlowSMA=15;InpLongTakeProfitFactor=1.03;InpLongStopLossFactor=0.97;InpShortTakeProfitFactor=0.97;InpShortStopLossFactor=1.03})
)
foreach($v in $btc){Add-ResearchCase $v[0] ('BTC '+$v[1]) 'Research BTC Four SMA EA' 'BASELINE - BTC Four SMA M5 - 1pct.set' 'BTCUSD' 'M5' $v[2]}

$us30=@(
 @('u00','published core',@{}),
 @('u01','impulse0.5 stop0.5 RR1.5',@{InpImpulseBodyATR=0.5;InpStopBeyondZoneATR=0.5;InpRewardRisk=1.5}),
 @('u02','impulse0.5 stop1 RR2',@{InpImpulseBodyATR=0.5}),
 @('u03','impulse0.75 stop0.75 RR2',@{InpImpulseBodyATR=0.75;InpStopBeyondZoneATR=0.75}),
 @('u04','impulse1 stop0.5 RR2.5',@{InpStopBeyondZoneATR=0.5;InpRewardRisk=2.5}),
 @('u05','impulse1 stop1 RR3',@{InpRewardRisk=3}),
 @('u06','impulse1.5 stop1 RR2',@{InpImpulseBodyATR=1.5}),
 @('u07','impulse1.5 stop1 RR3',@{InpImpulseBodyATR=1.5;InpRewardRisk=3}),
 @('u08','impulse2 stop1 RR2',@{InpImpulseBodyATR=2}),
 @('u09','impulse2 stop1.5 RR3',@{InpImpulseBodyATR=2;InpStopBeyondZoneATR=1.5;InpRewardRisk=3}),
 @('u10','NY overlap 12-16 UTC',@{InpSessionStartUTC=12}),
 @('u11','US morning 13-17 UTC',@{InpSessionStartUTC=13;InpSessionEndUTC=17;InpRewardRisk=2.5})
)
foreach($v in $us30){Add-ResearchCase $v[0] ('US30 '+$v[1]) 'Research US30 Supply Demand ATR EA' 'BASELINE - US30 Supply Demand H1 - 1pct.set' 'US30' 'H1' $v[2]}

foreach($case in $cases){
 $setText=Get-Content -Raw -LiteralPath (Join-Path $researchRoot ('Sets\'+$case.BaseSet))
 foreach($key in $case.Values.Keys){$setText=Set-InputValue $setText $key $case.Values[$key]}
 $setName='SCREEN '+$case.Slug+'.set'
 [IO.File]::WriteAllText((Join-Path $setRoot $setName),$setText,[Text.UTF8Encoding]::new($false))
 $configPath=Join-Path $configRoot ($case.Slug+'.ini')
 $testerReport=Join-Path $reportRoot ($case.Slug+'.htm')
 $relativeReport='reports\online-research-screen-20260811\'+$case.Slug+'.htm'
 $config=@"
[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=Online Research 2026-08-11\$($case.Expert)
ExpertParameters=$setName
Symbol=$($case.Symbol)
Period=$($case.Period)
Login=472334559
Deposit=10000
Currency=USD
Leverage=1:2000
Model=$Model
ExecutionMode=1
Optimization=0
FromDate=$FromDate
ToDate=$ToDate
ForwardMode=0
Report=$relativeReport
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"@
 [IO.File]::WriteAllText($configPath,$config,[Text.UTF8Encoding]::new($true))
 Remove-Item -LiteralPath $testerReport -Force -ErrorAction SilentlyContinue
 Write-Host ("START {0}" -f $case.Label) -ForegroundColor Cyan
 $process=Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"'+$configPath+'"')) -PassThru -WindowStyle Hidden
 try{Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop}catch{Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue;throw "$($case.Label) timed out."}
 if(-not (Test-Path -LiteralPath $testerReport)){Write-Warning "$($case.Label) did not create a report";continue}
 Copy-Item -LiteralPath $testerReport -Destination (Join-Path $outputRoot ($case.Slug+'.htm')) -Force
 Write-Host ("DONE  {0}" -f $case.Label) -ForegroundColor Green
}
$cases | Select-Object Slug,Label,Expert,BaseSet,Symbol,Period,Values | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $outputRoot 'manifest.json') -Encoding utf8
Write-Host ("Completed {0} training screens." -f $cases.Count) -ForegroundColor Green
