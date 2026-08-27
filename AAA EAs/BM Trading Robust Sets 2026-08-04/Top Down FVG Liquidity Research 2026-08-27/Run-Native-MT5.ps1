[CmdletBinding()]
param([int]$TimeoutSeconds=1200,[string]$CaseRegex='')

Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$researchRoot=$PSScriptRoot
$packageRoot=Split-Path -Parent $researchRoot
$testerRoot=Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'
$terminal=Join-Path $testerRoot 'terminal64.exe'
$expertFolder='AAA Research\Top Down FVG Liquidity'
$expertName='Top Down FVG Liquidity EA'
$expertRoot=Join-Path $testerRoot ('MQL5\Experts\'+$expertFolder)
$setRoot=Join-Path $testerRoot 'MQL5\Profiles\Tester'
$configRoot=Join-Path $testerRoot 'backtest-configs\top-down-fvg-native-20260827'
$testerReports=Join-Path $testerRoot 'reports\top-down-fvg-native-20260827'
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

$symbols=@('XAUUSD','USTEC','BTCUSD','ETHUSD')
foreach($symbol in $symbols){
    $setName='SELECTED - '+$symbol+' M15 - Top Down FVG Liquidity - 1pct.set'
    Copy-Item -LiteralPath (Join-Path $researchRoot ('Sets\'+$setName)) -Destination (Join-Path $setRoot $setName) -Force
}

$cases=New-Object System.Collections.Generic.List[object]
foreach($symbol in $symbols){
    $slug=$symbol.ToLowerInvariant()
    $setName='SELECTED - '+$symbol+' M15 - Top Down FVG Liquidity - 1pct.set'
    $cases.Add([pscustomobject]@{Slug=$slug+'-training';Symbol=$symbol;Set=$setName;From='2021.01.01';To='2024.12.31';Model=1;Segment='Training'})
    $cases.Add([pscustomobject]@{Slug=$slug+'-locked-year';Symbol=$symbol;Set=$setName;From='2025.08.26';To='2026.08.26';Model=0;Segment='Locked year'})
}
if($CaseRegex){
    $cases=@($cases|Where-Object Slug -Match $CaseRegex)
    if($cases.Count -eq 0){throw "CaseRegex selected no cases: $CaseRegex"}
}

$manifest=New-Object System.Collections.Generic.List[object]
foreach($case in $cases){
    $configPath=Join-Path $configRoot ($case.Slug+'.ini')
    $reportPath=Join-Path $testerReports ($case.Slug+'.htm')
    $relativeReport='reports\top-down-fvg-native-20260827\'+$case.Slug+'.htm'
    $config=@"
[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=$expertFolder\$expertName
ExpertParameters=$($case.Set)
Symbol=$($case.Symbol)
Period=M15
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
    Write-Host ('START {0}: {1} {2}, model {3}' -f $case.Slug,$case.From,$case.To,$case.Model) -ForegroundColor Cyan
    $process=Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"'+$configPath+'"')) -PassThru -WindowStyle Hidden
    try{Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop}
    catch{
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        $manifest.Add([pscustomobject]@{Slug=$case.Slug;Symbol=$case.Symbol;Segment=$case.Segment;Status='timeout';Report=$null})
        Write-Warning ('TIMEOUT '+$case.Slug)
        continue
    }
    if(-not(Test-Path -LiteralPath $reportPath)){
        $manifest.Add([pscustomobject]@{Slug=$case.Slug;Symbol=$case.Symbol;Segment=$case.Segment;Status='no-report';Report=$null})
        Write-Warning ('NO REPORT '+$case.Slug)
        continue
    }
    Get-ChildItem -LiteralPath $testerReports -Filter ($case.Slug+'*')|Copy-Item -Destination $outputRoot -Force
    $manifest.Add([pscustomobject]@{Slug=$case.Slug;Symbol=$case.Symbol;Segment=$case.Segment;Status='complete';Report=(Join-Path $outputRoot ($case.Slug+'.htm'))})
    Write-Host ('DONE '+$case.Slug) -ForegroundColor Green
}
$manifest|ConvertTo-Json -Depth 5|Set-Content -LiteralPath (Join-Path $outputRoot 'manifest.json') -Encoding utf8
$completedCount=($manifest|Where-Object Status -eq 'complete'|Measure-Object).Count
$caseCount=($cases|Measure-Object).Count
Write-Host ('Completed {0} of {1} cases.' -f $completedCount,$caseCount) -ForegroundColor Green
