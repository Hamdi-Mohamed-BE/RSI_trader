[CmdletBinding()]
param(
    [string]$DevelopmentFrom='2024.08.29',[string]$DevelopmentTo='2025.08.28',
    [string]$LockedFrom='2025.08.29',[string]$LockedTo='2026.08.28',[int]$TimeoutSeconds=1200
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$researchRoot=$PSScriptRoot
$packageRoot=Split-Path -Parent $researchRoot
$testerRoot=Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'
$terminal=Join-Path $testerRoot 'terminal64.exe'
$expertFolder='AAA Research\Crypto Hybrid Edge'
$expertRoot=Join-Path (Join-Path $testerRoot 'MQL5\Experts') $expertFolder
$testerSetRoot=Join-Path $testerRoot 'MQL5\Profiles\Tester'
$configRoot=Join-Path $testerRoot 'backtest-configs\crypto-hybrid-20260830'
$testerReportRoot=Join-Path $testerRoot 'reports\crypto-hybrid-20260830'
$outputRoot=Join-Path $researchRoot 'Backtest Reports'
$developmentOutput=Join-Path $outputRoot 'Development 2024-2025'
$lockedOutput=Join-Path $outputRoot 'Locked 2025-2026'
$selectedSetRoot=Join-Path $researchRoot 'Sets'
$activeConfigRoot='C:\Users\hama101\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\config'
$isolatedConfigRoot=Join-Path $testerRoot 'Config'
foreach($path in @($expertRoot,$testerSetRoot,$configRoot,$testerReportRoot,$developmentOutput,$lockedOutput,$selectedSetRoot,$isolatedConfigRoot)){
    [void](New-Item -ItemType Directory -Path $path -Force)
}
foreach($name in @('accounts.dat','servers.dat','common.ini')){Copy-Item -LiteralPath (Join-Path $activeConfigRoot $name) -Destination (Join-Path $isolatedConfigRoot $name) -Force}
$compiledSource=Join-Path $researchRoot 'EA\Crypto Momentum Reversal Hybrid EA.ex5'
if(-not(Test-Path -LiteralPath $compiledSource)){throw "Compile the EA first: $compiledSource"}
Copy-Item -LiteralPath $compiledSource -Destination (Join-Path $expertRoot 'Crypto Momentum Reversal Hybrid EA.ex5') -Force
$symbols=@([pscustomobject]@{Symbol='BTCUSD';Slug='btcusd'},[pscustomobject]@{Symbol='ETHUSD';Slug='ethusd'})
$variants=@(
 [pscustomobject]@{Id='trend-all-r05';Mode=0;RR=.5;Session=$false;Bands=2.5;RevTrend=$false;Momentum=$true;Volume=1.1;MinBody=.7},
 [pscustomobject]@{Id='trend-all-r07';Mode=0;RR=.7;Session=$false;Bands=2.5;RevTrend=$false;Momentum=$true;Volume=1.1;MinBody=.7},
 [pscustomobject]@{Id='trend-all-r10';Mode=0;RR=1.;Session=$false;Bands=2.5;RevTrend=$false;Momentum=$true;Volume=1.1;MinBody=.7},
 [pscustomobject]@{Id='trend-liquid-r07';Mode=0;RR=.7;Session=$true;Bands=2.5;RevTrend=$false;Momentum=$true;Volume=1.1;MinBody=.7},
 [pscustomobject]@{Id='trend-liquid-r10';Mode=0;RR=1.;Session=$true;Bands=2.5;RevTrend=$false;Momentum=$true;Volume=1.1;MinBody=.7},
 [pscustomobject]@{Id='revert-all-r05';Mode=1;RR=.5;Session=$false;Bands=2.5;RevTrend=$false;Momentum=$false;Volume=1.1;MinBody=.7},
 [pscustomobject]@{Id='revert-all-r07';Mode=1;RR=.7;Session=$false;Bands=2.5;RevTrend=$false;Momentum=$false;Volume=1.1;MinBody=.7},
 [pscustomobject]@{Id='revert-all-r10';Mode=1;RR=1.;Session=$false;Bands=2.5;RevTrend=$false;Momentum=$false;Volume=1.1;MinBody=.7},
 [pscustomobject]@{Id='revert-liquid-trend-r05';Mode=1;RR=.5;Session=$true;Bands=2.2;RevTrend=$true;Momentum=$false;Volume=1.1;MinBody=.7},
 [pscustomobject]@{Id='revert-liquid-trend-r07';Mode=1;RR=.7;Session=$true;Bands=2.2;RevTrend=$true;Momentum=$false;Volume=1.1;MinBody=.7},
 [pscustomobject]@{Id='break-liquid-r07';Mode=2;RR=.7;Session=$true;Bands=2.5;RevTrend=$false;Momentum=$false;Volume=1.1;MinBody=.7},
 [pscustomobject]@{Id='break-liquid-r10';Mode=2;RR=1.;Session=$true;Bands=2.5;RevTrend=$false;Momentum=$false;Volume=1.1;MinBody=.7}
)
function BoolText([bool]$Value){
    if($Value){return 'true'}
    return 'false'
}
function Write-SetFile([object]$v,[string]$path,[long]$magic){
$text=@"
InpMode=$($v.Mode)
InpSignalTimeframe=15
InpATRPeriod=14
InpFastEMAPeriod=20
InpSlowEMAPeriod=50
InpRSIPeriod=14
InpBollingerPeriod=20
InpBollingerDeviation=$($v.Bands)
InpDonchianBars=20
InpUseH4Trend=true
InpRequire24HourMomentum=$(BoolText $v.Momentum)
InpPullbackTouchATR=0.20
InpStructureLookbackBars=6
InpRSILow=22.0
InpRSIHigh=78.0
InpReversionWithH1Trend=$(BoolText $v.RevTrend)
InpMinimumBreakoutBodyATR=$($v.MinBody)
InpMinimumVolumeFactor=$($v.Volume)
InpRetestToleranceATR=0.20
InpUseUTCSession=$(BoolText $v.Session)
InpSessionStartHourUTC=7
InpSessionEndHourUTC=21
InpServerUTCOffsetHours=0
InpMaximumTradesPerDay=3
InpMaximumHoldingBars=32
InpRiskPercent=1.0
InpRewardRisk=$($v.RR)
InpStopBufferATR=0.10
InpMinimumStopATR=0.35
InpMaximumStopATR=2.50
InpMoveToBreakEven=false
InpBreakEvenAtR=0.50
InpMaximumSpreadATR=0.08
InpMaximumDeviationPoints=80
InpAllowLong=true
InpAllowShort=true
InpMagic=$magic
"@
[IO.File]::WriteAllText($path,$text.TrimStart(),[Text.UTF8Encoding]::new($false))}
function Run-Case([string]$phase,[object]$symbolCase,[object]$variant,[string]$from,[string]$to,[string]$destination,[int]$sequence){
 $caseId="$($symbolCase.Slug)--$($variant.Id)--$phase";$setName="Crypto-$caseId.set";Write-SetFile $variant (Join-Path $testerSetRoot $setName) (86340000+$sequence);$configPath=Join-Path $configRoot ($caseId+'.ini');$reportRelative='reports\crypto-hybrid-20260830\'+$caseId+'.htm';$reportPath=Join-Path $testerReportRoot ($caseId+'.htm')
 $config=@"
[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=$expertFolder\Crypto Momentum Reversal Hybrid EA
ExpertParameters=$setName
Symbol=$($symbolCase.Symbol)
Period=M15
Login=472334559
Deposit=10000
Currency=USD
Leverage=1:2000
Model=0
ExecutionMode=1
Optimization=0
FromDate=$from
ToDate=$to
ForwardMode=0
Report=$reportRelative
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"@
 [IO.File]::WriteAllText($configPath,$config,[Text.UTF8Encoding]::new($true));Get-ChildItem -LiteralPath $testerReportRoot -Filter ($caseId+'*') -ErrorAction SilentlyContinue|Remove-Item -Force;Write-Host("START {0} {1} {2} | {3} to {4}"-f $phase,$symbolCase.Symbol,$variant.Id,$from,$to)-ForegroundColor Cyan
 $process=Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"'+$configPath+'"')) -PassThru -WindowStyle Hidden
 try{Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop}catch{Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue;throw"MT5 timed out: $caseId"}
 if(-not(Test-Path -LiteralPath $reportPath)){throw"MT5 did not create report: $reportPath"};Get-ChildItem -LiteralPath $testerReportRoot -Filter ($caseId+'*')|Copy-Item -Destination $destination -Force}
$sequence=0
foreach($symbolCase in $symbols){
    foreach($variant in $variants){
        $sequence++
        Run-Case 'development' $symbolCase $variant $DevelopmentFrom $DevelopmentTo $developmentOutput $sequence
    }
}
$python=(Get-Command python.exe -ErrorAction Stop).Source
& $python (Join-Path $researchRoot 'Select-Winners.py') --reports $developmentOutput --output (Join-Path $outputRoot 'selected.json')
if($LASTEXITCODE -ne 0){throw 'Selection failed'}
$selected=Get-Content -LiteralPath (Join-Path $outputRoot 'selected.json') -Raw | ConvertFrom-Json
foreach($symbolCase in $symbols){
    $winnerId=[string]$selected.$($symbolCase.Slug).variant
    $variant=$variants | Where-Object Id -eq $winnerId | Select-Object -First 1
    if(-not $variant){throw "No selected variant for $($symbolCase.Symbol)"}
    $sourceSet=Join-Path $testerSetRoot "Crypto-$($symbolCase.Slug)--$winnerId--development.set"
    Copy-Item -LiteralPath $sourceSet -Destination (Join-Path $selectedSetRoot "$($symbolCase.Symbol) - selected $winnerId.set") -Force
    $sequence++
    Run-Case 'locked' $symbolCase $variant $LockedFrom $LockedTo $lockedOutput $sequence
}
& $python (Join-Path $researchRoot 'Build-Report.py') --development $developmentOutput --locked $lockedOutput --selected (Join-Path $outputRoot 'selected.json') --output $researchRoot
if($LASTEXITCODE -ne 0){throw 'Report build failed'}
Write-Host 'Completed crypto hybrid selection, locked tests, reports and charts.' -ForegroundColor Green
