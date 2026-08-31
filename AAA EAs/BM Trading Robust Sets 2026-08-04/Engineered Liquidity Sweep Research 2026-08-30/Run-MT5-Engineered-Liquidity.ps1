[CmdletBinding()]
param(
    [string]$DevelopmentFrom='2024.08.29',
    [string]$DevelopmentTo='2025.08.28',
    [string]$LockedFrom='2025.08.29',
    [string]$LockedTo='2026.08.28',
    [int]$TimeoutSeconds=1200
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'

$researchRoot=$PSScriptRoot
$packageRoot=Split-Path -Parent $researchRoot
$testerRoot=Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'
$terminal=Join-Path $testerRoot 'terminal64.exe'
$compiledSource=Join-Path $researchRoot 'EA\Engineered Liquidity Sweep EA.ex5'
$expertFolder='AAA Research\Engineered Liquidity Sweep'
$expertName='Engineered Liquidity Sweep EA'
$expertRoot=Join-Path (Join-Path $testerRoot 'MQL5\Experts') $expertFolder
$testerSetRoot=Join-Path $testerRoot 'MQL5\Profiles\Tester'
$configRoot=Join-Path $testerRoot 'backtest-configs\engineered-liquidity-20260830'
$testerReportRoot=Join-Path $testerRoot 'reports\engineered-liquidity-20260830'
$outputRoot=Join-Path $researchRoot 'Backtest Reports'
$developmentOutput=Join-Path $outputRoot 'Development 2024-2025'
$lockedOutput=Join-Path $outputRoot 'Locked 2025-2026'
$setOutput=Join-Path $researchRoot 'Sets'
foreach($path in @($expertRoot,$testerSetRoot,$configRoot,$testerReportRoot,$developmentOutput,$lockedOutput,$setOutput)){
    [void](New-Item -ItemType Directory -Path $path -Force)
}
foreach($path in @($developmentOutput,$lockedOutput,$setOutput)){
    Get-ChildItem -LiteralPath $path -File -ErrorAction SilentlyContinue | Remove-Item -Force
}
if(-not (Test-Path -LiteralPath $compiledSource)){throw "Missing compiled EA: $compiledSource"}
Copy-Item -LiteralPath $compiledSource -Destination (Join-Path $expertRoot ($expertName+'.ex5')) -Force

$markets=@(
    [pscustomobject]@{Symbol='XAUUSD';Slug='xauusd';Group='Metal'},
    [pscustomobject]@{Symbol='BTCUSD';Slug='btcusd';Group='Crypto'},
    [pscustomobject]@{Symbol='ETHUSD';Slug='ethusd';Group='Crypto'},
    [pscustomobject]@{Symbol='USTEC';Slug='ustec';Group='Index'},
    [pscustomobject]@{Symbol='EURUSD';Slug='eurusd';Group='Forex'},
    [pscustomobject]@{Symbol='GBPUSD';Slug='gbpusd';Group='Forex'},
    [pscustomobject]@{Symbol='USDJPY';Slug='usdjpy';Group='Forex'},
    [pscustomobject]@{Symbol='AUDUSD';Slug='audusd';Group='Forex'},
    [pscustomobject]@{Symbol='USDCAD';Slug='usdcad';Group='Forex'},
    [pscustomobject]@{Symbol='USDCHF';Slug='usdchf';Group='Forex'},
    [pscustomobject]@{Symbol='NZDUSD';Slug='nzdusd';Group='Forex'}
)

$variants=@(
    [pscustomobject]@{Slug='m15-h1-reclaim';Signal=15;Trend=16385;Lookback=40;Target=40;Hold=64;Displacement='false'},
    [pscustomobject]@{Slug='m15-h4-reclaim';Signal=15;Trend=16388;Lookback=40;Target=40;Hold=64;Displacement='false'},
    [pscustomobject]@{Slug='m15-h4-displacement';Signal=15;Trend=16388;Lookback=40;Target=40;Hold=64;Displacement='true'},
    [pscustomobject]@{Slug='m30-h4-reclaim';Signal=30;Trend=16388;Lookback=36;Target=36;Hold=48;Displacement='false'},
    [pscustomobject]@{Slug='m30-h4-displacement';Signal=30;Trend=16388;Lookback=36;Target=36;Hold=48;Displacement='true'},
    [pscustomobject]@{Slug='h1-d1-reclaim';Signal=16385;Trend=16408;Lookback=32;Target=32;Hold=24;Displacement='false'}
)

function Write-SetFile([string]$Path,[object]$Variant,[long]$Magic){
    $text=@"
InpSignalTimeframe=$($Variant.Signal)
InpSwingStrength=2
InpLiquidityLookback=$($Variant.Lookback)
InpTargetLookback=$($Variant.Target)
InpATRPeriod=14
InpMinimumSweepATR=0.01
InpMaximumSweepATR=0.75
InpStopBufferATR=0.08
InpRequireDirectionalCandle=true
InpRequireDisplacementClose=$($Variant.Displacement)
InpTrendTimeframe=$($Variant.Trend)
InpTrendFastEMA=20
InpTrendSlowEMA=50
InpRequireFastEMASlope=true
InpMinimumRewardRisk=1.5
InpMaximumRewardRisk=8
InpMaximumHoldingBars=$($Variant.Hold)
InpMaximumTradesPerDay=2
InpAllowLong=true
InpAllowShort=true
InpRiskPercent=1
InpMaximumSpreadATR=0.08
InpMaximumDeviationPoints=80
InpMagic=$Magic
"@
    [IO.File]::WriteAllText($Path,$text.TrimStart(),[Text.UTF8Encoding]::new($false))
}

function Run-Case([string]$Phase,[object]$Market,[object]$Variant,[string]$From,[string]$To,[string]$Destination,[int]$Sequence){
    $caseId="$($Market.Slug)--$($Variant.Slug)--$Phase"
    $setName="ELS-$caseId.set"
    $setPath=Join-Path $testerSetRoot $setName
    Write-SetFile $setPath $Variant (86830000+$Sequence)
    if($Phase -eq 'locked'){
        Copy-Item -LiteralPath $setPath -Destination (Join-Path $setOutput "$($Market.Symbol) - $($Variant.Slug) - locked.set") -Force
    }
    $configPath=Join-Path $configRoot ($caseId+'.ini')
    $reportRelative='reports\engineered-liquidity-20260830\'+$caseId+'.htm'
    $reportPath=Join-Path $testerReportRoot ($caseId+'.htm')
    $config=@"
[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=$expertFolder\$expertName
ExpertParameters=$setName
Symbol=$($Market.Symbol)
Period=M1
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
    [IO.File]::WriteAllText($configPath,$config,[Text.UTF8Encoding]::new($true))
    Get-ChildItem -LiteralPath $testerReportRoot -Filter ($caseId+'*') -ErrorAction SilentlyContinue | Remove-Item -Force
    Write-Host ("START {0} {1} {2}" -f $Phase,$Market.Symbol,$Variant.Slug) -ForegroundColor Cyan
    $process=Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"'+$configPath+'"')) -PassThru -WindowStyle Hidden
    try{Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop}
    catch{Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue;throw "MT5 timed out: $caseId"}
    if(-not (Test-Path -LiteralPath $reportPath)){throw "MT5 did not create report: $reportPath"}
    Get-ChildItem -LiteralPath $testerReportRoot -Filter ($caseId+'*') | Copy-Item -Destination $Destination -Force
}

$sequence=0
foreach($market in $markets){
    foreach($variant in $variants){
        $sequence++
        Run-Case 'development' $market $variant $DevelopmentFrom $DevelopmentTo $developmentOutput $sequence
    }
}

$python=(Get-Command python.exe -ErrorAction Stop).Source
$analyzer=Join-Path $researchRoot 'Analyze-Engineered-Liquidity.py'
$selection=Join-Path $researchRoot 'DEVELOPMENT SELECTION.json'
& $python $analyzer select --development $developmentOutput --output $selection
if($LASTEXITCODE -ne 0){throw 'Development selection failed'}
$chosen=(Get-Content -LiteralPath $selection -Raw | ConvertFrom-Json).markets
foreach($market in $markets){
    $variantSlug=$chosen.($market.Slug).variant
    $variant=$variants | Where-Object Slug -eq $variantSlug | Select-Object -First 1
    if($null -eq $variant){throw "Unknown selected variant for $($market.Symbol): $variantSlug"}
    $sequence++
    Run-Case 'locked' $market $variant $LockedFrom $LockedTo $lockedOutput $sequence
}

& $python $analyzer report --development $developmentOutput --locked $lockedOutput --selection $selection --output $researchRoot
if($LASTEXITCODE -ne 0){throw 'Final engineered-liquidity report failed'}
Write-Host 'Completed engineered-liquidity MT5 audit.' -ForegroundColor Green
