[CmdletBinding()]
param(
    [int]$TimeoutSeconds=1200,
    [string]$SetName='OPTIMIZE STAGE 1 - USTEC M5.set',
    [string]$RunSlug='stage-1',
    [string]$FromDate='2020.01.01',
    [string]$ToDate='2023.12.31',
    [int]$Model=1,
    [int]$Optimization=1
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
$configRoot=Join-Path $testerRoot 'backtest-configs\us100-selective-orb-opt-20260821'
$reportRoot=Join-Path $testerRoot 'reports\us100-selective-orb-opt-20260821'
$outputRoot=Join-Path $researchRoot ('Optimization Results\'+$RunSlug)
$activeConfigRoot='C:\Users\hama101\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\config'
$isolatedConfigRoot=Join-Path $testerRoot 'Config'
foreach($path in @($expertRoot,$setRoot,$configRoot,$reportRoot,$outputRoot,$isolatedConfigRoot)){[void](New-Item -ItemType Directory -Path $path -Force)}
foreach($name in @('accounts.dat','servers.dat','common.ini')){Copy-Item -LiteralPath (Join-Path $activeConfigRoot $name) -Destination (Join-Path $isolatedConfigRoot $name) -Force}
Copy-Item -LiteralPath (Join-Path $researchRoot ('EA\'+$expertName+'.ex5')) -Destination (Join-Path $expertRoot ($expertName+'.ex5')) -Force
Copy-Item -LiteralPath (Join-Path $researchRoot ('Sets\'+$SetName)) -Destination (Join-Path $setRoot $SetName) -Force
$configPath=Join-Path $configRoot ($RunSlug+'.ini')
$config=@"
[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=$expertFolder\$expertName
ExpertParameters=$SetName
Symbol=USTEC
Period=M5
Login=472334559
Deposit=10000
Currency=USD
Leverage=1:2000
Model=$Model
ExecutionMode=1
Optimization=$Optimization
OptimizationCriterion=6
FromDate=$FromDate
ToDate=$ToDate
ForwardMode=0
Report=reports\us100-selective-orb-opt-20260821\$RunSlug.xml
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"@
[IO.File]::WriteAllText($configPath,$config,[Text.UTF8Encoding]::new($true))
Get-ChildItem -LiteralPath $reportRoot -Filter ($RunSlug+'*') -ErrorAction SilentlyContinue | Remove-Item -Force
$process=Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"'+$configPath+'"')) -PassThru -WindowStyle Hidden
try{Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop}catch{Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue; throw 'Training optimization timed out.'}
$files=@(Get-ChildItem -LiteralPath $reportRoot -Filter ($RunSlug+'*') -ErrorAction SilentlyContinue)
if($files.Count -eq 0){throw 'MT5 produced no optimization report.'}
$files | Copy-Item -Destination $outputRoot -Force
$files | ForEach-Object {Write-Host ('RESULT '+$_.FullName) -ForegroundColor Green}
