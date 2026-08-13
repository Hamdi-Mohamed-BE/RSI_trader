[CmdletBinding()]
param(
    [ValidateSet('Baseline','Training','Refinement','Neighborhood','Final')]
    [string]$Stage='Baseline',
    [int]$TimeoutSeconds=1200
)

Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'

$researchRoot=$PSScriptRoot
$packageRoot=Split-Path -Parent $researchRoot
$testerRoot=Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'
$terminal=Join-Path $testerRoot 'terminal64.exe'
$expertTarget=Join-Path $testerRoot 'MQL5\Experts\ICT SNR Research 2026-08-13'
$setTarget=Join-Path $testerRoot 'MQL5\Profiles\Tester'
$stageSlug=$Stage.ToLowerInvariant()
$configRoot=Join-Path $testerRoot "backtest-configs\ict-snr-20260813-$stageSlug"
$testerReportRoot=Join-Path $testerRoot "reports\ict-snr-20260813-$stageSlug"
$outputRoot=Join-Path $researchRoot "Backtest Reports\$Stage"

foreach($path in @($expertTarget,$setTarget,$configRoot,$testerReportRoot,$outputRoot)){
    [void](New-Item -ItemType Directory -Path $path -Force)
}

Copy-Item -LiteralPath (Join-Path $researchRoot 'Source\ICT SNR Liquidity Reversal EA.ex5') -Destination $expertTarget -Force
$baseSet=Get-Content -Raw -LiteralPath (Join-Path $researchRoot 'Sets\BASE - ICT SNR M5 - 1pct.set')

function Set-InputValue{
    param([string]$Text,[string]$Name,[object]$Value)
    $pattern='(?m)^'+[regex]::Escape($Name)+'=[^\r\n]*$'
    if(-not [regex]::IsMatch($Text,$pattern)){throw "Input $Name was not found."}
    $raw=[string]$Value
    return [regex]::Replace($Text,$pattern,($Name+'='+$raw+'||'+$raw+'||0||'+$raw+'||N'),1)
}

function Merge-Values{
    param([hashtable]$Base,[hashtable]$Overlay)
    $result=@{}
    foreach($key in $Base.Keys){$result[$key]=$Base[$key]}
    foreach($key in $Overlay.Keys){$result[$key]=$Overlay[$key]}
    return $result
}

function New-ResearchCase{
    param([string]$Id,[string]$Label,[string]$Symbol,[string]$Period,[hashtable]$Values)
    return [pscustomobject]@{Id=$Id;Label=$Label;Symbol=$Symbol;Period=$Period;Values=$Values}
}

$markets=@(
    @{Id='xau';Label='XAU';Symbol='XAUUSD';Base=@{InpSessionStartUTC=7;InpSessionEndUTC=16}},
    @{Id='xag';Label='XAG';Symbol='XAGUSD';Base=@{InpSessionStartUTC=7;InpSessionEndUTC=16}},
    @{Id='us30';Label='US30';Symbol='US30';Base=@{InpSessionStartUTC=12;InpSessionEndUTC=17}},
    @{Id='us100';Label='US100';Symbol='USTEC';Base=@{InpSessionStartUTC=12;InpSessionEndUTC=17}}
)

$cases=New-Object System.Collections.Generic.List[object]
$fromDate='2025.08.11'
$toDate='2026.08.10'
$model=1

if($Stage -eq 'Baseline'){
    foreach($market in $markets){
        $cases.Add((New-ResearchCase $market.Id ($market.Label+' core baseline') $market.Symbol 'M5' $market.Base))
    }
}
elseif($Stage -eq 'Training'){
    $fromDate='2023.08.11'
    $toDate='2025.08.10'
    $variants=@(
        @{Id='t01';Label='core';Period='M5';Values=@{}},
        @{Id='t02';Label='prior day plus Asia';Period='M5';Values=@{InpLevelMask=3}},
        @{Id='t03';Label='prior day plus H1 swing';Period='M5';Values=@{InpLevelMask=5}},
        @{Id='t04';Label='loose level score';Period='M5';Values=@{InpMinimumLevelScore=1}},
        @{Id='t05';Label='strong confluence';Period='M5';Values=@{InpMinimumLevelScore=3;InpLevelZoneATR=0.18}},
        @{Id='t06';Label='M15 structure';Period='M15';Values=@{InpSignalTimeframe=15;InpInternalSwingLookback=4;InpMaximumMSSBars=4;InpDisplacementBodyATR=0.70;InpMinimumFVGATR=0.02;InpMaximumFVGWaitBars=4}},
        @{Id='t07';Label='two R';Period='M5';Values=@{InpRewardRisk=2.0}},
        @{Id='t08';Label='three R';Period='M5';Values=@{InpRewardRisk=3.0}},
        @{Id='t09';Label='strong displacement';Period='M5';Values=@{InpDisplacementBodyATR=1.0;InpMinimumFVGATR=0.06}},
        @{Id='t10';Label='narrow killzone';Period='M5';Values=@{UseNarrowSession='true'}},
        @{Id='t11';Label='no premium discount';Period='M5';Values=@{InpBiasMode=0}},
        @{Id='t12';Label='H1 dealing range bias';Period='M5';Values=@{InpBiasMode=2}},
        @{Id='t13';Label='long only';Period='M5';Values=@{InpEnableShort='false'}},
        @{Id='t14';Label='short only';Period='M5';Values=@{InpEnableLong='false'}},
        @{Id='t15';Label='fast FVG retest';Period='M5';Values=@{InpMaximumFVGWaitBars=3;InpMaximumMSSBars=4}},
        @{Id='t16';Label='deep FVG three R';Period='M5';Values=@{InpFVGRetracement=0.75;InpMaximumFVGWaitBars=8;InpRewardRisk=3.0;InpMaximumEntryChaseATR=0.75}},
        @{Id='t17';Label='ATR trail';Period='M5';Values=@{InpRewardRisk=3.0;InpTrailStartR=1.5;InpTrailATR=1.0}},
        @{Id='t18';Label='no break even';Period='M5';Values=@{InpBreakEvenAtR=10.0;InpRewardRisk=2.5}}
    )
    foreach($market in $markets){
        foreach($variant in $variants){
            $overlay=@{}
            foreach($key in $variant.Values.Keys){if($key -ne 'UseNarrowSession'){$overlay[$key]=$variant.Values[$key]}}
            if($variant.Values.ContainsKey('UseNarrowSession')){
                if($market.Id -in @('xau','xag')){$overlay['InpSessionStartUTC']=7;$overlay['InpSessionEndUTC']=10}
                else{$overlay['InpSessionStartUTC']=13;$overlay['InpSessionEndUTC']=16}
            }
            $values=Merge-Values $market.Base $overlay
            $cases.Add((New-ResearchCase ($market.Id+'-'+$variant.Id) ($market.Label+' '+$variant.Label) $market.Symbol $variant.Period $values))
        }
    }
}
elseif($Stage -eq 'Refinement'){
    $fromDate='2023.08.11'
    $toDate='2025.08.10'
    $relaxed=@{
        InpMinimumLevelScore=1;InpBiasMode=0;InpMinimumSweepATR=0.0;InpMaximumSweepATR=1.2;
        InpMinimumCloseLocation=0.50;InpInternalSwingLookback=3;InpMaximumMSSBars=10;
        InpDisplacementBodyATR=0.45;InpMinimumFVGATR=0.0;InpMaximumFVGWaitBars=10;
        InpMaximumEntryChaseATR=1.0;InpMinimumStopATR=0.25;InpMaximumStopATR=5.0;
        InpMaximumTradesPerDay=2
    }
    $variants=@(
        @{Id='r01';Label='relaxed composite';Period='M5';Values=@{}},
        @{Id='r02';Label='prior day plus Asia relaxed';Period='M5';Values=@{InpLevelMask=3}},
        @{Id='r03';Label='prior day plus H1 relaxed';Period='M5';Values=@{InpLevelMask=5}},
        @{Id='r04';Label='wide SNR zone';Period='M5';Values=@{InpLevelZoneATR=0.25;InpTouchLookback=144}},
        @{Id='r05';Label='clean displacement';Period='M5';Values=@{InpDisplacementBodyATR=0.65;InpMinimumCloseLocation=0.60;InpMaximumMSSBars=8}},
        @{Id='r06';Label='relaxed two R';Period='M5';Values=@{InpRewardRisk=2.0}},
        @{Id='r07';Label='relaxed three R';Period='M5';Values=@{InpRewardRisk=3.0}},
        @{Id='r08';Label='relaxed no break even';Period='M5';Values=@{InpBreakEvenAtR=10.0}},
        @{Id='r09';Label='relaxed ATR trail';Period='M5';Values=@{InpRewardRisk=3.0;InpTrailStartR=1.5;InpTrailATR=1.0}},
        @{Id='r10';Label='relaxed long only';Period='M5';Values=@{InpEnableShort='false'}},
        @{Id='r11';Label='relaxed short only';Period='M5';Values=@{InpEnableLong='false'}},
        @{Id='r12';Label='M1 execution';Period='M1';Values=@{InpSignalTimeframe=1;InpInternalSwingLookback=5;InpMaximumMSSBars=12;InpMaximumFVGWaitBars=12;InpDisplacementBodyATR=0.55;InpMinimumStopATR=0.35}},
        @{Id='r13';Label='M15 execution';Period='M15';Values=@{InpSignalTimeframe=15;InpInternalSwingLookback=3;InpMaximumMSSBars=6;InpMaximumFVGWaitBars=6;InpDisplacementBodyATR=0.45}},
        @{Id='r14';Label='narrow session relaxed';Period='M5';Values=@{UseNarrowSession='true'}}
    )
    foreach($market in $markets){
        foreach($variant in $variants){
            $base=Merge-Values $market.Base $relaxed
            $overlay=@{}
            foreach($key in $variant.Values.Keys){if($key -ne 'UseNarrowSession'){$overlay[$key]=$variant.Values[$key]}}
            if($variant.Values.ContainsKey('UseNarrowSession')){
                if($market.Id -in @('xau','xag')){$overlay['InpSessionStartUTC']=7;$overlay['InpSessionEndUTC']=11}
                else{$overlay['InpSessionStartUTC']=13;$overlay['InpSessionEndUTC']=16}
            }
            $values=Merge-Values $base $overlay
            $cases.Add((New-ResearchCase ($market.Id+'-'+$variant.Id) ($market.Label+' '+$variant.Label) $market.Symbol $variant.Period $values))
        }
    }
}
elseif($Stage -eq 'Neighborhood'){
    $fromDate='2023.08.11'
    $toDate='2025.08.10'
    $relaxed=@{
        InpMinimumLevelScore=1;InpBiasMode=0;InpMinimumSweepATR=0.0;InpMaximumSweepATR=1.2;
        InpMinimumCloseLocation=0.50;InpInternalSwingLookback=3;InpMaximumMSSBars=10;
        InpDisplacementBodyATR=0.45;InpMinimumFVGATR=0.0;InpMaximumFVGWaitBars=10;
        InpMaximumEntryChaseATR=1.0;InpMinimumStopATR=0.25;InpMaximumStopATR=5.0;
        InpMaximumTradesPerDay=2
    }

    $xauBase=Merge-Values $relaxed @{InpSessionStartUTC=7;InpSessionEndUTC=16;InpSignalTimeframe=15;InpInternalSwingLookback=3;InpMaximumMSSBars=6;InpMaximumFVGWaitBars=6;InpDisplacementBodyATR=0.45}
    $xauVariants=@(
        @{Id='n01';Label='M15 repeat';Values=@{}},
        @{Id='n02';Label='M15 two R';Values=@{InpRewardRisk=2.0}},
        @{Id='n03';Label='M15 three R';Values=@{InpRewardRisk=3.0}},
        @{Id='n04';Label='M15 no break even';Values=@{InpBreakEvenAtR=10.0}},
        @{Id='n05';Label='M15 long only';Values=@{InpEnableShort='false'}},
        @{Id='n06';Label='M15 short only';Values=@{InpEnableLong='false'}},
        @{Id='n07';Label='M15 prior day Asia';Values=@{InpLevelMask=3}},
        @{Id='n08';Label='M15 premium discount';Values=@{InpBiasMode=1}},
        @{Id='n09';Label='M15 London';Values=@{InpSessionEndUTC=11}},
        @{Id='n10';Label='M15 stronger displacement';Values=@{InpDisplacementBodyATR=0.60;InpMinimumFVGATR=0.02}}
    )
    foreach($variant in $xauVariants){
        $cases.Add((New-ResearchCase ('xau-'+$variant.Id) ('XAU '+$variant.Label) 'XAUUSD' 'M15' (Merge-Values $xauBase $variant.Values)))
    }

    $xagBase=Merge-Values $relaxed @{InpSessionStartUTC=7;InpSessionEndUTC=18;InpBreakEvenAtR=10.0}
    $xagVariants=@(
        @{Id='n01';Label='no BE repeat';Period='M5';Values=@{}},
        @{Id='n02';Label='one point five R';Period='M5';Values=@{InpRewardRisk=1.5}},
        @{Id='n03';Label='two R';Period='M5';Values=@{InpRewardRisk=2.0}},
        @{Id='n04';Label='three R';Period='M5';Values=@{InpRewardRisk=3.0}},
        @{Id='n05';Label='London only';Period='M5';Values=@{InpSessionEndUTC=11}},
        @{Id='n06';Label='New York only';Period='M5';Values=@{InpSessionStartUTC=12;InpSessionEndUTC=17}},
        @{Id='n07';Label='extended day';Period='M5';Values=@{InpSessionStartUTC=0;InpSessionEndUTC=23}},
        @{Id='n08';Label='M1 no BE';Period='M1';Values=@{InpSignalTimeframe=1;InpInternalSwingLookback=5;InpMaximumMSSBars=12;InpMaximumFVGWaitBars=12;InpDisplacementBodyATR=0.55;InpMinimumStopATR=0.35}},
        @{Id='n09';Label='M15 no BE';Period='M15';Values=@{InpSignalTimeframe=15;InpMaximumMSSBars=6;InpMaximumFVGWaitBars=6}},
        @{Id='n10';Label='long only';Period='M5';Values=@{InpEnableShort='false'}},
        @{Id='n11';Label='short only';Period='M5';Values=@{InpEnableLong='false'}}
    )
    foreach($variant in $xagVariants){
        $cases.Add((New-ResearchCase ('xag-'+$variant.Id) ('XAG '+$variant.Label) 'XAGUSD' $variant.Period (Merge-Values $xagBase $variant.Values)))
    }

    foreach($market in @(@{Id='us30';Label='US30';Symbol='US30'},@{Id='us100';Label='US100';Symbol='USTEC'})){
        $indexBase=Merge-Values $relaxed @{InpSessionStartUTC=12;InpSessionEndUTC=17;InpSignalTimeframe=1;InpInternalSwingLookback=5;InpMaximumMSSBars=12;InpMaximumFVGWaitBars=12;InpDisplacementBodyATR=0.55;InpMinimumStopATR=0.35}
        $indexVariants=@(
            @{Id='n01';Label='M1 repeat';Values=@{}},
            @{Id='n02';Label='M1 two R';Values=@{InpRewardRisk=2.0}},
            @{Id='n03';Label='M1 three R';Values=@{InpRewardRisk=3.0}},
            @{Id='n04';Label='M1 no break even';Values=@{InpBreakEvenAtR=10.0}},
            @{Id='n05';Label='M1 long only';Values=@{InpEnableShort='false'}},
            @{Id='n06';Label='M1 short only';Values=@{InpEnableLong='false'}},
            @{Id='n07';Label='M1 premium discount';Values=@{InpBiasMode=1}},
            @{Id='n08';Label='M1 prior day Asia';Values=@{InpLevelMask=3}},
            @{Id='n09';Label='M1 prior day H1';Values=@{InpLevelMask=5}},
            @{Id='n10';Label='M1 NY open';Values=@{InpSessionStartUTC=13;InpSessionEndUTC=16}},
            @{Id='n11';Label='M1 ATR trail';Values=@{InpRewardRisk=3.0;InpTrailStartR=1.5;InpTrailATR=1.0}},
            @{Id='n12';Label='M1 stronger displacement';Values=@{InpDisplacementBodyATR=0.70;InpMinimumFVGATR=0.02}}
        )
        foreach($variant in $indexVariants){
            $cases.Add((New-ResearchCase ($market.Id+'-'+$variant.Id) ($market.Label+' '+$variant.Label) $market.Symbol 'M1' (Merge-Values $indexBase $variant.Values)))
        }
    }
}
else{
    # Exness-MT5Trial16 does not expose a usable historical real-tick archive to
    # this portable tester. Model 4 exits with "no history data" and zero bars.
    # Use MT5's full Every Tick simulation from the broker's M1 history for the
    # untouched validation instead of silently accepting an invalid zero test.
    $model=0
    $path=Join-Path $researchRoot 'selected-configs.json'
    if(-not (Test-Path -LiteralPath $path)){throw 'selected-configs.json does not exist.'}
    foreach($item in (Get-Content -Raw -LiteralPath $path|ConvertFrom-Json)){
        $values=@{}
        foreach($property in $item.Values.PSObject.Properties){$values[$property.Name]=$property.Value}
        $cases.Add((New-ResearchCase $item.Id $item.Label $item.Symbol $item.Period $values))
    }
}

$manifest=@()
foreach($case in $cases){
    $setText=$baseSet
    foreach($key in $case.Values.Keys){$setText=Set-InputValue $setText $key $case.Values[$key]}
    $setName="$Stage - $($case.Id).set"
    $testerSet=Join-Path $setTarget $setName
    [IO.File]::WriteAllText($testerSet,$setText,[Text.UTF8Encoding]::new($false))
    if($Stage -eq 'Final'){
        [IO.File]::WriteAllText((Join-Path (Join-Path $researchRoot 'Sets') ("BEST - $($case.Id).set")),$setText,[Text.UTF8Encoding]::new($false))
    }

    $relativeReport="reports\ict-snr-20260813-$stageSlug\$($case.Id).htm"
    $testerReport=Join-Path $testerReportRoot "$($case.Id).htm"
    $configPath=Join-Path $configRoot "$($case.Id).ini"
    $config=@"
[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=ICT SNR Research 2026-08-13\ICT SNR Liquidity Reversal EA
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
    Remove-Item -LiteralPath $testerReport -Force -ErrorAction SilentlyContinue
    Write-Host ("START {0}" -f $case.Label) -ForegroundColor Cyan
    $process=Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"'+$configPath+'"')) -PassThru -WindowStyle Hidden
    try{Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop}
    catch{Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue;throw "$($case.Label) exceeded $TimeoutSeconds seconds."}
    if(-not (Test-Path -LiteralPath $testerReport)){throw "$($case.Label) did not create a report."}
    Copy-Item -LiteralPath $testerReport -Destination $outputRoot -Force
    foreach($suffix in @('.png','-hst.png','-mfemae.png','-holding.png')){
        $artifact=Join-Path $testerReportRoot ($case.Id+$suffix)
        if(Test-Path -LiteralPath $artifact){Copy-Item -LiteralPath $artifact -Destination $outputRoot -Force}
    }
    $manifest+=[pscustomobject]@{Id=$case.Id;Label=$case.Label;Symbol=$case.Symbol;Period=$case.Period;Values=$case.Values;Report=$testerReport}
    Write-Host ("DONE  {0}" -f $case.Label) -ForegroundColor Green
}

$manifest|ConvertTo-Json -Depth 8|Set-Content -LiteralPath (Join-Path $outputRoot 'manifest.json') -Encoding utf8
Write-Host ("Completed {0} ICT + SNR {1} cases." -f $cases.Count,$Stage) -ForegroundColor Green
