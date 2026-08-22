[CmdletBinding()]
param(
    [string]$FromDate='2024.01.01',
    [string]$ToDate='2025.06.30',
    [string]$OutputFolder='Candidate Validation',
    [string]$RunSlug='candidate-validation',
    [int]$Model=1,
    [int]$TimeoutSeconds=600,
    [string]$CaseRegex=''
)

Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$researchRoot=$PSScriptRoot
$packageRoot=Split-Path -Parent $researchRoot
$testerRoot=Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'
$terminal=Join-Path $testerRoot 'terminal64.exe'
$expertFolder='AAA Research\US100 Selective ORB'
$expertName='US100 Selective ORB Retest EA'
$expertRoot=Join-Path $testerRoot ('MQL5\Experts\'+$expertFolder)
$setRoot=Join-Path $testerRoot 'MQL5\Profiles\Tester'
$configRoot=Join-Path $testerRoot ('backtest-configs\us100-selective-orb-'+$RunSlug)
$reportRoot=Join-Path $testerRoot ('reports\us100-selective-orb-'+$RunSlug)
$outputRoot=Join-Path $researchRoot ('Backtest Reports\'+$OutputFolder)
$outputSetRoot=Join-Path $outputRoot 'Sets'
$activeConfigRoot='C:\Users\hama101\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\config'
$isolatedConfigRoot=Join-Path $testerRoot 'Config'
foreach($path in @($expertRoot,$setRoot,$configRoot,$reportRoot,$outputRoot,$outputSetRoot,$isolatedConfigRoot)){[void](New-Item -ItemType Directory -Path $path -Force)}
foreach($name in @('accounts.dat','servers.dat','common.ini')){Copy-Item -LiteralPath (Join-Path $activeConfigRoot $name) -Destination (Join-Path $isolatedConfigRoot $name) -Force}
Copy-Item -LiteralPath (Join-Path $researchRoot ('EA\'+$expertName+'.ex5')) -Destination (Join-Path $expertRoot ($expertName+'.ex5')) -Force

function Set-InputValue([string]$Text,[string]$Name,[object]$Value){
    $pattern='(?m)^'+[regex]::Escape($Name)+'=[^\r\n]*$'
    if(-not [regex]::IsMatch($Text,$pattern)){throw "Input $Name was not found."}
    $rendered=if($Value -is [bool]){([string]$Value).ToLowerInvariant()}else{[string]$Value}
    return [regex]::Replace($Text,$pattern,($Name+'='+$rendered),1)
}

$cases=@(
    [pscustomobject]@{Slug='rv06-06-body75-r1-t25'; Parameters=@{InpMinimumOpeningRelativeVolume=0.6;InpMinimumBreakoutRelativeVolume=0.6;InpBreakoutBodyMinimum=0.75;InpMaximumRetestBars=1;InpRetestToleranceRange=0.25}},
    [pscustomobject]@{Slug='rv06-06-body75-r3-t25'; Parameters=@{InpMinimumOpeningRelativeVolume=0.6;InpMinimumBreakoutRelativeVolume=0.6;InpBreakoutBodyMinimum=0.75;InpMaximumRetestBars=3;InpRetestToleranceRange=0.25}},
    [pscustomobject]@{Slug='rv06-06-body75-r5-t25'; Parameters=@{InpMinimumOpeningRelativeVolume=0.6;InpMinimumBreakoutRelativeVolume=0.6;InpBreakoutBodyMinimum=0.75;InpMaximumRetestBars=5;InpRetestToleranceRange=0.25}},
    [pscustomobject]@{Slug='rv06-06-body75-r1-t15'; Parameters=@{InpMinimumOpeningRelativeVolume=0.6;InpMinimumBreakoutRelativeVolume=0.6;InpBreakoutBodyMinimum=0.75;InpMaximumRetestBars=1;InpRetestToleranceRange=0.15}},
    [pscustomobject]@{Slug='rv09-06-body75-r1-t25'; Parameters=@{InpMinimumOpeningRelativeVolume=0.9;InpMinimumBreakoutRelativeVolume=0.6;InpBreakoutBodyMinimum=0.75;InpMaximumRetestBars=1;InpRetestToleranceRange=0.25}},
    [pscustomobject]@{Slug='rv06-09-body75-r3-t25'; Parameters=@{InpMinimumOpeningRelativeVolume=0.6;InpMinimumBreakoutRelativeVolume=0.9;InpBreakoutBodyMinimum=0.75;InpMaximumRetestBars=3;InpRetestToleranceRange=0.25}},
    [pscustomobject]@{Slug='rv06-06-body55-r1-t25'; Parameters=@{InpMinimumOpeningRelativeVolume=0.6;InpMinimumBreakoutRelativeVolume=0.6;InpBreakoutBodyMinimum=0.55;InpMaximumRetestBars=1;InpRetestToleranceRange=0.25}},
    [pscustomobject]@{Slug='rv09-09-body75-r5-t15'; Parameters=@{InpMinimumOpeningRelativeVolume=0.9;InpMinimumBreakoutRelativeVolume=0.9;InpBreakoutBodyMinimum=0.75;InpMaximumRetestBars=5;InpRetestToleranceRange=0.15}},
    [pscustomobject]@{Slug='selected-exit-stop00-rr25-be15'; Parameters=@{InpMinimumOpeningRelativeVolume=0.6;InpMinimumBreakoutRelativeVolume=0.9;InpBreakoutBodyMinimum=0.75;InpMaximumRetestBars=3;InpRetestToleranceRange=0.25;InpStopBufferRange=0.0;InpRewardRisk=2.5;InpBreakEvenAtR=1.5}},
    [pscustomobject]@{Slug='selected-exit-stop00-rr20-be15'; Parameters=@{InpMinimumOpeningRelativeVolume=0.6;InpMinimumBreakoutRelativeVolume=0.9;InpBreakoutBodyMinimum=0.75;InpMaximumRetestBars=3;InpRetestToleranceRange=0.25;InpStopBufferRange=0.0;InpRewardRisk=2.0;InpBreakEvenAtR=1.5}},
    [pscustomobject]@{Slug='selected-exit-stop05-rr25-be15'; Parameters=@{InpMinimumOpeningRelativeVolume=0.6;InpMinimumBreakoutRelativeVolume=0.9;InpBreakoutBodyMinimum=0.75;InpMaximumRetestBars=3;InpRetestToleranceRange=0.25;InpStopBufferRange=0.05;InpRewardRisk=2.5;InpBreakEvenAtR=1.5}},
    [pscustomobject]@{Slug='selected-exit-stop00-rr30-be15'; Parameters=@{InpMinimumOpeningRelativeVolume=0.6;InpMinimumBreakoutRelativeVolume=0.9;InpBreakoutBodyMinimum=0.75;InpMaximumRetestBars=3;InpRetestToleranceRange=0.25;InpStopBufferRange=0.0;InpRewardRisk=3.0;InpBreakEvenAtR=1.5}},
    [pscustomobject]@{Slug='early-rv08-06-body75-r3-t25'; Parameters=@{InpEntryCutoffHour=10;InpEntryCutoffMinute=30;InpMinimumOpeningRelativeVolume=0.8;InpMinimumBreakoutRelativeVolume=0.6;InpBreakoutBodyMinimum=0.75;InpMaximumRetestBars=3;InpRetestToleranceRange=0.25}},
    [pscustomobject]@{Slug='early-rv06-06-body75-r3-t25'; Parameters=@{InpEntryCutoffHour=10;InpEntryCutoffMinute=30;InpMinimumOpeningRelativeVolume=0.6;InpMinimumBreakoutRelativeVolume=0.6;InpBreakoutBodyMinimum=0.75;InpMaximumRetestBars=3;InpRetestToleranceRange=0.25}},
    [pscustomobject]@{Slug='early-rv08-08-body75-r3-t25'; Parameters=@{InpEntryCutoffHour=10;InpEntryCutoffMinute=30;InpMinimumOpeningRelativeVolume=0.8;InpMinimumBreakoutRelativeVolume=0.8;InpBreakoutBodyMinimum=0.75;InpMaximumRetestBars=3;InpRetestToleranceRange=0.25}},
    [pscustomobject]@{Slug='early-rv06-08-body75-r3-t25'; Parameters=@{InpEntryCutoffHour=10;InpEntryCutoffMinute=30;InpMinimumOpeningRelativeVolume=0.6;InpMinimumBreakoutRelativeVolume=0.8;InpBreakoutBodyMinimum=0.75;InpMaximumRetestBars=3;InpRetestToleranceRange=0.25}},
    [pscustomobject]@{Slug='early-rv08-06-body75-r3-t15'; Parameters=@{InpEntryCutoffHour=10;InpEntryCutoffMinute=30;InpMinimumOpeningRelativeVolume=0.8;InpMinimumBreakoutRelativeVolume=0.6;InpBreakoutBodyMinimum=0.75;InpMaximumRetestBars=3;InpRetestToleranceRange=0.15}},
    [pscustomobject]@{Slug='v3-neighbor-l1025-s1100'; Parameters=@{InpUseTimeDirectionFilter=$true;InpLongOnlyStartHour=10;InpLongOnlyStartMinute=25;InpShortOnlyStartHour=11;InpShortOnlyStartMinute=0;InpMinimumOpeningRelativeVolume=0.6;InpMinimumBreakoutRelativeVolume=0.9;InpBreakoutBodyMinimum=0.75;InpMaximumRetestBars=3;InpRetestToleranceRange=0.25}},
    [pscustomobject]@{Slug='v3-neighbor-l1030-s1100'; Parameters=@{InpUseTimeDirectionFilter=$true;InpLongOnlyStartHour=10;InpLongOnlyStartMinute=30;InpShortOnlyStartHour=11;InpShortOnlyStartMinute=0;InpMinimumOpeningRelativeVolume=0.6;InpMinimumBreakoutRelativeVolume=0.9;InpBreakoutBodyMinimum=0.75;InpMaximumRetestBars=3;InpRetestToleranceRange=0.25}},
    [pscustomobject]@{Slug='v3-neighbor-l1035-s1100'; Parameters=@{InpUseTimeDirectionFilter=$true;InpLongOnlyStartHour=10;InpLongOnlyStartMinute=35;InpShortOnlyStartHour=11;InpShortOnlyStartMinute=0;InpMinimumOpeningRelativeVolume=0.6;InpMinimumBreakoutRelativeVolume=0.9;InpBreakoutBodyMinimum=0.75;InpMaximumRetestBars=3;InpRetestToleranceRange=0.25}},
    [pscustomobject]@{Slug='v3-neighbor-l1030-s1055'; Parameters=@{InpUseTimeDirectionFilter=$true;InpLongOnlyStartHour=10;InpLongOnlyStartMinute=30;InpShortOnlyStartHour=10;InpShortOnlyStartMinute=55;InpMinimumOpeningRelativeVolume=0.6;InpMinimumBreakoutRelativeVolume=0.9;InpBreakoutBodyMinimum=0.75;InpMaximumRetestBars=3;InpRetestToleranceRange=0.25}},
    [pscustomobject]@{Slug='v3-neighbor-l1030-s1105'; Parameters=@{InpUseTimeDirectionFilter=$true;InpLongOnlyStartHour=10;InpLongOnlyStartMinute=30;InpShortOnlyStartHour=11;InpShortOnlyStartMinute=5;InpMinimumOpeningRelativeVolume=0.6;InpMinimumBreakoutRelativeVolume=0.9;InpBreakoutBodyMinimum=0.75;InpMaximumRetestBars=3;InpRetestToleranceRange=0.25}},
    [pscustomobject]@{Slug='v3-neighbor-l1025-s1055'; Parameters=@{InpUseTimeDirectionFilter=$true;InpLongOnlyStartHour=10;InpLongOnlyStartMinute=25;InpShortOnlyStartHour=10;InpShortOnlyStartMinute=55;InpMinimumOpeningRelativeVolume=0.6;InpMinimumBreakoutRelativeVolume=0.9;InpBreakoutBodyMinimum=0.75;InpMaximumRetestBars=3;InpRetestToleranceRange=0.25}},
    [pscustomobject]@{Slug='v3-neighbor-l1035-s1105'; Parameters=@{InpUseTimeDirectionFilter=$true;InpLongOnlyStartHour=10;InpLongOnlyStartMinute=35;InpShortOnlyStartHour=11;InpShortOnlyStartMinute=5;InpMinimumOpeningRelativeVolume=0.6;InpMinimumBreakoutRelativeVolume=0.9;InpBreakoutBodyMinimum=0.75;InpMaximumRetestBars=3;InpRetestToleranceRange=0.25}}
)
$cases=@($cases)
if($CaseRegex){
    $cases=@($cases | Where-Object Slug -Match $CaseRegex)
    if($cases.Count -eq 0){throw "CaseRegex selected no cases: $CaseRegex"}
}
$base=Get-Content -Raw -LiteralPath (Join-Path $researchRoot 'Sets\RESEARCH - US100 USTEC M5 - OR30 Retest RV - 1pct.set')
$manifest=New-Object System.Collections.Generic.List[object]
foreach($case in $cases){
    $setText=$base
    foreach($name in $case.Parameters.Keys){$setText=Set-InputValue $setText $name $case.Parameters[$name]}
    $setName='SCREEN '+$case.Slug+'.set'
    [IO.File]::WriteAllText((Join-Path $setRoot $setName),$setText,[Text.UTF8Encoding]::new($false))
    [IO.File]::WriteAllText((Join-Path $outputSetRoot $setName),$setText,[Text.UTF8Encoding]::new($false))
    $configPath=Join-Path $configRoot ($case.Slug+'.ini')
    $reportPath=Join-Path $reportRoot ($case.Slug+'.htm')
    $config=@"
[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=$expertFolder\$expertName
ExpertParameters=$setName
Symbol=USTEC
Period=M5
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
Report=reports\us100-selective-orb-$RunSlug\$($case.Slug).htm
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"@
    [IO.File]::WriteAllText($configPath,$config,[Text.UTF8Encoding]::new($true))
    Get-ChildItem -LiteralPath $reportRoot -Filter ($case.Slug+'*') -ErrorAction SilentlyContinue | Remove-Item -Force
    Write-Host ('START '+$case.Slug) -ForegroundColor Cyan
    $process=Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"'+$configPath+'"')) -PassThru -WindowStyle Hidden
    try{Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop}catch{Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue;$manifest.Add([pscustomobject]@{Strategy='US100 Selective ORB';Slug=$case.Slug;Symbol='USTEC';Parameters=$case.Parameters;Status='timeout';Report=$null});continue}
    if(-not (Test-Path -LiteralPath $reportPath)){$manifest.Add([pscustomobject]@{Strategy='US100 Selective ORB';Slug=$case.Slug;Symbol='USTEC';Parameters=$case.Parameters;Status='no-report';Report=$null});continue}
    Get-ChildItem -LiteralPath $reportRoot -Filter ($case.Slug+'*') | Copy-Item -Destination $outputRoot -Force
    $manifest.Add([pscustomobject]@{Strategy='US100 Selective ORB';Slug=$case.Slug;Symbol='USTEC';Parameters=$case.Parameters;Status='complete';Report=(Join-Path $outputRoot ($case.Slug+'.htm'))})
    Write-Host ('DONE  '+$case.Slug) -ForegroundColor Green
}
$manifest | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $outputRoot 'manifest.json') -Encoding utf8
