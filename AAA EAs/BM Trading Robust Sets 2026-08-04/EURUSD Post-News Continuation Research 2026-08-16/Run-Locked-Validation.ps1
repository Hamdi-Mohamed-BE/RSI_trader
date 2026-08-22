[CmdletBinding()]
param([int]$TimeoutSeconds=600)

Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$researchRoot=$PSScriptRoot
$packageRoot=Split-Path -Parent $researchRoot
$testerRoot=Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'
$terminal=Join-Path $testerRoot 'terminal64.exe'
$configRoot=Join-Path $testerRoot 'backtest-configs\eurusd-post-news-20260816\validation'
$reportRoot=Join-Path $testerRoot 'reports\eurusd-post-news-20260816\validation'
$outputRoot=Join-Path $researchRoot 'Backtest Reports\Locked Validation'
foreach($path in @($configRoot,$reportRoot,$outputRoot)){[void](New-Item -ItemType Directory -Path $path -Force)}

$candidates=@(
    [pscustomobject]@{slug='primary-d3-b50-r20';set='PNC INCLUSIVE d3-b50-r20.set'},
    [pscustomobject]@{slug='alternate-d5-b35-r40';set='PNC INCLUSIVE d5-b35-r40.set'}
)
$windows=@(
    [pscustomobject]@{slug='unseen';from='2025.01.01';to='2026.08.10';model=1},
    [pscustomobject]@{slug='last-year';from='2025.08.11';to='2026.08.10';model=1},
    [pscustomobject]@{slug='2026-real-ticks';from='2026.01.01';to='2026.08.10';model=0}
)

$manifest=New-Object System.Collections.Generic.List[object]
foreach($candidate in $candidates){
    foreach($window in $windows){
        $slug=$candidate.slug+'-'+$window.slug
        $configPath=Join-Path $configRoot ($slug+'.ini')
        $relativeReport='reports\eurusd-post-news-20260816\validation\'+$slug+'.htm'
        $config=@"
[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=AAA Research\EURUSD Post-News Continuation\EURUSD Post-News Continuation EA
ExpertParameters=$($candidate.set)
Symbol=EURUSD
Period=M1
Login=472334559
Deposit=10000
Currency=USD
Leverage=1:2000
Model=$($window.model)
ExecutionMode=1
Optimization=0
FromDate=$($window.from)
ToDate=$($window.to)
ForwardMode=0
Report=$relativeReport
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"@
        [IO.File]::WriteAllText($configPath,$config,[Text.UTF8Encoding]::new($true))
        $testerReport=Join-Path $reportRoot ($slug+'.htm')
        if(Test-Path -LiteralPath $testerReport){Remove-Item -LiteralPath $testerReport -Force}
        Write-Host ('START '+$slug)
        $process=Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"'+$configPath+'"')) -PassThru -WindowStyle Hidden
        try{Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop}
        catch{Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue;throw ($slug+' timed out')}
        if(-not (Test-Path -LiteralPath $testerReport)){throw ($slug+' did not create a report')}
        Copy-Item -LiteralPath $testerReport -Destination (Join-Path $outputRoot ($slug+'.htm')) -Force
        $manifest.Add([pscustomobject]@{slug=$slug;candidate=$candidate.slug;window=$window.slug;model=$window.model;from=$window.from;to=$window.to;set=$candidate.set})
    }
}
$manifest | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $outputRoot 'manifest.json') -Encoding utf8
Write-Host ('Completed '+$manifest.Count+' locked validations.')
