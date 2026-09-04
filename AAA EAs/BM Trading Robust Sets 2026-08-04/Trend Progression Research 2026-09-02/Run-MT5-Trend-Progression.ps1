[CmdletBinding()]
param(
    [ValidateSet('screen','stoprr','trailing','session','locked','full')]
    [string]$Phase,
    [int]$TimeoutSeconds=1200,
    [string]$TesterRootOverride='',
    [ValidateSet('core','extension')]
    [string]$Universe='core',
    [string[]]$OnlySymbols=@(),
    [switch]$KeepOutput
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'

$researchRoot=$PSScriptRoot
$packageRoot=Split-Path -Parent $researchRoot
$runId=if($Universe -eq 'core'){$Phase}else{'extension-'+$Phase}
$selectionPrefix=if($Universe -eq 'core'){''}else{'extension-'}
$testerRoot=if([string]::IsNullOrWhiteSpace($TesterRootOverride)){Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'}else{$TesterRootOverride}
$terminal=Join-Path $testerRoot 'terminal64.exe'
$expertFolder='AAA Research\Trend Progression'
$expertRoot=Join-Path (Join-Path $testerRoot 'MQL5\Experts') $expertFolder
$testerSetRoot=Join-Path $testerRoot 'MQL5\Profiles\Tester'
$configRoot=Join-Path $testerRoot ('backtest-configs\trend-progression-'+$runId)
$testerReportRoot=Join-Path $testerRoot ('reports\trend-progression-'+$runId)
$outputRoot=Join-Path $researchRoot ('Backtest Reports\'+$runId)
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
$compiled=Join-Path $researchRoot 'EA\Trend Progression EA.ex5'
if(-not (Test-Path -LiteralPath $compiled)){throw "Missing compiled EA: $compiled"}
Copy-Item -LiteralPath $compiled -Destination (Join-Path $expertRoot 'Trend Progression EA.ex5') -Force

$symbols=if($Universe -eq 'core'){@(
    [pscustomobject]@{Symbol='USTEC';Slug='ustec'},
    [pscustomobject]@{Symbol='BTCUSD';Slug='btcusd'},
    [pscustomobject]@{Symbol='XAUUSD';Slug='xauusd'}
)}else{@(
    [pscustomobject]@{Symbol='XAGUSD';Slug='xagusd'},
    [pscustomobject]@{Symbol='ETHUSD';Slug='ethusd'},
    [pscustomobject]@{Symbol='EURUSD';Slug='eurusd'},
    [pscustomobject]@{Symbol='GBPUSD';Slug='gbpusd'},
    [pscustomobject]@{Symbol='USDJPY';Slug='usdjpy'},
    [pscustomobject]@{Symbol='GBPJPY';Slug='gbpjpy'}
)}
if($OnlySymbols.Count -gt 0){$symbols=@($symbols | Where-Object {$OnlySymbols -contains $_.Slug})}
if($symbols.Count -eq 0){throw 'No symbols selected.'}

function Default-Config {
    return [ordered]@{
        Risk=1.0;AllowLong=$true;AllowShort=$true;FastEMA=20;SlowEMA=50;Slope=3;MomentumBars=24;MomentumATR=0.50;
        RangeBars=48;RangeMinimum=0.65;UseRange=$false;Pullback=0;PullbackTolerance=0.25;Confirmation=0;
        MinimumBodyATR=0.05;MaximumSignalATR=2.50;StopMode=1;Swing=5;StopATR=2.0;BufferATR=0.10;RR=1.50;
        BreakEven=$false;BEAt=1.0;BELock=0.05;Trail=$false;TrailStart=1.0;TrailATR=2.0;
        Dynamic=$false;DynamicTrigger=0.50;DynamicLock=0.20;MaxHold=0;Session=0;
        Regime=$false;RegimeReturn=20;RegimeThreshold=2.0;RegimeTraining=500;RegimeProbability=0.40;
        MaxSpread=0;Deviation=80
    }
}

function Apply-Structure([System.Collections.IDictionary]$Config,[string]$Variant){
    switch($Variant){
        'base' {}
        'ema50' {$Config.Pullback=1}
        'range' {$Config.UseRange=$true}
        'markov' {$Config.Regime=$true}
        'longonly' {$Config.AllowShort=$false}
        default {throw "Unknown structure variant: $Variant"}
    }
}

function Apply-StopRR([System.Collections.IDictionary]$Config,[string]$Variant){
    if($Variant -notmatch '^(signal|swing|atr)-rr(050|075|100|150|200|300|400)$'){throw "Unknown stop/RR: $Variant"}
    $Config.StopMode=switch($Matches[1]){'signal'{0};'swing'{1};'atr'{2}}
    $Config.RR=[double]$Matches[2]/100.0
}

function Apply-Trailing([System.Collections.IDictionary]$Config,[string]$Variant){
    switch($Variant){
        'none' {}
        'be075' {$Config.BreakEven=$true;$Config.BEAt=0.75}
        'be100' {$Config.BreakEven=$true;$Config.BEAt=1.00}
        'trail075-atr15' {$Config.Trail=$true;$Config.TrailStart=0.75;$Config.TrailATR=1.50}
        'trail100-atr20' {$Config.Trail=$true;$Config.TrailStart=1.00;$Config.TrailATR=2.00}
        'dynamic5020' {$Config.Dynamic=$true}
        'dynamic5020-trail' {$Config.Dynamic=$true;$Config.Trail=$true;$Config.TrailStart=1.00;$Config.TrailATR=2.00}
        default {throw "Unknown trailing variant: $Variant"}
    }
}

function Apply-Session([System.Collections.IDictionary]$Config,[string]$Variant){
    $Config.Session=switch($Variant){'all'{0};'asia'{1};'london'{2};'newyork'{3};'overlap'{4};default{throw "Unknown session: $Variant"}}
}

function Write-Set([string]$Path,[System.Collections.IDictionary]$C,[long]$Magic){
    $text=@"
InpRiskPercent=$($C.Risk)
InpAllowLong=$($C.AllowLong.ToString().ToLower())
InpAllowShort=$($C.AllowShort.ToString().ToLower())
InpFastEMA=$($C.FastEMA)
InpSlowEMA=$($C.SlowEMA)
InpSlopeLookback=$($C.Slope)
InpMomentumLookback=$($C.MomentumBars)
InpMinimumMomentumATR=$($C.MomentumATR)
InpRangeLookback=$($C.RangeBars)
InpRangePositionMinimum=$($C.RangeMinimum)
InpUseRangeFilter=$($C.UseRange.ToString().ToLower())
InpPullbackMode=$($C.Pullback)
InpPullbackToleranceATR=$($C.PullbackTolerance)
InpConfirmation=$($C.Confirmation)
InpMinimumBodyATR=$($C.MinimumBodyATR)
InpMaximumSignalATR=$($C.MaximumSignalATR)
InpStopMode=$($C.StopMode)
InpSwingLookback=$($C.Swing)
InpStopATR=$($C.StopATR)
InpStopBufferATR=$($C.BufferATR)
InpRewardRisk=$($C.RR)
InpUseBreakEven=$($C.BreakEven.ToString().ToLower())
InpBreakEvenAtR=$($C.BEAt)
InpBreakEvenLockR=$($C.BELock)
InpUseATRTrailing=$($C.Trail.ToString().ToLower())
InpTrailStartR=$($C.TrailStart)
InpTrailATR=$($C.TrailATR)
InpUseDynamicM15Stop=$($C.Dynamic.ToString().ToLower())
InpDynamicTriggerR=$($C.DynamicTrigger)
InpDynamicLockR=$($C.DynamicLock)
InpMaximumHoldingBars=$($C.MaxHold)
InpSession=$($C.Session)
InpUseRegimeGate=$($C.Regime.ToString().ToLower())
InpRegimeReturnBars=$($C.RegimeReturn)
InpRegimeThresholdATR=$($C.RegimeThreshold)
InpRegimeTrainingBars=$($C.RegimeTraining)
InpRegimeMinimumProbability=$($C.RegimeProbability)
InpMaximumSpreadPoints=$($C.MaxSpread)
InpMaximumDeviationPoints=$($C.Deviation)
InpMagic=$Magic
"@
    [IO.File]::WriteAllText($Path,$text.TrimStart(),[Text.UTF8Encoding]::new($false))
}

function Run-Case([object]$SymbolCase,[string]$Timeframe,[string]$Variant,[System.Collections.IDictionary]$Config,[int]$Sequence,[string]$From,[string]$To){
    $caseId="$($SymbolCase.Slug)--$($Timeframe.ToLower())--$Variant--$Phase"
    $setName="TrendProgression-$caseId.set"
    $savedSet=Join-Path $setsRoot $setName
    Write-Set $savedSet $Config (926300000+$Sequence)
    Copy-Item -LiteralPath $savedSet -Destination (Join-Path $testerSetRoot $setName) -Force
    $configPath=Join-Path $configRoot ($caseId+'.ini')
    $reportRelative='reports\trend-progression-'+$runId+'\'+$caseId+'.htm'
    $reportPath=Join-Path $testerReportRoot ($caseId+'.htm')
    $ini=@"
[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=$expertFolder\Trend Progression EA
ExpertParameters=$setName
Symbol=$($SymbolCase.Symbol)
Period=$Timeframe
Login=472334559
Deposit=10000
Currency=USD
Leverage=1:2000
Model=0
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
    Write-Host ("START {0} {1} {2}" -f $SymbolCase.Symbol,$Timeframe,$Variant) -ForegroundColor Cyan
    $process=Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"'+$configPath+'"')) -PassThru -WindowStyle Hidden
    try{Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop}
    catch{Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue;throw "MT5 timed out: $caseId"}
    if(-not (Test-Path -LiteralPath $reportPath)){throw "Missing MT5 report: $reportPath"}
    Get-ChildItem -LiteralPath $testerReportRoot -Filter ($caseId+'*') | Copy-Item -Destination $outputRoot -Force
}

function Read-Winners([string]$Name){
    $path=Join-Path $researchRoot $Name
    if(-not (Test-Path -LiteralPath $path)){throw "Run and analyze the prior phase first: $path"}
    return (Get-Content -LiteralPath $path -Raw | ConvertFrom-Json).winners
}

$sequence=0
$developmentFrom='2023.09.01';$developmentTo='2025.08.31'
$lockedFrom='2025.09.01';$lockedTo='2026.09.01'
$fullFrom='2023.09.01';$fullTo='2026.09.01'

if($Phase -eq 'screen'){
    $structureVariants=if($Universe -eq 'core'){@('base','ema50','range','markov','longonly')}else{@('longonly')}
    foreach($s in $symbols){foreach($tf in @('M15','H1','H4')){foreach($variant in $structureVariants){
        $c=Default-Config;Apply-Structure $c $variant;$sequence++;Run-Case $s $tf $variant $c $sequence $developmentFrom $developmentTo
    }}}
} else {
    $screen=Read-Winners ($selectionPrefix+'screen-selection.json')
    $stop=if($Phase -in @('trailing','session','locked','full')){Read-Winners ($selectionPrefix+'stoprr-selection.json')}else{$null}
    $trail=if($Phase -in @('session','locked','full')){Read-Winners ($selectionPrefix+'trailing-selection.json')}else{$null}
    $session=if($Phase -in @('locked','full')){Read-Winners ($selectionPrefix+'session-selection.json')}else{$null}
    foreach($s in $symbols){
        $selected=$screen.($s.Slug);$tf=[string]$selected.timeframe;$structure=[string]$selected.variant
        if($Phase -eq 'stoprr'){
            foreach($variant in @('signal-rr050','signal-rr075','signal-rr100','signal-rr150','signal-rr200','signal-rr300','signal-rr400','swing-rr050','swing-rr075','swing-rr100','swing-rr150','swing-rr200','swing-rr300','swing-rr400','atr-rr050','atr-rr075','atr-rr100','atr-rr150','atr-rr200','atr-rr300','atr-rr400')){
                $c=Default-Config;Apply-Structure $c $structure;Apply-StopRR $c $variant;$sequence++;Run-Case $s $tf $variant $c $sequence $developmentFrom $developmentTo
            }
        } elseif($Phase -eq 'trailing'){
            foreach($variant in @('none','be075','be100','trail075-atr15','trail100-atr20','dynamic5020','dynamic5020-trail')){
                $c=Default-Config;Apply-Structure $c $structure;Apply-StopRR $c ([string]$stop.($s.Slug).variant);Apply-Trailing $c $variant;$sequence++;Run-Case $s $tf $variant $c $sequence $developmentFrom $developmentTo
            }
        } elseif($Phase -eq 'session'){
            foreach($variant in @('all','asia','london','newyork','overlap')){
                $c=Default-Config;Apply-Structure $c $structure;Apply-StopRR $c ([string]$stop.($s.Slug).variant);Apply-Trailing $c ([string]$trail.($s.Slug).variant);Apply-Session $c $variant;$sequence++;Run-Case $s $tf $variant $c $sequence $developmentFrom $developmentTo
            }
        } elseif($Phase -eq 'locked'){
            $base=Default-Config;$sequence++;Run-Case $s $tf 'baseline' $base $sequence $lockedFrom $lockedTo
            $c=Default-Config;Apply-Structure $c $structure;Apply-StopRR $c ([string]$stop.($s.Slug).variant);Apply-Trailing $c ([string]$trail.($s.Slug).variant);Apply-Session $c ([string]$session.($s.Slug).variant)
            $sequence++;Run-Case $s $tf 'optimized' $c $sequence $lockedFrom $lockedTo
        } elseif($Phase -eq 'full'){
            $c=Default-Config;Apply-Structure $c $structure;Apply-StopRR $c ([string]$stop.($s.Slug).variant);Apply-Trailing $c ([string]$trail.($s.Slug).variant);Apply-Session $c ([string]$session.($s.Slug).variant)
            $sequence++;Run-Case $s $tf 'optimized' $c $sequence $fullFrom $fullTo
        }
    }
}
Write-Host "Completed $sequence native MT5 Every Tick tests for $Phase." -ForegroundColor Green
