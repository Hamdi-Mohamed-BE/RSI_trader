[CmdletBinding()]
param(
    [string]$FromDate = '2021.08.11',
    [string]$ToDate = '2025.08.10',
    [int]$TimeoutSeconds = 600
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$researchRoot=$PSScriptRoot
$packageRoot=Split-Path -Parent $researchRoot
$testerRoot=Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'
$terminal=Join-Path $testerRoot 'terminal64.exe'
$expertRoot=Join-Path $testerRoot 'MQL5\Experts\AAA Research\XAU Weakness Bias'
$setRoot=Join-Path $testerRoot 'MQL5\Profiles\Tester'
$configRoot=Join-Path $testerRoot 'backtest-configs\xau-weakness-bias-training'
$testerReports=Join-Path $testerRoot 'reports\xau-weakness-bias-training'
$outputRoot=Join-Path $researchRoot 'Backtest Reports\Training'
foreach($path in @($expertRoot,$setRoot,$configRoot,$testerReports,$outputRoot)){[void](New-Item -ItemType Directory -Path $path -Force)}
Copy-Item -LiteralPath (Join-Path $researchRoot 'EA\XAU Weakness Bias Research EA.ex5') -Destination $expertRoot -Force
Copy-Item -LiteralPath (Join-Path $researchRoot 'EA\AAA_Final_Common.mqh') -Destination $expertRoot -Force

$modes=@(
    [pscustomobject]@{Name='baseline';Mode=0;Symmetric='false'},
    [pscustomobject]@{Name='buy-h1';Mode=1;Symmetric='false'},
    [pscustomobject]@{Name='buy-h4';Mode=2;Symmetric='false'},
    [pscustomobject]@{Name='buy-d1';Mode=3;Symmetric='false'},
    [pscustomobject]@{Name='buy-any';Mode=4;Symmetric='false'},
    [pscustomobject]@{Name='buy-majority';Mode=5;Symmetric='false'},
    [pscustomobject]@{Name='buy-all';Mode=6;Symmetric='false'},
    [pscustomobject]@{Name='symmetric-h1';Mode=1;Symmetric='true'},
    [pscustomobject]@{Name='symmetric-h4';Mode=2;Symmetric='true'},
    [pscustomobject]@{Name='symmetric-d1';Mode=3;Symmetric='true'},
    [pscustomobject]@{Name='symmetric-any';Mode=4;Symmetric='true'},
    [pscustomobject]@{Name='symmetric-majority';Mode=5;Symmetric='true'},
    [pscustomobject]@{Name='symmetric-all';Mode=6;Symmetric='true'}
)
$manifest=New-Object System.Collections.Generic.List[object]
foreach($case in $modes){
    $setName='XWB TRAIN '+$case.Name+'.set'
    $set=@"
InpEnableTrading=true
InpRiskPercent=1
InpMagic=4080402
InpMaxSpreadPoints=0
InpMaximumDeviationPoints=50
InpWeaknessATRImpulse=2
InpRewardRisk=2
InpPendingExpiryBars=8
InpBuyBiasMode=$($case.Mode)
InpApplySymmetricBiasToSells=$($case.Symmetric)
InpBiasEMAPeriod=50
InpBiasSlopeBars=3
"@
    [IO.File]::WriteAllText((Join-Path $setRoot $setName),$set,[Text.UTF8Encoding]::new($true))
    $configPath=Join-Path $configRoot ($case.Name+'.ini')
    $reportPath=Join-Path $testerReports ($case.Name+'.htm')
    $relative='reports\xau-weakness-bias-training\'+$case.Name+'.htm'
    $config=@"
[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=AAA Research\XAU Weakness Bias\XAU Weakness Bias Research EA
ExpertParameters=$setName
Symbol=XAUUSD
Period=M15
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
Report=$relative
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"@
    [IO.File]::WriteAllText($configPath,$config,[Text.UTF8Encoding]::new($true))
    Get-ChildItem -LiteralPath $testerReports -Filter ($case.Name+'*') -ErrorAction SilentlyContinue|Remove-Item -Force
    Write-Host ('START '+$case.Name) -ForegroundColor Cyan
    $process=Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"'+$configPath+'"')) -PassThru -WindowStyle Hidden
    try{Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop}catch{Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue;$manifest.Add([pscustomobject]@{Slug=$case.Name;Status='timeout'});continue}
    if(-not(Test-Path -LiteralPath $reportPath)){$manifest.Add([pscustomobject]@{Slug=$case.Name;Status='no-report'});continue}
    Get-ChildItem -LiteralPath $testerReports -Filter ($case.Name+'*')|Copy-Item -Destination $outputRoot -Force
    $manifest.Add([pscustomobject]@{Slug=$case.Name;Mode=$case.Mode;Symmetric=$case.Symmetric;Status='complete';Report=(Join-Path $outputRoot ($case.Name+'.htm'))})
    Write-Host ('DONE  '+$case.Name) -ForegroundColor Green
}
$manifest|ConvertTo-Json -Depth 5|Set-Content -LiteralPath (Join-Path $outputRoot 'manifest.json') -Encoding utf8
Write-Host ('Completed '+(($manifest|Where-Object Status -eq 'complete').Count)+' bias cases.') -ForegroundColor Green
