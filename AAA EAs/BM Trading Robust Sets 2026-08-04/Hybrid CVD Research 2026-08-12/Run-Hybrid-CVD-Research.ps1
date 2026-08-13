[CmdletBinding()]
param(
    [ValidateSet('Baseline','Training','Refinement','Final')]
    [string]$Stage = 'Baseline',
    [int]$TimeoutSeconds = 900
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$researchRoot = $PSScriptRoot
$packageRoot = Split-Path -Parent $researchRoot
$testerRoot = Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'
$terminal = Join-Path $testerRoot 'terminal64.exe'
$expertTarget = Join-Path $testerRoot 'MQL5\Experts\Hybrid CVD Research 2026-08-12'
$setTarget = Join-Path $testerRoot 'MQL5\Profiles\Tester'
$slug = $Stage.ToLowerInvariant()
$configRoot = Join-Path $testerRoot "backtest-configs\hybrid-cvd-20260812-$slug"
$reportRoot = Join-Path $testerRoot "reports\hybrid-cvd-20260812-$slug"
$outputRoot = Join-Path $researchRoot "Backtest Reports\$Stage"

foreach ($path in @($expertTarget,$setTarget,$configRoot,$reportRoot,$outputRoot)) {
    [void](New-Item -ItemType Directory -Path $path -Force)
}

Copy-Item -LiteralPath (Join-Path $researchRoot 'Source\Hybrid CVD VWAP EA.ex5') -Destination $expertTarget -Force
Copy-Item -LiteralPath (Join-Path $researchRoot 'Source\Research_Common.mqh') -Destination $expertTarget -Force

$baseSet = Get-Content -Raw -LiteralPath (Join-Path $researchRoot 'Sets\BASE - Hybrid CVD M5 - 1pct.set')

function Set-InputValue {
    param([string]$Text,[string]$Name,[object]$Value)
    $pattern = '(?m)^' + [regex]::Escape($Name) + '=[^\r\n]*$'
    if (-not [regex]::IsMatch($Text,$pattern)) { throw "Input $Name was not found." }
    return [regex]::Replace($Text,$pattern,($Name + '=' + [string]$Value + '||' + [string]$Value + '||0||' + [string]$Value + '||N'),1)
}

function New-Case {
    param([string]$Id,[string]$Label,[string]$Symbol,[string]$Period,[hashtable]$Values)
    [pscustomobject]@{ Id=$Id; Label=$Label; Symbol=$Symbol; Period=$Period; Values=$Values }
}

$cases = New-Object System.Collections.Generic.List[object]
$fromDate = '2025.08.11'
$toDate = '2026.08.10'
$model = 1

if ($Stage -eq 'Baseline') {
    $cases.Add((New-Case 'xau' 'XAU baseline' 'XAUUSD' 'M5' @{}))
    $cases.Add((New-Case 'us30' 'US30 baseline' 'US30' 'M5' @{}))
    $cases.Add((New-Case 'us100' 'US100 baseline' 'USTEC' 'M5' @{}))
}
elseif ($Stage -eq 'Training') {
    $fromDate = '2023.08.11'
    $toDate = '2025.08.10'
    $model = 1
    $symbols = @(
        @{Id='xau'; Label='XAU'; Symbol='XAUUSD'},
        @{Id='us30'; Label='US30'; Symbol='US30'},
        @{Id='us100'; Label='US100'; Symbol='USTEC'}
    )
    $variants = @(
        @{Id='c01'; Label='NY breakout balanced'; Values=@{}},
        @{Id='c02'; Label='NY faster pressure'; Values=@{InpFastCVDMinutes=15;InpFastCVDMinRatio=0.15;InpBreakoutLookback=3;InpRewardRisk=2.5}},
        @{Id='c03'; Label='NY sustained pressure'; Values=@{InpFastCVDMinutes=60;InpFastCVDMinRatio=0.08;InpSessionCVDMinRatio=0.02;InpBreakoutLookback=6}},
        @{Id='c04'; Label='NY high participation'; Values=@{InpFastCVDMinutes=30;InpFastCVDMinRatio=0.10;InpMinRelativeVolume=1.20;InpBreakoutLookback=3;InpRewardRisk=2.5}},
        @{Id='c05'; Label='US open narrow'; Values=@{InpSessionStartUTC=13;InpSessionEndUTC=18;InpFastCVDMinutes=30;InpFastCVDMinRatio=0.10;InpBreakoutLookback=3}},
        @{Id='c06'; Label='London and NY'; Values=@{InpSessionStartUTC=7;InpSessionEndUTC=20;InpFastCVDMinutes=60;InpFastCVDMinRatio=0.08;InpSessionCVDMinRatio=0.01;InpBreakoutLookback=9}},
        @{Id='c07'; Label='Tight stop trend'; Values=@{InpStopATR=1.0;InpRewardRisk=2.5;InpTrailStartR=1.5;InpTrailATR=1.0;InpBreakoutLookback=6}},
        @{Id='c08'; Label='Wide stop trend'; Values=@{InpStopATR=2.0;InpRewardRisk=2.0;InpBreakEvenAtR=1.25;InpTrailStartR=2.0;InpTrailATR=2.0;InpBreakoutLookback=6}},
        @{Id='c09'; Label='No trailing trend'; Values=@{InpStopATR=1.5;InpRewardRisk=2.5;InpBreakEvenAtR=10.0;InpTrailStartR=10.0;InpBreakoutLookback=6}},
        @{Id='c10'; Label='Long only trend'; Values=@{InpEnableShort='false';InpFastCVDMinutes=30;InpFastCVDMinRatio=0.10;InpBreakoutLookback=6}},
        @{Id='c11'; Label='Short only trend'; Values=@{InpEnableLong='false';InpFastCVDMinutes=30;InpFastCVDMinRatio=0.10;InpBreakoutLookback=6}},
        @{Id='c12'; Label='M15 trend'; Values=@{InpSignalTimeframe=15;InpFastCVDMinutes=60;InpFastCVDMinRatio=0.08;InpBreakoutLookback=4;InpSlowEMAPeriod=50;InpStopATR=1.5;InpRewardRisk=2.5}},
        @{Id='d01'; Label='Divergence core'; Values=@{InpSignalMode=1;InpBreakoutLookback=6;InpFastCVDMinutes=30;InpDivergenceLookback=12;InpDivergenceMinImprovement=0.08;InpRewardRisk=2.0}},
        @{Id='d02'; Label='Divergence fast'; Values=@{InpSignalMode=1;InpFastCVDMinutes=15;InpDivergenceLookback=6;InpDivergenceMinImprovement=0.10;InpStopATR=1.25;InpRewardRisk=2.0}},
        @{Id='d03'; Label='Divergence slow'; Values=@{InpSignalMode=1;InpFastCVDMinutes=60;InpDivergenceLookback=18;InpDivergenceMinImprovement=0.05;InpStopATR=2.0;InpRewardRisk=2.0}},
        @{Id='h01'; Label='Both core'; Values=@{InpSignalMode=2;InpFastCVDMinutes=30;InpDivergenceLookback=12;InpDivergenceMinImprovement=0.08;InpBreakoutLookback=6}},
        @{Id='h02'; Label='Both selective'; Values=@{InpSignalMode=2;InpFastCVDMinutes=60;InpFastCVDMinRatio=0.10;InpDivergenceLookback=18;InpDivergenceMinImprovement=0.10;InpBreakoutLookback=9;InpMinRelativeVolume=1.10}}
    )
    foreach ($symbol in $symbols) {
        foreach ($variant in $variants) {
            $cases.Add((New-Case ($symbol.Id+'-'+$variant.Id) ($symbol.Label+' '+$variant.Label) $symbol.Symbol 'M5' $variant.Values))
        }
    }
}
elseif ($Stage -eq 'Refinement') {
    $fromDate = '2023.08.11'
    $toDate = '2025.08.10'
    $model = 1

    $xau = @(
        @{Id='r01';Label='core repeat';Values=@{}},
        @{Id='r02';Label='breakout 4';Values=@{InpBreakoutLookback=4}},
        @{Id='r03';Label='breakout 8';Values=@{InpBreakoutLookback=8}},
        @{Id='r04';Label='CVD 20 threshold 0.14';Values=@{InpFastCVDMinutes=20;InpFastCVDMinRatio=0.14}},
        @{Id='r05';Label='CVD 45 threshold 0.10';Values=@{InpFastCVDMinutes=45;InpFastCVDMinRatio=0.10}},
        @{Id='r06';Label='one trade daily';Values=@{InpMaximumTradesPerDay=1}},
        @{Id='r07';Label='long only core';Values=@{InpEnableShort='false'}},
        @{Id='r08';Label='long only breakout 4';Values=@{InpEnableShort='false';InpBreakoutLookback=4}},
        @{Id='r09';Label='stop 1.25 RR 2.25';Values=@{InpStopATR=1.25;InpRewardRisk=2.25}},
        @{Id='r10';Label='stop 1.75 RR 2.25';Values=@{InpStopATR=1.75;InpRewardRisk=2.25}},
        @{Id='r11';Label='session 12 to 18';Values=@{InpSessionEndUTC=18}},
        @{Id='r12';Label='session 13 to 21';Values=@{InpSessionStartUTC=13}}
    )
    foreach ($variant in $xau) {
        $cases.Add((New-Case ('xau-'+$variant.Id) ('XAU '+$variant.Label) 'XAUUSD' 'M5' $variant.Values))
    }

    $us30Base = @{InpSignalMode=1;InpFastCVDMinutes=60;InpDivergenceLookback=18;InpDivergenceMinImprovement=0.05;InpStopATR=2.0;InpRewardRisk=2.0}
    $us30 = @(
        @{Id='r01';Label='divergence repeat';Values=@{}},
        @{Id='r02';Label='improvement 0.03';Values=@{InpDivergenceMinImprovement=0.03}},
        @{Id='r03';Label='improvement 0.07';Values=@{InpDivergenceMinImprovement=0.07}},
        @{Id='r04';Label='lookback 12';Values=@{InpDivergenceLookback=12}},
        @{Id='r05';Label='lookback 24';Values=@{InpDivergenceLookback=24}},
        @{Id='r06';Label='no VWAP gate';Values=@{InpRequireVWAP='false'}},
        @{Id='r07';Label='session 7 to 20';Values=@{InpSessionStartUTC=7;InpSessionEndUTC=20}},
        @{Id='r08';Label='session 13 to 18';Values=@{InpSessionStartUTC=13;InpSessionEndUTC=18}},
        @{Id='r09';Label='RR 1.5';Values=@{InpRewardRisk=1.5}},
        @{Id='r10';Label='RR 2.5';Values=@{InpRewardRisk=2.5}},
        @{Id='r11';Label='M15 divergence';Values=@{InpSignalTimeframe=15;InpFastCVDMinutes=90;InpDivergenceLookback=12}},
        @{Id='r12';Label='long only';Values=@{InpEnableShort='false'}},
        @{Id='r13';Label='short only';Values=@{InpEnableLong='false'}}
    )
    foreach ($variant in $us30) {
        $values = @{} + $us30Base
        foreach ($key in $variant.Values.Keys) { $values[$key]=$variant.Values[$key] }
        $cases.Add((New-Case ('us30-'+$variant.Id) ('US30 '+$variant.Label) 'US30' 'M5' $values))
    }

    $us100Base = @{InpSignalTimeframe=15;InpFastCVDMinutes=60;InpFastCVDMinRatio=0.08;InpBreakoutLookback=4;InpStopATR=1.5;InpRewardRisk=2.5}
    $us100 = @(
        @{Id='r01';Label='M15 repeat';Values=@{}},
        @{Id='r02';Label='breakout 3';Values=@{InpBreakoutLookback=3}},
        @{Id='r03';Label='breakout 6';Values=@{InpBreakoutLookback=6}},
        @{Id='r04';Label='CVD 45 threshold 0.10';Values=@{InpFastCVDMinutes=45;InpFastCVDMinRatio=0.10}},
        @{Id='r05';Label='CVD 90 threshold 0.06';Values=@{InpFastCVDMinutes=90;InpFastCVDMinRatio=0.06}},
        @{Id='r06';Label='one trade daily';Values=@{InpMaximumTradesPerDay=1}},
        @{Id='r07';Label='long only';Values=@{InpEnableShort='false'}},
        @{Id='r08';Label='short only';Values=@{InpEnableLong='false'}},
        @{Id='r09';Label='stop 2 RR 2';Values=@{InpStopATR=2.0;InpRewardRisk=2.0}},
        @{Id='r10';Label='no trailing';Values=@{InpBreakEvenAtR=10.0;InpTrailStartR=10.0}},
        @{Id='r11';Label='session 13 to 20';Values=@{InpSessionStartUTC=13;InpSessionEndUTC=20}},
        @{Id='r12';Label='volume 1.2';Values=@{InpMinRelativeVolume=1.2}}
    )
    foreach ($variant in $us100) {
        $values = @{} + $us100Base
        foreach ($key in $variant.Values.Keys) { $values[$key]=$variant.Values[$key] }
        $cases.Add((New-Case ('us100-'+$variant.Id) ('US100 '+$variant.Label) 'USTEC' 'M5' $values))
    }
}
else {
    # Model 0 is MT5 Every Tick generated from synchronized broker M1 history.
    # Exness has incomplete real-tick archives for XAUUSD and USTEC in this
    # isolated terminal, so Model 4 would silently produce zero-trade reports.
    $model = 0
    $selectionPath = Join-Path $researchRoot 'selected-configs.json'
    if (-not (Test-Path -LiteralPath $selectionPath)) { throw 'selected-configs.json does not exist.' }
    $selected = Get-Content -Raw -LiteralPath $selectionPath | ConvertFrom-Json
    foreach ($item in $selected) {
        $values = @{}
        foreach ($property in $item.Values.PSObject.Properties) { $values[$property.Name]=$property.Value }
        $cases.Add((New-Case $item.Id $item.Label $item.Symbol $item.Period $values))
    }
}

$manifest = @()
foreach ($case in $cases) {
    $setText = $baseSet
    foreach ($key in $case.Values.Keys) { $setText = Set-InputValue $setText $key $case.Values[$key] }
    $setName = "$Stage - $($case.Id).set"
    [IO.File]::WriteAllText((Join-Path $setTarget $setName),$setText,[Text.UTF8Encoding]::new($false))
    if ($Stage -eq 'Final') {
        [IO.File]::WriteAllText((Join-Path (Join-Path $researchRoot 'Sets') ("BEST - $($case.Id).set")),$setText,[Text.UTF8Encoding]::new($false))
    }

    $relativeReport = "reports\hybrid-cvd-20260812-$slug\$($case.Id).htm"
    $report = Join-Path $reportRoot "$($case.Id).htm"
    $configPath = Join-Path $configRoot "$($case.Id).ini"
    $config = @"
[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=Hybrid CVD Research 2026-08-12\Hybrid CVD VWAP EA
ExpertParameters=$setName
Symbol=$($case.Symbol)
Period=$($case.Period)
Login=472334559
Deposit=10000
Currency=USD
Leverage=1:2000
Model=$model
ExecutionMode=1
Optimization=0
FromDate=$fromDate
ToDate=$toDate
ForwardMode=0
Report=$relativeReport
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"@
    [IO.File]::WriteAllText($configPath,$config,[Text.UTF8Encoding]::new($true))
    Remove-Item -LiteralPath $report -Force -ErrorAction SilentlyContinue
    Write-Host ("START {0}" -f $case.Label) -ForegroundColor Cyan
    $process = Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"'+$configPath+'"')) -PassThru -WindowStyle Hidden
    try {
        Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop
    }
    catch {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        throw "$($case.Label) exceeded $TimeoutSeconds seconds."
    }
    if (-not (Test-Path -LiteralPath $report)) { throw "$($case.Label) did not create a report." }
    Copy-Item -LiteralPath $report -Destination $outputRoot -Force
    foreach ($suffix in @('.png','-hst.png','-mfemae.png','-holding.png')) {
        $artifact = Join-Path $reportRoot ($case.Id+$suffix)
        if (Test-Path -LiteralPath $artifact) { Copy-Item -LiteralPath $artifact -Destination $outputRoot -Force }
    }
    $manifest += [pscustomobject]@{Id=$case.Id;Label=$case.Label;Symbol=$case.Symbol;Period=$case.Period;Values=$case.Values;Report=$report}
    Write-Host ("DONE  {0}" -f $case.Label) -ForegroundColor Green
}

$manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $outputRoot 'manifest.json') -Encoding utf8
Write-Host ("Completed {0} Hybrid CVD {1} cases." -f $cases.Count,$Stage) -ForegroundColor Green
