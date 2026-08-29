[CmdletBinding()]
param(
    [double]$InitialStopATR,
    [double]$TrailingATR,
    [double]$TrailStartR,
    [int]$TimeoutSeconds = 1200,
    [switch]$OnlyLastYear
)

Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$researchRoot=$PSScriptRoot
$packageRoot=Split-Path -Parent $researchRoot
$testerRoot=Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'
$terminal=Join-Path $testerRoot 'terminal64.exe'
$expertRoot=Join-Path $testerRoot 'MQL5\Experts\AAA Research\Nasdaq 5M Open EMA ATR'
$setRoot=Join-Path $testerRoot 'MQL5\Profiles\Tester'
$configRoot=Join-Path $testerRoot 'backtest-configs\n5ema-982-final-20260829'
$testerReportRoot=Join-Path $testerRoot 'reports\n5ema-982-final-20260829'
$outputRoot=Join-Path $researchRoot 'Backtest Reports\982 Claim Recheck\Final'
$activeConfigRoot='C:\Users\hama101\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\config'
$isolatedConfigRoot=Join-Path $testerRoot 'Config'
foreach($path in @($expertRoot,$setRoot,$configRoot,$testerReportRoot,$outputRoot,$isolatedConfigRoot)){[void](New-Item -ItemType Directory -Path $path -Force)}
foreach($name in @('accounts.dat','servers.dat','common.ini')){Copy-Item -LiteralPath (Join-Path $activeConfigRoot $name) -Destination (Join-Path $isolatedConfigRoot $name) -Force}
Copy-Item -LiteralPath (Join-Path $researchRoot 'EA\Nasdaq 5M Open EMA ATR EA.ex5') -Destination (Join-Path $expertRoot 'Nasdaq 5M Open EMA ATR EA.ex5') -Force

function Set-InputValue([string]$Text,[string]$Name,[object]$Value){
    $pattern='(?m)^'+[regex]::Escape($Name)+'=[^\r\n]*$'
    if(-not [regex]::IsMatch($Text,$pattern)){throw "Input $Name was not found."}
    return [regex]::Replace($Text,$pattern,($Name+'='+[string]$Value),1)
}
$setText=Get-Content -Raw -LiteralPath (Join-Path $researchRoot 'Sets\BASE - USTEC M5 - 1pct.set')
foreach($pair in @(
    @('InpInitialStopATR',$InitialStopATR),@('InpTrailingATR',$TrailingATR),@('InpTrailStartR',$TrailStartR),
    @('InpCloseAtSessionEnd','true'),@('InpAllowLong','true'),@('InpAllowShort','true'),@('InpMaximumSpreadATR','0')
)){$setText=Set-InputValue $setText $pair[0] $pair[1]}
$setName='SELECTED - USTEC M5 - 982 claim recheck - 1pct.set'
[IO.File]::WriteAllText((Join-Path $setRoot $setName),$setText,[Text.UTF8Encoding]::new($false))
[IO.File]::WriteAllText((Join-Path (Join-Path $researchRoot 'Sets') $setName),$setText,[Text.UTF8Encoding]::new($false))

$cases=@(
    [pscustomobject]@{Slug='last-year-2025-2026';From='2025.08.28';To='2026.08.27'},
    [pscustomobject]@{Slug='locked-2025-2026';From='2025.01.01';To='2026.08.27'},
    [pscustomobject]@{Slug='full-2019-2026';From='2019.07.16';To='2026.08.27'}
)
if($OnlyLastYear){$cases=@($cases | Where-Object Slug -eq 'last-year-2025-2026')}
foreach($case in $cases){
    $configPath=Join-Path $configRoot ($case.Slug+'.ini')
    $reportPath=Join-Path $testerReportRoot ($case.Slug+'.htm')
    $relativeReport='reports\n5ema-982-final-20260829\'+$case.Slug+'.htm'
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
Model=0
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
    Get-ChildItem -LiteralPath $testerReportRoot -Filter ($case.Slug+'*') -ErrorAction SilentlyContinue | Remove-Item -Force
    Write-Host ("START {0} Every Tick" -f $case.Slug) -ForegroundColor Cyan
    $process=Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"'+$configPath+'"')) -PassThru -WindowStyle Hidden
    try{Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop}catch{Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue;throw "TIMEOUT $($case.Slug)"}
    if(-not (Test-Path -LiteralPath $reportPath)){throw "NO REPORT $($case.Slug)"}
    Get-ChildItem -LiteralPath $testerReportRoot -Filter ($case.Slug+'*') | Copy-Item -Destination $outputRoot -Force
}
& (Get-Command python.exe -ErrorAction Stop).Source (Join-Path $researchRoot 'Analyze-Nasdaq-5M-Reports.py') $outputRoot (Join-Path $researchRoot 'claim-982-final-results')
if($LASTEXITCODE -ne 0){throw 'Final report analysis failed.'}
Write-Host 'Completed the locked and full-history Every Tick tests.' -ForegroundColor Green
