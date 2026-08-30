[CmdletBinding()]
param(
    [string]$DevelopmentFrom='2024.08.29',
    [string]$DevelopmentTo='2025.08.28',
    [string]$ValidationFrom='2025.08.29',
    [string]$ValidationTo='2026.02.28',
    [string]$HoldoutFrom='2026.03.01',
    [string]$HoldoutTo='2026.08.28',
    [int]$TimeoutSeconds=1200
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
$configRoot=Join-Path $testerRoot 'backtest-configs\crypto-slow-20260830'
$testerReportRoot=Join-Path $testerRoot 'reports\crypto-slow-20260830'
$outputRoot=Join-Path $researchRoot 'Backtest Reports'
$developmentOutput=Join-Path $outputRoot 'Slow Development 2024-2025'
$validationOutput=Join-Path $outputRoot 'Slow Validation 2025-2026'
$holdoutOutput=Join-Path $outputRoot 'Final Holdout 2026'
$selectedSetRoot=Join-Path $researchRoot 'Slow Sets'
$selectionPath=Join-Path $outputRoot 'slow-selection.json'
$activeConfigRoot='C:\Users\hama101\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\config'
$isolatedConfigRoot=Join-Path $testerRoot 'Config'
foreach($path in @($expertRoot,$testerSetRoot,$configRoot,$testerReportRoot,$developmentOutput,$validationOutput,$holdoutOutput,$selectedSetRoot,$isolatedConfigRoot)){
    [void](New-Item -ItemType Directory -Path $path -Force)
}
foreach($path in @($developmentOutput,$validationOutput,$holdoutOutput)){
    Get-ChildItem -LiteralPath $path -File -ErrorAction SilentlyContinue | Remove-Item -Force
}
foreach($name in @('accounts.dat','servers.dat','common.ini')){
    Copy-Item -LiteralPath (Join-Path $activeConfigRoot $name) -Destination (Join-Path $isolatedConfigRoot $name) -Force
}
$compiledSource=Join-Path $researchRoot 'EA\Crypto Momentum Reversal Hybrid EA.ex5'
if(-not (Test-Path -LiteralPath $compiledSource)){throw "Compile the EA first: $compiledSource"}
Copy-Item -LiteralPath $compiledSource -Destination (Join-Path $expertRoot 'Crypto Momentum Reversal Hybrid EA.ex5') -Force

$symbols=@(
    [pscustomobject]@{Symbol='BTCUSD';Slug='btcusd'},
    [pscustomobject]@{Symbol='ETHUSD';Slug='ethusd'}
)
$variants=@(
    [pscustomobject]@{Id='trend-h1-both-r05';Mode=0;TF=16385;RR=.5;Long=$true;Short=$true;Momentum=$true;BE=$false;MaxHold=16;MaxDay=2;Bands=2.5},
    [pscustomobject]@{Id='trend-h1-both-r07';Mode=0;TF=16385;RR=.7;Long=$true;Short=$true;Momentum=$true;BE=$false;MaxHold=16;MaxDay=2;Bands=2.5},
    [pscustomobject]@{Id='trend-h1-both-r10';Mode=0;TF=16385;RR=1.0;Long=$true;Short=$true;Momentum=$true;BE=$false;MaxHold=16;MaxDay=2;Bands=2.5},
    [pscustomobject]@{Id='trend-h1-long-r07';Mode=0;TF=16385;RR=.7;Long=$true;Short=$false;Momentum=$true;BE=$false;MaxHold=16;MaxDay=2;Bands=2.5},
    [pscustomobject]@{Id='trend-h1-long-r10';Mode=0;TF=16385;RR=1.0;Long=$true;Short=$false;Momentum=$true;BE=$false;MaxHold=16;MaxDay=2;Bands=2.5},
    [pscustomobject]@{Id='trend-h1-both-r10-be';Mode=0;TF=16385;RR=1.0;Long=$true;Short=$true;Momentum=$true;BE=$true;MaxHold=20;MaxDay=2;Bands=2.5},
    [pscustomobject]@{Id='trend-h4-both-r07';Mode=0;TF=16388;RR=.7;Long=$true;Short=$true;Momentum=$true;BE=$false;MaxHold=8;MaxDay=1;Bands=2.5},
    [pscustomobject]@{Id='trend-h4-both-r10';Mode=0;TF=16388;RR=1.0;Long=$true;Short=$true;Momentum=$true;BE=$false;MaxHold=8;MaxDay=1;Bands=2.5},
    [pscustomobject]@{Id='trend-h4-long-r07';Mode=0;TF=16388;RR=.7;Long=$true;Short=$false;Momentum=$true;BE=$false;MaxHold=8;MaxDay=1;Bands=2.5},
    [pscustomobject]@{Id='revert-h1-both-r05';Mode=1;TF=16385;RR=.5;Long=$true;Short=$true;Momentum=$false;BE=$false;MaxHold=16;MaxDay=2;Bands=2.5},
    [pscustomobject]@{Id='revert-h1-both-r07';Mode=1;TF=16385;RR=.7;Long=$true;Short=$true;Momentum=$false;BE=$false;MaxHold=16;MaxDay=2;Bands=2.5},
    [pscustomobject]@{Id='revert-h1-both-r10';Mode=1;TF=16385;RR=1.0;Long=$true;Short=$true;Momentum=$false;BE=$false;MaxHold=16;MaxDay=2;Bands=2.5}
)

function BoolText([bool]$Value){
    if($Value){return 'true'}
    return 'false'
}
function Find-Variant([string]$Id){
    return $variants | Where-Object Id -eq $Id | Select-Object -First 1
}
function Write-SetFile([object]$Variant,[string]$Path,[long]$Magic){
    $text=@"
InpMode=$($Variant.Mode)
InpSignalTimeframe=$($Variant.TF)
InpATRPeriod=14
InpFastEMAPeriod=20
InpSlowEMAPeriod=50
InpRSIPeriod=14
InpBollingerPeriod=20
InpBollingerDeviation=$($Variant.Bands)
InpDonchianBars=20
InpUseH4Trend=true
InpRequire24HourMomentum=$(BoolText $Variant.Momentum)
InpPullbackTouchATR=0.20
InpStructureLookbackBars=6
InpRSILow=22.0
InpRSIHigh=78.0
InpReversionWithH1Trend=false
InpMinimumBreakoutBodyATR=0.70
InpMinimumVolumeFactor=1.10
InpRetestToleranceATR=0.20
InpUseUTCSession=false
InpSessionStartHourUTC=7
InpSessionEndHourUTC=21
InpServerUTCOffsetHours=0
InpMaximumTradesPerDay=$($Variant.MaxDay)
InpMaximumHoldingBars=$($Variant.MaxHold)
InpRiskPercent=1.0
InpRewardRisk=$($Variant.RR)
InpStopBufferATR=0.10
InpMinimumStopATR=0.35
InpMaximumStopATR=2.50
InpMoveToBreakEven=$(BoolText $Variant.BE)
InpBreakEvenAtR=0.50
InpMaximumSpreadATR=0.08
InpMaximumDeviationPoints=80
InpAllowLong=$(BoolText $Variant.Long)
InpAllowShort=$(BoolText $Variant.Short)
InpMagic=$Magic
"@
    [IO.File]::WriteAllText($Path,$text.TrimStart(),[Text.UTF8Encoding]::new($false))
}
function Run-Case([string]$Phase,[object]$SymbolCase,[object]$Variant,[string]$From,[string]$To,[string]$Destination,[int]$Sequence){
    $caseId="$($SymbolCase.Slug)--$($Variant.Id)--$Phase"
    $setName="Crypto-Slow-$caseId.set"
    Write-SetFile $Variant (Join-Path $testerSetRoot $setName) (86470000+$Sequence)
    $configPath=Join-Path $configRoot ($caseId+'.ini')
    $reportRelative='reports\crypto-slow-20260830\'+$caseId+'.htm'
    $reportPath=Join-Path $testerReportRoot ($caseId+'.htm')
    $config=@"
[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=$expertFolder\Crypto Momentum Reversal Hybrid EA
ExpertParameters=$setName
Symbol=$($SymbolCase.Symbol)
Period=M15
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
    Write-Host ("START {0} {1} {2} | {3} to {4}" -f $Phase,$SymbolCase.Symbol,$Variant.Id,$From,$To) -ForegroundColor Cyan
    $process=Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"'+$configPath+'"')) -PassThru -WindowStyle Hidden
    try{
        Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop
    } catch {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        throw "MT5 timed out: $caseId"
    }
    if(-not (Test-Path -LiteralPath $reportPath)){throw "MT5 did not create report: $reportPath"}
    Get-ChildItem -LiteralPath $testerReportRoot -Filter ($caseId+'*') | Copy-Item -Destination $Destination -Force
}

$sequence=0
foreach($symbolCase in $symbols){
    foreach($variant in $variants){
        $sequence++
        Run-Case 'slowdev' $symbolCase $variant $DevelopmentFrom $DevelopmentTo $developmentOutput $sequence
    }
}
$python=(Get-Command python.exe -ErrorAction Stop).Source
& $python (Join-Path $researchRoot 'Slow-Holdout-Analysis.py') select-development --reports $developmentOutput --output $selectionPath
if($LASTEXITCODE -ne 0){throw 'Slow development selection failed'}
$selection=Get-Content -LiteralPath $selectionPath -Raw | ConvertFrom-Json
foreach($symbolCase in $symbols){
    foreach($candidate in $selection.$($symbolCase.Slug).top_two){
        $variant=Find-Variant ([string]$candidate.variant)
        if(-not $variant){throw "Missing candidate $($candidate.variant)"}
        $sequence++
        Run-Case 'slowval' $symbolCase $variant $ValidationFrom $ValidationTo $validationOutput $sequence
    }
}
& $python (Join-Path $researchRoot 'Slow-Holdout-Analysis.py') select-validation --development $developmentOutput --validation $validationOutput --selection $selectionPath --output $selectionPath
if($LASTEXITCODE -ne 0){throw 'Slow validation selection failed'}
$selection=Get-Content -LiteralPath $selectionPath -Raw | ConvertFrom-Json
foreach($symbolCase in $symbols){
    $winnerId=[string]$selection.$($symbolCase.Slug).winner.variant
    $variant=Find-Variant $winnerId
    if(-not $variant){throw "Missing final candidate $winnerId"}
    $sourceSet=Join-Path $testerSetRoot "Crypto-Slow-$($symbolCase.Slug)--$winnerId--slowval.set"
    Copy-Item -LiteralPath $sourceSet -Destination (Join-Path $selectedSetRoot "$($symbolCase.Symbol) - selected $winnerId.set") -Force
    $sequence++
    Run-Case 'holdout' $symbolCase $variant $HoldoutFrom $HoldoutTo $holdoutOutput $sequence
}
& $python (Join-Path $researchRoot 'Slow-Holdout-Analysis.py') report --development $developmentOutput --validation $validationOutput --holdout $holdoutOutput --selection $selectionPath --output $researchRoot
if($LASTEXITCODE -ne 0){throw 'Slow holdout report failed'}
Write-Host 'Completed slow crypto development, validation and final holdout tests.' -ForegroundColor Green
