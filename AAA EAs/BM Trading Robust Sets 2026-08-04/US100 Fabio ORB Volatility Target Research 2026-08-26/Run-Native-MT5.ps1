[CmdletBinding()]
param([int]$TimeoutSeconds=1200,[string]$CaseRegex='')

Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$researchRoot=$PSScriptRoot
$packageRoot=Split-Path -Parent $researchRoot
$testerRoot=Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'
$terminal=Join-Path $testerRoot 'terminal64.exe'
$expertFolder='AAA Research\US100 Fabio ORB'
$expertName='US100 Fabio ORB Volatility Target EA'
$expertRoot=Join-Path $testerRoot ('MQL5\Experts\'+$expertFolder)
$setRoot=Join-Path $testerRoot 'MQL5\Profiles\Tester'
$configRoot=Join-Path $testerRoot 'backtest-configs\us100-fabio-orb-20260826'
$testerReports=Join-Path $testerRoot 'reports\us100-fabio-orb-20260826'
$outputRoot=Join-Path $researchRoot 'Backtest Reports'
$activeConfigRoot='C:\Users\hama101\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\config'
$isolatedConfigRoot=Join-Path $testerRoot 'Config'
foreach($path in @($expertRoot,$setRoot,$configRoot,$testerReports,$outputRoot,$isolatedConfigRoot)){
    [void](New-Item -ItemType Directory -Path $path -Force)
}
foreach($name in @('accounts.dat','servers.dat','common.ini')){
    Copy-Item -LiteralPath (Join-Path $activeConfigRoot $name) -Destination (Join-Path $isolatedConfigRoot $name) -Force
}
Copy-Item -LiteralPath (Join-Path $researchRoot ('EA\'+$expertName+'.ex5')) -Destination (Join-Path $expertRoot ($expertName+'.ex5')) -Force

$selected='SCREEN SELECTED - USTEC M5 - ORB15 early bullish RR15 - 1pct.set'
$literal='LITERAL - USTEC M5 - ORB30 direct long RR1 - 1pct.set'
foreach($setName in @($selected,$literal)){
    Copy-Item -LiteralPath (Join-Path $researchRoot ('Sets\'+$setName)) -Destination (Join-Path $setRoot $setName) -Force
}

$cases=@(
    [pscustomobject]@{Slug='selected-training-2020-2023';Set=$selected;From='2020.01.01';To='2023.12.31';Model=1;Segment='Training'},
    [pscustomobject]@{Slug='selected-validation-2024-2025h1';Set=$selected;From='2024.01.01';To='2025.06.30';Model=1;Segment='Validation'},
    [pscustomobject]@{Slug='selected-locked-every-tick';Set=$selected;From='2025.07.01';To='2026.08.25';Model=0;Segment='Locked'},
    [pscustomobject]@{Slug='selected-one-year-every-tick';Set=$selected;From='2025.08.26';To='2026.08.25';Model=0;Segment='Latest year'},
    [pscustomobject]@{Slug='selected-full-2020-2026';Set=$selected;From='2020.01.01';To='2026.08.25';Model=1;Segment='Full'},
    [pscustomobject]@{Slug='literal-training-2020-2023';Set=$literal;From='2020.01.01';To='2023.12.31';Model=1;Segment='Training'},
    [pscustomobject]@{Slug='literal-validation-2024-2025h1';Set=$literal;From='2024.01.01';To='2025.06.30';Model=1;Segment='Validation'},
    [pscustomobject]@{Slug='literal-locked-every-tick';Set=$literal;From='2025.07.01';To='2026.08.25';Model=0;Segment='Locked'},
    [pscustomobject]@{Slug='literal-one-year-every-tick';Set=$literal;From='2025.08.26';To='2026.08.25';Model=0;Segment='Latest year'},
    [pscustomobject]@{Slug='literal-full-2020-2026';Set=$literal;From='2020.01.01';To='2026.08.25';Model=1;Segment='Full'}
)
if($CaseRegex){
    $cases=@($cases|Where-Object Slug -Match $CaseRegex)
    if($cases.Count -eq 0){throw "CaseRegex selected no cases: $CaseRegex"}
}

$manifest=New-Object System.Collections.Generic.List[object]
foreach($case in $cases){
    $configPath=Join-Path $configRoot ($case.Slug+'.ini')
    $reportPath=Join-Path $testerReports ($case.Slug+'.htm')
    $relativeReport='reports\us100-fabio-orb-20260826\'+$case.Slug+'.htm'
    $config=@"
[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=$expertFolder\$expertName
ExpertParameters=$($case.Set)
Symbol=USTEC
Period=M5
Login=472334559
Deposit=10000
Currency=USD
Leverage=1:2000
Model=$($case.Model)
ExecutionMode=1
Optimization=0
FromDate=$($case.From)
ToDate=$($case.To)
ForwardMode=0
Report=$relativeReport
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"@
    [IO.File]::WriteAllText($configPath,$config,[Text.UTF8Encoding]::new($true))
    Get-ChildItem -LiteralPath $testerReports -Filter ($case.Slug+'*') -ErrorAction SilentlyContinue|Remove-Item -Force
    Write-Host ('START {0}: {1} to {2}, model {3}' -f $case.Slug,$case.From,$case.To,$case.Model) -ForegroundColor Cyan
    $process=Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"'+$configPath+'"')) -PassThru -WindowStyle Hidden
    try{ Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop }
    catch{
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        $manifest.Add([pscustomobject]@{Slug=$case.Slug;Strategy=if($case.Set -eq $selected){'Selected'}else{'Literal'};Segment=$case.Segment;From=$case.From;To=$case.To;Model=$case.Model;Status='timeout';Report=$null})
        Write-Warning ('TIMEOUT '+$case.Slug)
        continue
    }
    if(-not(Test-Path -LiteralPath $reportPath)){
        $manifest.Add([pscustomobject]@{Slug=$case.Slug;Strategy=if($case.Set -eq $selected){'Selected'}else{'Literal'};Segment=$case.Segment;From=$case.From;To=$case.To;Model=$case.Model;Status='no-report';Report=$null})
        Write-Warning ('NO REPORT '+$case.Slug)
        continue
    }
    Get-ChildItem -LiteralPath $testerReports -Filter ($case.Slug+'*')|Copy-Item -Destination $outputRoot -Force
    $manifest.Add([pscustomobject]@{Slug=$case.Slug;Strategy=if($case.Set -eq $selected){'Selected'}else{'Literal'};Segment=$case.Segment;From=$case.From;To=$case.To;Model=$case.Model;Status='complete';Report=(Join-Path $outputRoot ($case.Slug+'.htm'))})
    Write-Host ('DONE  '+$case.Slug) -ForegroundColor Green
}
$manifest|ConvertTo-Json -Depth 5|Set-Content -LiteralPath (Join-Path $outputRoot 'manifest.json') -Encoding utf8
Write-Host ('Completed {0} of {1} cases.' -f @($manifest|Where-Object Status -eq 'complete').Count,@($cases).Count) -ForegroundColor Green
