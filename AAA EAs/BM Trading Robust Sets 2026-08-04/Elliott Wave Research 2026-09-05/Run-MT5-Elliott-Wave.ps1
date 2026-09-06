[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('screen','stoprr','trailing','session','locked','full')]
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
$expertFolder='AAA Research\Elliott Wave 123'
$expertRoot=Join-Path (Join-Path $testerRoot 'MQL5\Experts') $expertFolder
$testerSetRoot=Join-Path $testerRoot 'MQL5\Profiles\Tester'
$configRoot=Join-Path $testerRoot ('backtest-configs\elliott-wave-'+$Phase)
$testerReportRoot=Join-Path $testerRoot ('reports\elliott-wave-'+$Phase)
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
$compiled=Join-Path $researchRoot 'EA\Elliott Wave 123 EA.ex5'
if(-not (Test-Path -LiteralPath $compiled)){throw "Missing compiled EA: $compiled"}
Copy-Item -LiteralPath $compiled -Destination (Join-Path $expertRoot 'Elliott Wave 123 EA.ex5') -Force

$symbols=@(
    [pscustomobject]@{Symbol='XAUUSD';Slug='xauusd'},
    [pscustomobject]@{Symbol='XAGUSD';Slug='xagusd'},
    [pscustomobject]@{Symbol='USTEC';Slug='ustec'},
    [pscustomobject]@{Symbol='US30';Slug='us30'},
    [pscustomobject]@{Symbol='BTCUSD';Slug='btcusd'},
    [pscustomobject]@{Symbol='GBPJPY';Slug='gbpjpy'},
    [pscustomobject]@{Symbol='EURUSD';Slug='eurusd'}
)
if($OnlySymbols.Count -gt 0){$symbols=@($symbols | Where-Object {$OnlySymbols -contains $_.Slug})}
if($symbols.Count -eq 0){throw 'No symbols selected.'}

function Default-Config {
    return [ordered]@{
        Risk=1.0;AllowLong=$true;AllowShort=$true;PivotStrength=3;PivotLookback=300;
        MinWave1ATR=1.50;MaxWave1ATR=10.0;MinRetrace=0.382;MaxRetrace=0.786;
        BreakoutBufferATR=0.05;MinimumBodyATR=0.15;TrendFilter=1;FastEMA=20;SlowEMA=50;Slope=3;
        StopMode=0;StopBufferATR=0.10;StopATR=2.0;MaximumStopATR=5.0;RR=1.50;
        BreakEven=$false;BEAt=1.0;BELock=0.0;Trail=$false;TrailStart=1.0;TrailATR=2.0;
        Dynamic=$false;DynamicTrigger=0.50;DynamicLock=0.20;MaxHold=0;Session=0;
        MaxSpreadATR=0.15;Deviation=80
    }
}

function Apply-Structure([System.Collections.IDictionary]$Config,[string]$Variant){
    $Config.TrendFilter=switch($Variant){'wave-only'{0};'ema50'{1};'ema-stack'{2};'h4-ema50'{3};default{throw "Unknown structure: $Variant"}}
}

function Apply-StopRR([System.Collections.IDictionary]$Config,[string]$Variant){
    if($Variant -notmatch '^(wave2|signal|atr)-rr(050|075|100|150|200|300|400)$'){throw "Unknown stop/RR: $Variant"}
    $Config.StopMode=switch($Matches[1]){'wave2'{0};'signal'{1};'atr'{2}}
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
        default {throw "Unknown trailing: $Variant"}
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
InpPivotStrength=$($C.PivotStrength)
InpPivotLookback=$($C.PivotLookback)
InpMinimumWave1ATR=$($C.MinWave1ATR)
InpMaximumWave1ATR=$($C.MaxWave1ATR)
InpMinimumWave2Retrace=$($C.MinRetrace)
InpMaximumWave2Retrace=$($C.MaxRetrace)
InpBreakoutBufferATR=$($C.BreakoutBufferATR)
InpMinimumBreakoutBodyATR=$($C.MinimumBodyATR)
InpTrendFilter=$($C.TrendFilter)
InpFastEMA=$($C.FastEMA)
InpSlowEMA=$($C.SlowEMA)
InpSlopeLookback=$($C.Slope)
InpStopMode=$($C.StopMode)
InpStopBufferATR=$($C.StopBufferATR)
InpStopATR=$($C.StopATR)
InpMaximumStopATR=$($C.MaximumStopATR)
InpRewardRisk=$($C.RR)
InpUseBreakEven=$($C.BreakEven.ToString().ToLower())
InpBreakEvenAtR=$($C.BEAt)
InpBreakEvenLockR=$($C.BELock)
InpUseATRTrailing=$($C.Trail.ToString().ToLower())
InpTrailStartAtR=$($C.TrailStart)
InpTrailATR=$($C.TrailATR)
InpUseDynamicM15Stop=$($C.Dynamic.ToString().ToLower())
InpDynamicTriggerR=$($C.DynamicTrigger)
InpDynamicLockR=$($C.DynamicLock)
InpMaximumHoldingBars=$($C.MaxHold)
InpSession=$($C.Session)
InpMaximumSpreadATR=$($C.MaxSpreadATR)
InpMaximumDeviationPoints=$($C.Deviation)
InpMagic=$Magic
"@
    [IO.File]::WriteAllText($Path,$text.TrimStart(),[Text.UTF8Encoding]::new($false))
}

function Run-Case([object]$SymbolCase,[string]$Timeframe,[string]$Variant,[System.Collections.IDictionary]$Config,[int]$Sequence,[string]$From,[string]$To,[int]$Model){
    $caseId="$($SymbolCase.Slug)--$($Timeframe.ToLower())--$Variant--$Phase"
    $setName="ElliottWave-$caseId.set"
    $savedSet=Join-Path $setsRoot $setName
    Write-Set $savedSet $Config (965090000+$Sequence)
    Copy-Item -LiteralPath $savedSet -Destination (Join-Path $testerSetRoot $setName) -Force
    $configPath=Join-Path $configRoot ($caseId+'.ini')
    $reportRelative='reports\elliott-wave-'+$Phase+'\'+$caseId+'.htm'
    $reportPath=Join-Path $testerReportRoot ($caseId+'.htm')
    $ini=@"
[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=$expertFolder\Elliott Wave 123 EA
ExpertParameters=$setName
Symbol=$($SymbolCase.Symbol)
Period=$Timeframe
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
    foreach($s in $symbols){foreach($tf in @('M15','H1','H4')){foreach($variant in @('wave-only','ema50','ema-stack','h4-ema50')){
        $c=Default-Config;Apply-Structure $c $variant;$sequence++;Run-Case $s $tf $variant $c $sequence $developmentFrom $developmentTo 1
    }}}
} else {
    $screen=Read-Winners 'screen-selection.json'
    $stop=if($Phase -in @('trailing','session','locked','full')){Read-Winners 'stoprr-selection.json'}else{$null}
    $trail=if($Phase -in @('session','locked','full')){Read-Winners 'trailing-selection.json'}else{$null}
    $session=if($Phase -in @('locked','full')){Read-Winners 'session-selection.json'}else{$null}
    foreach($s in $symbols){
        $selected=$screen.($s.Slug);$tf=[string]$selected.timeframe;$structure=[string]$selected.variant
        if($Phase -eq 'stoprr'){
            foreach($variant in @('wave2-rr050','wave2-rr075','wave2-rr100','wave2-rr150','wave2-rr200','wave2-rr300','wave2-rr400','signal-rr050','signal-rr075','signal-rr100','signal-rr150','signal-rr200','signal-rr300','signal-rr400','atr-rr050','atr-rr075','atr-rr100','atr-rr150','atr-rr200','atr-rr300','atr-rr400')){
                $c=Default-Config;Apply-Structure $c $structure;Apply-StopRR $c $variant;$sequence++;Run-Case $s $tf $variant $c $sequence $developmentFrom $developmentTo 1
            }
        } elseif($Phase -eq 'trailing'){
            foreach($variant in @('none','be075','be100','trail075-atr15','trail100-atr20','dynamic5020')){
                $c=Default-Config;Apply-Structure $c $structure;Apply-StopRR $c ([string]$stop.($s.Slug).variant);Apply-Trailing $c $variant;$sequence++;Run-Case $s $tf $variant $c $sequence $developmentFrom $developmentTo 1
            }
        } elseif($Phase -eq 'session'){
            foreach($variant in @('all','asia','london','newyork','overlap')){
                $c=Default-Config;Apply-Structure $c $structure;Apply-StopRR $c ([string]$stop.($s.Slug).variant);Apply-Trailing $c ([string]$trail.($s.Slug).variant);Apply-Session $c $variant;$sequence++;Run-Case $s $tf $variant $c $sequence $developmentFrom $developmentTo 1
            }
        } elseif($Phase -eq 'locked'){
            $base=Default-Config;$sequence++;Run-Case $s $tf 'baseline' $base $sequence $lockedFrom $lockedTo 0
            $c=Default-Config;Apply-Structure $c $structure;Apply-StopRR $c ([string]$stop.($s.Slug).variant);Apply-Trailing $c ([string]$trail.($s.Slug).variant);Apply-Session $c ([string]$session.($s.Slug).variant)
            $sequence++;Run-Case $s $tf 'optimized' $c $sequence $lockedFrom $lockedTo 0
        } elseif($Phase -eq 'full'){
            $c=Default-Config;Apply-Structure $c $structure;Apply-StopRR $c ([string]$stop.($s.Slug).variant);Apply-Trailing $c ([string]$trail.($s.Slug).variant);Apply-Session $c ([string]$session.($s.Slug).variant)
            $sequence++;Run-Case $s $tf 'optimized' $c $sequence $fullFrom $fullTo 0
        }
    }
}
Write-Host "Completed $sequence MT5 tests for $Phase." -ForegroundColor Green
