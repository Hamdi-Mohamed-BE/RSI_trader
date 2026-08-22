[CmdletBinding()]
param(
    [int]$TimeoutSeconds = 300,
    [string]$FromDate = '2019.07.16',
    [string]$ToDate = '2024.12.31',
    [int]$Model = 1
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$researchRoot = $PSScriptRoot
$packageRoot = Split-Path -Parent $researchRoot
$testerRoot = Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'
$terminal = Join-Path $testerRoot 'terminal64.exe'
$expertRoot = Join-Path $testerRoot 'MQL5\Experts\AAA Research\Nasdaq 5M Open EMA ATR'
$setRoot = Join-Path $testerRoot 'MQL5\Profiles\Tester'
$configRoot = Join-Path $testerRoot 'backtest-configs\n5ema-core-20260820'
$testerReportRoot = Join-Path $testerRoot 'reports\n5ema-core-20260820'
$outputRoot = Join-Path $researchRoot 'Backtest Reports\Training Core'
$activeConfigRoot = 'C:\Users\hama101\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\config'
$isolatedConfigRoot = Join-Path $testerRoot 'Config'

foreach ($path in @($expertRoot,$setRoot,$configRoot,$testerReportRoot,$outputRoot,$isolatedConfigRoot)) {
    [void](New-Item -ItemType Directory -Path $path -Force)
}
foreach ($name in @('accounts.dat','servers.dat','common.ini')) {
    Copy-Item -LiteralPath (Join-Path $activeConfigRoot $name) -Destination (Join-Path $isolatedConfigRoot $name) -Force
}
Copy-Item -LiteralPath (Join-Path $researchRoot 'EA\Nasdaq 5M Open EMA ATR EA.ex5') -Destination (Join-Path $expertRoot 'Nasdaq 5M Open EMA ATR EA.ex5') -Force

function Set-InputValue {
    param([string]$Text,[string]$Name,[object]$Value)
    $pattern='(?m)^'+[regex]::Escape($Name)+'=[^\r\n]*$'
    if(-not [regex]::IsMatch($Text,$pattern)){throw "Input $Name was not found."}
    return [regex]::Replace($Text,$pattern,($Name+'='+[string]$Value),1)
}

$baseSet=Get-Content -Raw -LiteralPath (Join-Path $researchRoot 'Sets\BASE - USTEC M5 - 1pct.set')
$cases=New-Object System.Collections.Generic.List[object]
foreach($initial in @(1.0,1.5,2.0,2.5)) {
    foreach($trail in @(1.0,1.5,2.0,2.5)) {
        $slug=('sl{0}-tr{1}' -f ([string]$initial).Replace('.',''),([string]$trail).Replace('.',''))
        $cases.Add([pscustomobject]@{Slug=$slug;InitialStopATR=$initial;TrailingATR=$trail;TrailStartR=0.0;CloseAtSessionEnd=$true})
    }
}

$manifest=New-Object System.Collections.Generic.List[object]
foreach($case in $cases) {
    $setText=$baseSet
    $setText=Set-InputValue $setText 'InpInitialStopATR' $case.InitialStopATR
    $setText=Set-InputValue $setText 'InpTrailingATR' $case.TrailingATR
    $setText=Set-InputValue $setText 'InpTrailStartR' $case.TrailStartR
    $setText=Set-InputValue $setText 'InpCloseAtSessionEnd' ([string]$case.CloseAtSessionEnd).ToLowerInvariant()
    $setName='N5EMA CORE '+$case.Slug+'.set'
    [IO.File]::WriteAllText((Join-Path $setRoot $setName),$setText,[Text.UTF8Encoding]::new($false))

    $configPath=Join-Path $configRoot ($case.Slug+'.ini')
    $reportPath=Join-Path $testerReportRoot ($case.Slug+'.htm')
    $relativeReport='reports\n5ema-core-20260820\'+$case.Slug+'.htm'
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
Model=$Model
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
    Write-Host ("START {0} | initial {1} ATR | trail {2} ATR" -f $case.Slug,$case.InitialStopATR,$case.TrailingATR) -ForegroundColor Cyan
    $process=Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"'+$configPath+'"')) -PassThru -WindowStyle Hidden
    try {
        Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop
    } catch {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        Write-Warning ("TIMEOUT {0}" -f $case.Slug)
        $manifest.Add([pscustomobject]@{Case=$case;Status='timeout';Report=$null})
        continue
    }
    if(-not (Test-Path -LiteralPath $reportPath)) {
        Write-Warning ("NO REPORT {0}" -f $case.Slug)
        $manifest.Add([pscustomobject]@{Case=$case;Status='no-report';Report=$null})
        continue
    }
    Get-ChildItem -LiteralPath $testerReportRoot -Filter ($case.Slug+'*') | Copy-Item -Destination $outputRoot -Force
    $manifest.Add([pscustomobject]@{Case=$case;Status='complete';Report=(Join-Path $outputRoot ($case.Slug+'.htm'))})
    Write-Host ("DONE  {0}" -f $case.Slug) -ForegroundColor Green
}

$manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $outputRoot 'manifest.json') -Encoding utf8
Write-Host ("Completed {0} core screens." -f (($manifest | Where-Object Status -eq 'complete').Count)) -ForegroundColor Green
