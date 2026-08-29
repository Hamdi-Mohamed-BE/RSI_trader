[CmdletBinding()]
param(
    [int]$TimeoutSeconds = 420,
    [string]$FromDate = '2019.07.16',
    [string]$ToDate = '2024.12.31'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$researchRoot=$PSScriptRoot
$packageRoot=Split-Path -Parent $researchRoot
$testerRoot=Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'
$terminal=Join-Path $testerRoot 'terminal64.exe'
$expertRoot=Join-Path $testerRoot 'MQL5\Experts\AAA Research\Nasdaq 5M Open EMA ATR'
$setRoot=Join-Path $testerRoot 'MQL5\Profiles\Tester'
$configRoot=Join-Path $testerRoot 'backtest-configs\n5ema-982-screen-20260829'
$testerReportRoot=Join-Path $testerRoot 'reports\n5ema-982-screen-20260829'
$outputRoot=Join-Path $researchRoot 'Backtest Reports\982 Claim Recheck\Training Screen'
$activeConfigRoot='C:\Users\hama101\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\config'
$isolatedConfigRoot=Join-Path $testerRoot 'Config'
foreach($path in @($expertRoot,$setRoot,$configRoot,$testerReportRoot,$outputRoot,$isolatedConfigRoot)){[void](New-Item -ItemType Directory -Path $path -Force)}
foreach($name in @('accounts.dat','servers.dat','common.ini')){Copy-Item -LiteralPath (Join-Path $activeConfigRoot $name) -Destination (Join-Path $isolatedConfigRoot $name) -Force}
Copy-Item -LiteralPath (Join-Path $researchRoot 'EA\Nasdaq 5M Open EMA ATR EA.ex5') -Destination (Join-Path $expertRoot 'Nasdaq 5M Open EMA ATR EA.ex5') -Force

function Set-InputValue {
    param([string]$Text,[string]$Name,[object]$Value)
    $pattern='(?m)^'+[regex]::Escape($Name)+'=[^\r\n]*$'
    if(-not [regex]::IsMatch($Text,$pattern)){throw "Input $Name was not found."}
    return [regex]::Replace($Text,$pattern,($Name+'='+[string]$Value),1)
}

$cases=New-Object System.Collections.Generic.List[object]
foreach($initial in @(4.0,6.0,8.0,10.0)){
    foreach($trail in @(2.5,4.0,6.0)){
        foreach($start in @(1.0,2.0)){
            $slug=('wide-sl{0}-tr{1}-start{2}' -f ([string]$initial).Replace('.',''),([string]$trail).Replace('.',''),([string]$start).Replace('.',''))
            $cases.Add([pscustomobject]@{Slug=$slug;InitialStopATR=$initial;TrailingATR=$trail;TrailStartR=$start})
        }
    }
}

$baseSet=Get-Content -Raw -LiteralPath (Join-Path $researchRoot 'Sets\BASE - USTEC M5 - 1pct.set')
$manifest=New-Object System.Collections.Generic.List[object]
foreach($case in $cases){
    $setText=$baseSet
    foreach($pair in @(
        @('InpInitialStopATR',$case.InitialStopATR),@('InpTrailingATR',$case.TrailingATR),@('InpTrailStartR',$case.TrailStartR),
        @('InpCloseAtSessionEnd','true'),@('InpAllowLong','true'),@('InpAllowShort','true'),@('InpMaximumSpreadATR','0')
    )){$setText=Set-InputValue $setText $pair[0] $pair[1]}
    $setName='N5EMA 982 SCREEN '+$case.Slug+'.set'
    [IO.File]::WriteAllText((Join-Path $setRoot $setName),$setText,[Text.UTF8Encoding]::new($false))
    $configPath=Join-Path $configRoot ($case.Slug+'.ini')
    $reportPath=Join-Path $testerReportRoot ($case.Slug+'.htm')
    $relativeReport='reports\n5ema-982-screen-20260829\'+$case.Slug+'.htm'
    $config=@"
[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=AAA Research\Nasdaq 5M Open EMA ATR\Nasdaq 5M Open EMA ATR EA
ExpertParameters=$setName
Symbol=USTEC
Period=M5
Login=472334559
Deposit=10000
Currency=USD
Leverage=1:2000
Model=1
ExecutionMode=1
Optimization=0
FromDate=$FromDate
ToDate=$ToDate
ForwardMode=0
Report=$relativeReport
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"@
    [IO.File]::WriteAllText($configPath,$config,[Text.UTF8Encoding]::new($true))
    Get-ChildItem -LiteralPath $testerReportRoot -Filter ($case.Slug+'*') -ErrorAction SilentlyContinue | Remove-Item -Force
    Write-Host ("START {0}" -f $case.Slug) -ForegroundColor Cyan
    $process=Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"'+$configPath+'"')) -PassThru -WindowStyle Hidden
    try{Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop}catch{Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue;throw "TIMEOUT $($case.Slug)"}
    if(-not (Test-Path -LiteralPath $reportPath)){throw "NO REPORT $($case.Slug)"}
    Get-ChildItem -LiteralPath $testerReportRoot -Filter ($case.Slug+'*') | Copy-Item -Destination $outputRoot -Force
    $manifest.Add([pscustomobject]@{Case=$case;Status='complete';Report=(Join-Path $outputRoot ($case.Slug+'.htm'))})
}
$manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $outputRoot 'manifest.json') -Encoding utf8
& (Get-Command python.exe -ErrorAction Stop).Source (Join-Path $researchRoot 'Analyze-Nasdaq-5M-Reports.py') $outputRoot (Join-Path $researchRoot 'claim-982-training-results')
if($LASTEXITCODE -ne 0){throw 'Report analysis failed.'}
Write-Host 'Completed the 982-claim training screen.' -ForegroundColor Green
