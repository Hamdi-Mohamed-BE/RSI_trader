[CmdletBinding()]
param([int]$TimeoutSeconds=1800)

Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$researchRoot=$PSScriptRoot
$packageRoot=Split-Path -Parent $researchRoot
$testerRoot=Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'
$terminal=Join-Path $testerRoot 'terminal64.exe'
$setRoot=Join-Path $testerRoot 'MQL5\Profiles\Tester'
$configRoot=Join-Path $testerRoot 'backtest-configs\online-research-final-btc'
$testerReportRoot=Join-Path $testerRoot 'reports\online-research-final-btc'
$outputRoot=Join-Path $researchRoot 'Backtest Reports\Final Validation\BTC Four SMA b07'
foreach($path in @($setRoot,$configRoot,$testerReportRoot,$outputRoot)){[void](New-Item -ItemType Directory -Path $path -Force)}
$setName='VALIDATION CANDIDATE - BTC Four SMA M5 - b07 - 1pct.set'
Copy-Item -LiteralPath (Join-Path $researchRoot ('Sets\'+$setName)) -Destination (Join-Path $setRoot $setName) -Force
$cases=@(
 [pscustomobject]@{Slug='btc-b07-oos-1y';From='2025.08.07';To='2026.08.06'},
 [pscustomobject]@{Slug='btc-b07-full-3y';From='2023.08.10';To='2026.08.06'}
)
foreach($case in $cases){
 $configPath=Join-Path $configRoot ($case.Slug+'.ini')
 $testerReport=Join-Path $testerReportRoot ($case.Slug+'.htm')
 $relativeReport='reports\online-research-final-btc\'+$case.Slug+'.htm'
 $config=@"
[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=Online Research 2026-08-11\Research BTC Four SMA EA
ExpertParameters=$setName
Symbol=BTCUSD
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
 Remove-Item -LiteralPath $testerReport -Force -ErrorAction SilentlyContinue
 Write-Host ("START {0}" -f $case.Slug) -ForegroundColor Cyan
 $process=Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"'+$configPath+'"')) -PassThru -WindowStyle Hidden
 try{Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop}catch{Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue;throw "$($case.Slug) timed out."}
 if(-not (Test-Path -LiteralPath $testerReport)){throw "$($case.Slug) did not create a report."}
 Get-ChildItem -LiteralPath $testerReportRoot -Filter ($case.Slug+'*') | Copy-Item -Destination $outputRoot -Force
 Write-Host ("DONE  {0}" -f $case.Slug) -ForegroundColor Green
}
$cases | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $outputRoot 'manifest.json') -Encoding utf8
