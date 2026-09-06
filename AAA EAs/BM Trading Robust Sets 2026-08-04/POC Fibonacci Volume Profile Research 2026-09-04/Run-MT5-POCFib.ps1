[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('screen','stop','rr','trailing','session','locked','full')]
    [string]$Phase,
    [int]$TimeoutSeconds=1200,
    [string[]]$OnlySymbols=@(),
    [switch]$KeepOutput
)

Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'

$researchRoot=$PSScriptRoot
$packageRoot=Split-Path -Parent $researchRoot
$testerRoot=Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'
$terminal=Join-Path $testerRoot 'terminal64.exe'
$expertFolder='AAA Research\POC Fibonacci Volume Profile 20260904'
$expertName='POC Fibonacci Volume Profile EA'
$expertRoot=Join-Path (Join-Path $testerRoot 'MQL5\Experts') $expertFolder
$testerSetRoot=Join-Path $testerRoot 'MQL5\Profiles\Tester'
$configRoot=Join-Path $testerRoot ('backtest-configs\pocfib-'+$Phase)
$testerReportRoot=Join-Path $testerRoot ('reports\pocfib-'+$Phase)
$outputRoot=Join-Path $researchRoot ('Backtest Reports\'+$Phase)
$setsRoot=Join-Path $researchRoot 'Sets'
$isolatedConfigRoot=Join-Path $testerRoot 'Config'
$activeConfigRoot='C:\Users\hama101\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\config'

foreach($path in @($expertRoot,$testerSetRoot,$configRoot,$testerReportRoot,$outputRoot,$setsRoot,$isolatedConfigRoot)){
    [void](New-Item -ItemType Directory -Path $path -Force)
}
if(-not $KeepOutput){Get-ChildItem -LiteralPath $outputRoot -File -ErrorAction SilentlyContinue | Remove-Item -Force}
foreach($name in @('accounts.dat','servers.dat','common.ini')){
    $source=Join-Path $activeConfigRoot $name
    if(Test-Path -LiteralPath $source){Copy-Item -LiteralPath $source -Destination (Join-Path $isolatedConfigRoot $name) -Force}
}
$compiled=Join-Path $researchRoot ('EA\'+$expertName+'.ex5')
if(-not (Test-Path -LiteralPath $compiled)){throw "Missing compiled EA: $compiled"}
Copy-Item -LiteralPath $compiled -Destination (Join-Path $expertRoot ($expertName+'.ex5')) -Force

$symbols=@(
    [pscustomobject]@{Symbol='XAUUSD';Slug='xauusd'},
    [pscustomobject]@{Symbol='XAGUSD';Slug='xagusd'},
    [pscustomobject]@{Symbol='BTCUSD';Slug='btcusd'},
    [pscustomobject]@{Symbol='US30';Slug='us30'},
    [pscustomobject]@{Symbol='USTEC';Slug='ustec'},
    [pscustomobject]@{Symbol='GBPJPY';Slug='gbpjpy'}
)
if($OnlySymbols.Count -gt 0){$symbols=@($symbols | Where-Object {$OnlySymbols -contains $_.Slug})}
if($symbols.Count -eq 0){throw 'No symbols selected.'}

function Default-Config {
    return [ordered]@{
        Entry=0;Days=1;ProfileBars=96;Bins=64;Fib=0.618;FibTolerance=0.50;Tolerance=0.10;MinProfileRange=2.0;RetestBars=16;
        Departure=0.75;MinBody=0.15;CloseLocation=0.60;
        Stop=0;Swing=5;StopATR=1.50;Buffer=0.10;RR=1.50;Trail=0;
        BEAt=1.00;BELock=0.05;DynamicTrigger=0.50;DynamicLock=0.20;TrailStart=1.00;TrailATR=2.00;Hold=96;
        Session=0;AllowLong=$true;AllowShort=$true;MaxTrades=2;Risk=1.00;MaxSpreadATR=0.20;Deviation=80
    }
}

function Apply-Screen([System.Collections.IDictionary]$Config,[string]$Variant){
    switch($Variant){
        'r32-f618' {$Config.ProfileBars=32;$Config.Fib=0.618}
        'r64-f618' {$Config.ProfileBars=64;$Config.Fib=0.618}
        'r96-f382' {$Config.ProfileBars=96;$Config.Fib=0.382}
        'r96-f500' {$Config.ProfileBars=96;$Config.Fib=0.500}
        'r96-f618' {$Config.ProfileBars=96;$Config.Fib=0.618}
        'r96-f705' {$Config.ProfileBars=96;$Config.Fib=0.705}
        'r192-f618' {$Config.ProfileBars=192;$Config.Fib=0.618}
        default {throw "Unknown screen variant: $Variant"}
    }
}

function Apply-Stop([System.Collections.IDictionary]$Config,[string]$Variant){
    switch($Variant){
        'signal' {$Config.Stop=0}
        'atr100' {$Config.Stop=1;$Config.StopATR=1.00}
        'atr150' {$Config.Stop=1;$Config.StopATR=1.50}
        'atr200' {$Config.Stop=1;$Config.StopATR=2.00}
        'swing3' {$Config.Stop=2;$Config.Swing=3}
        'swing5' {$Config.Stop=2;$Config.Swing=5}
        'swing8' {$Config.Stop=2;$Config.Swing=8}
        default {throw "Unknown stop variant: $Variant"}
    }
}

function Apply-RR([System.Collections.IDictionary]$Config,[string]$Variant){
    if($Variant -notmatch '^rr(050|075|100|150|200|300|400|500)$'){throw "Unknown RR variant: $Variant"}
    $Config.RR=[double]$Matches[1]/100.0
}

function Apply-Trailing([System.Collections.IDictionary]$Config,[string]$Variant){
    switch($Variant){
        'none' {$Config.Trail=0}
        'be075' {$Config.Trail=1;$Config.BEAt=0.75}
        'be100' {$Config.Trail=1;$Config.BEAt=1.00}
        'dynamic5020' {$Config.Trail=2}
        'atr100-200' {$Config.Trail=3;$Config.TrailStart=1.00;$Config.TrailATR=2.00}
        'dynamic5020-atr' {$Config.Trail=4;$Config.TrailStart=1.00;$Config.TrailATR=2.00}
        default {throw "Unknown trailing variant: $Variant"}
    }
}

function Apply-Session([System.Collections.IDictionary]$Config,[string]$Variant){
    $Config.Session=switch($Variant){'all'{0};'asia'{1};'london'{2};'newyork'{3};'overlap'{4};default{throw "Unknown session: $Variant"}}
}

function Write-Set([string]$Path,[System.Collections.IDictionary]$C,[long]$Magic){
    $text=@"
InpTimeframe=15
InpConfirmation=$($C.Entry)
InpProfileTimeframe=15
InpProfileLookbackDays=$($C.Days)
InpProfileLookbackBars=$($C.ProfileBars)
InpProfileBins=$($C.Bins)
InpFibonacciRatio=$($C.Fib)
InpFibonacciToleranceATR=$($C.FibTolerance)
InpPOCTouchToleranceATR=$($C.Tolerance)
InpMinimumProfileRangeATR=$($C.MinProfileRange)
InpTrendTimeframe=16385
InpTrendEMAPeriod=50
InpMinimumDepartureATR=$($C.Departure)
InpDepartureLookbackBars=$($C.RetestBars)
InpMinimumBodyATR=$($C.MinBody)
InpMinimumCloseLocation=$($C.CloseLocation)
InpStopMode=$($C.Stop)
InpSwingLookback=$($C.Swing)
InpStopATR=$($C.StopATR)
InpStopBufferATR=$($C.Buffer)
InpRewardRisk=$($C.RR)
InpTrailingMode=$($C.Trail)
InpBreakEvenAtR=$($C.BEAt)
InpBreakEvenLockR=$($C.BELock)
InpDynamicTriggerR=$($C.DynamicTrigger)
InpDynamicLockR=$($C.DynamicLock)
InpATRTrailStartR=$($C.TrailStart)
InpATRTrailDistance=$($C.TrailATR)
InpMaximumHoldingBars=$($C.Hold)
InpSession=$($C.Session)
InpAsiaStartHour=0
InpAsiaEndHour=7
InpLondonStartHour=7
InpLondonEndHour=13
InpNewYorkStartHour=13
InpNewYorkEndHour=21
InpOverlapStartHour=13
InpOverlapEndHour=16
InpAllowLong=$($C.AllowLong.ToString().ToLowerInvariant())
InpAllowShort=$($C.AllowShort.ToString().ToLowerInvariant())
InpMaximumTradesPerDay=$($C.MaxTrades)
InpRiskPercent=$($C.Risk)
InpMaximumSpreadATR=$($C.MaxSpreadATR)
InpMagic=$Magic
InpMaximumDeviationPoints=$($C.Deviation)
"@
    [IO.File]::WriteAllText($Path,$text.TrimStart(),[Text.UTF8Encoding]::new($false))
}

function Run-Case([object]$SymbolCase,[string]$Variant,[System.Collections.IDictionary]$Config,[int]$Sequence,[string]$From,[string]$To,[int]$Model){
    $caseId="$($SymbolCase.Slug)--$Variant--$Phase"
    $setName="POCFib-$caseId.set"
    $savedSet=Join-Path $setsRoot $setName
    Write-Set $savedSet $Config (940410000+$Sequence)
    Copy-Item -LiteralPath $savedSet -Destination (Join-Path $testerSetRoot $setName) -Force
    $configPath=Join-Path $configRoot ($caseId+'.ini')
    $reportRelative='reports\pocfib-'+$Phase+'\'+$caseId+'.htm'
    $reportPath=Join-Path $testerReportRoot ($caseId+'.htm')
    $ini=@"
[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=$expertFolder\$expertName
ExpertParameters=$setName
Symbol=$($SymbolCase.Symbol)
Period=M15
Login=472334559
Deposit=10000
Currency=USD
Leverage=1:2000
Model=$Model
ExecutionMode=1
Optimization=0
FromDate=$From
ToDate=$To
ForwardMode=0
Report=$reportRelative
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"@
    [IO.File]::WriteAllText($configPath,$ini,[Text.UTF8Encoding]::new($true))
    Get-ChildItem -LiteralPath $testerReportRoot -Filter ($caseId+'*') -ErrorAction SilentlyContinue | Remove-Item -Force
    Write-Host ("START {0} {1}" -f $SymbolCase.Symbol,$Variant) -ForegroundColor Cyan
    $process=Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"'+$configPath+'"')) -PassThru -WindowStyle Hidden
    try{Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop}
    catch{Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue;throw "MT5 timed out: $caseId"}
    if(-not (Test-Path -LiteralPath $reportPath)){throw "Missing MT5 report: $reportPath"}
    Get-ChildItem -LiteralPath $testerReportRoot -Filter ($caseId+'*') | Copy-Item -Destination $outputRoot -Force
}

function Read-Winners([string]$Name){
    $path=Join-Path $researchRoot $Name
    if(-not (Test-Path -LiteralPath $path)){throw "Run the previous phase first: $path"}
    return (Get-Content -LiteralPath $path -Raw | ConvertFrom-Json).winners
}

function Build-Selected([object]$SymbolCase,[object]$Screen,[object]$Stop,[object]$RR,[object]$Trailing,[object]$Session){
    $config=Default-Config
    Apply-Screen $config ([string]$Screen.($SymbolCase.Slug).variant)
    Apply-Stop $config ([string]$Stop.($SymbolCase.Slug).variant)
    Apply-RR $config ([string]$RR.($SymbolCase.Slug).variant)
    Apply-Trailing $config ([string]$Trailing.($SymbolCase.Slug).variant)
    Apply-Session $config ([string]$Session.($SymbolCase.Slug).variant)
    return $config
}

$developmentFrom='2023.09.01';$developmentTo='2025.08.31'
$lockedFrom='2025.09.01';$lockedTo='2026.09.01'
$fullFrom='2023.09.01';$fullTo='2026.09.01'
$sequence=0

if($Phase -eq 'screen'){
    foreach($symbol in $symbols){foreach($variant in @('r32-f618','r64-f618','r96-f382','r96-f500','r96-f618','r96-f705','r192-f618')){
        $config=Default-Config;Apply-Screen $config $variant;$sequence++;Run-Case $symbol $variant $config $sequence $developmentFrom $developmentTo 1
    }}
} else {
    $screen=Read-Winners 'screen-selection.json'
    $stop=if($Phase -in @('rr','trailing','session','locked','full')){Read-Winners 'stop-selection.json'}else{$null}
    $rr=if($Phase -in @('trailing','session','locked','full')){Read-Winners 'rr-selection.json'}else{$null}
    $trailing=if($Phase -in @('session','locked','full')){Read-Winners 'trailing-selection.json'}else{$null}
    $session=if($Phase -in @('locked','full')){Read-Winners 'session-selection.json'}else{$null}
    foreach($symbol in $symbols){
        if($Phase -eq 'stop'){
            foreach($variant in @('signal','atr100','atr150','atr200','swing3','swing5','swing8')){
                $config=Default-Config;Apply-Screen $config ([string]$screen.($symbol.Slug).variant);Apply-Stop $config $variant
                $sequence++;Run-Case $symbol $variant $config $sequence $developmentFrom $developmentTo 1
            }
        } elseif($Phase -eq 'rr'){
            foreach($variant in @('rr050','rr075','rr100','rr150','rr200','rr300','rr400','rr500')){
                $config=Default-Config;Apply-Screen $config ([string]$screen.($symbol.Slug).variant);Apply-Stop $config ([string]$stop.($symbol.Slug).variant);Apply-RR $config $variant
                $sequence++;Run-Case $symbol $variant $config $sequence $developmentFrom $developmentTo 1
            }
        } elseif($Phase -eq 'trailing'){
            foreach($variant in @('none','be075','be100','dynamic5020','atr100-200','dynamic5020-atr')){
                $config=Default-Config;Apply-Screen $config ([string]$screen.($symbol.Slug).variant);Apply-Stop $config ([string]$stop.($symbol.Slug).variant);Apply-RR $config ([string]$rr.($symbol.Slug).variant);Apply-Trailing $config $variant
                $sequence++;Run-Case $symbol $variant $config $sequence $developmentFrom $developmentTo 1
            }
        } elseif($Phase -eq 'session'){
            foreach($variant in @('all','asia','london','newyork','overlap')){
                $config=Default-Config;Apply-Screen $config ([string]$screen.($symbol.Slug).variant);Apply-Stop $config ([string]$stop.($symbol.Slug).variant);Apply-RR $config ([string]$rr.($symbol.Slug).variant);Apply-Trailing $config ([string]$trailing.($symbol.Slug).variant);Apply-Session $config $variant
                $sequence++;Run-Case $symbol $variant $config $sequence $developmentFrom $developmentTo 1
            }
        } elseif($Phase -eq 'locked'){
            $baseline=Default-Config;$sequence++;Run-Case $symbol 'baseline' $baseline $sequence $lockedFrom $lockedTo 0
            $optimized=Build-Selected $symbol $screen $stop $rr $trailing $session
            $sequence++;Run-Case $symbol 'optimized' $optimized $sequence $lockedFrom $lockedTo 0
        } elseif($Phase -eq 'full'){
            $optimized=Build-Selected $symbol $screen $stop $rr $trailing $session
            $sequence++;Run-Case $symbol 'optimized' $optimized $sequence $fullFrom $fullTo 0
        }
    }
}

Write-Host "Completed $sequence native MT5 tests for $Phase." -ForegroundColor Green
