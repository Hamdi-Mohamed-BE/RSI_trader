[CmdletBinding()]
param([int]$TimeoutSeconds=1200,[string]$SymbolRegex='')

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
$configRoot=Join-Path $testerRoot 'backtest-configs\top-down-fvg-opt-20260827'
$reportRoot=Join-Path $testerRoot 'reports\top-down-fvg-opt-20260827'
$outputRoot=Join-Path $researchRoot 'Optimization Results'
$activeConfigRoot='C:\Users\hama101\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\config'
$isolatedConfigRoot=Join-Path $testerRoot 'Config'
$setName='OPTIMIZE - Top Down FVG Liquidity - M15 - 1pct.set'

foreach($path in @($expertRoot,$setRoot,$configRoot,$reportRoot,$outputRoot,$isolatedConfigRoot)){
    [void](New-Item -ItemType Directory -Path $path -Force)
}
foreach($name in @('accounts.dat','servers.dat','common.ini')){
    Copy-Item -LiteralPath (Join-Path $activeConfigRoot $name) -Destination (Join-Path $isolatedConfigRoot $name) -Force
}
Copy-Item -LiteralPath (Join-Path $researchRoot ('EA\'+$expertName+'.ex5')) -Destination (Join-Path $expertRoot ($expertName+'.ex5')) -Force
Copy-Item -LiteralPath (Join-Path $researchRoot ('Sets\'+$setName)) -Destination (Join-Path $setRoot $setName) -Force

$symbols=@('XAUUSD','USTEC','BTCUSD','ETHUSD')
if($SymbolRegex){$symbols=@($symbols|Where-Object {$_ -match $SymbolRegex})}
if($symbols.Count -eq 0){throw 'No symbols selected.'}
$manifest=New-Object System.Collections.Generic.List[object]

foreach($symbol in $symbols){
    $slug=$symbol.ToLowerInvariant()
    $configPath=Join-Path $configRoot ($slug+'.ini')
    $relativeReport='reports\top-down-fvg-opt-20260827\'+$slug+'.xml'
    $reportPath=Join-Path $reportRoot ($slug+'.xml')
    $config=@"
[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=$expertFolder\$expertName
ExpertParameters=$setName
Symbol=$symbol
Period=M15
Login=472334559
Deposit=10000
Currency=USD
Leverage=1:2000
Model=1
ExecutionMode=1
Optimization=1
OptimizationCriterion=5
FromDate=2021.01.01
ToDate=2024.12.31
ForwardMode=0
Report=$relativeReport
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"@
    [IO.File]::WriteAllText($configPath,$config,[Text.UTF8Encoding]::new($true))
    Get-ChildItem -LiteralPath $reportRoot -Filter ($slug+'*') -ErrorAction SilentlyContinue|Remove-Item -Force
    Write-Host ('OPTIMIZING {0} on 2021-2024 broker history' -f $symbol) -ForegroundColor Cyan
    $process=Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"'+$configPath+'"')) -PassThru -WindowStyle Hidden
    try{Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop}
    catch{
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        $manifest.Add([pscustomobject]@{Symbol=$symbol;Status='timeout';Report=$null})
        Write-Warning ('TIMEOUT '+$symbol)
        continue
    }
    if(-not(Test-Path -LiteralPath $reportPath)){
        $manifest.Add([pscustomobject]@{Symbol=$symbol;Status='no-report';Report=$null})
        Write-Warning ('NO REPORT '+$symbol)
        continue
    }
    Copy-Item -LiteralPath $reportPath -Destination (Join-Path $outputRoot ($slug+'.xml')) -Force
    $manifest.Add([pscustomobject]@{Symbol=$symbol;Status='complete';Report=(Join-Path $outputRoot ($slug+'.xml'))})
    Write-Host ('DONE '+$symbol) -ForegroundColor Green
}
$manifest|ConvertTo-Json -Depth 4|Set-Content -LiteralPath (Join-Path $outputRoot 'manifest.json') -Encoding utf8
Write-Host ('Completed {0} of {1} optimizations.' -f @($manifest|Where-Object Status -eq 'complete').Count,$symbols.Count) -ForegroundColor Green
