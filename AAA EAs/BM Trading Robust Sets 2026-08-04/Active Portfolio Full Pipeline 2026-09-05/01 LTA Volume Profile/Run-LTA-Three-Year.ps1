[CmdletBinding()]
param([int]$TimeoutSeconds = 1800)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$auditRoot = $PSScriptRoot
$packageRoot = Split-Path -Parent (Split-Path -Parent $auditRoot)
$testerRoot = Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'
$terminal = Join-Path $testerRoot 'terminal64.exe'
$expertSource = Join-Path $packageRoot 'LTA volume profile\EA\LTA_Concepts_EA.ex5'
$setSource = Join-Path $packageRoot 'Selected Portfolio Settings 2026-09-01\01 LTA Volume Profile - CURRENT - ALL DAY.set'
$expertFolder = 'AAA Research\Active Portfolio Reaudit 20260905'
$expertName = 'LTA Volume Profile Current'
$expertTargetFolder = Join-Path (Join-Path $testerRoot 'MQL5\Experts') $expertFolder
$setTargetFolder = Join-Path $testerRoot 'MQL5\Profiles\Tester'
$configFolder = Join-Path $testerRoot 'backtest-configs\active-reaudit-lta-3y'
$reportFolder = Join-Path $testerRoot 'reports\active-reaudit-lta-3y'
$outputFolder = Join-Path $auditRoot 'Backtest Reports'

foreach ($path in @($expertTargetFolder, $setTargetFolder, $configFolder, $reportFolder, $outputFolder)) {
    [void](New-Item -ItemType Directory -Path $path -Force)
}

Copy-Item -LiteralPath $expertSource -Destination (Join-Path $expertTargetFolder ($expertName + '.ex5')) -Force
$setName = 'LTA Current All Day 1pct Three Year.set'
Copy-Item -LiteralPath $setSource -Destination (Join-Path $setTargetFolder $setName) -Force

$reportBase = 'lta-current-all-day-1pct-20230901-20260901'
$reportPath = Join-Path $reportFolder ($reportBase + '.htm')
$configPath = Join-Path $configFolder ($reportBase + '.ini')
$config = @"
[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=$expertFolder\$expertName
ExpertParameters=$setName
Symbol=XAUUSD
Period=M15
Login=472334559
Deposit=10000
Currency=USD
Leverage=1:2000
Model=0
ExecutionMode=1
Optimization=0
FromDate=2023.09.01
ToDate=2026.09.01
ForwardMode=0
Report=reports\active-reaudit-lta-3y\$reportBase.htm
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"@
[IO.File]::WriteAllText($configPath, $config, [Text.UnicodeEncoding]::new($false, $true))

Get-ChildItem -LiteralPath $reportFolder -Filter ($reportBase + '*') -ErrorAction SilentlyContinue | Remove-Item -Force
$process = Start-Process -FilePath $terminal -ArgumentList @('/portable', ('/config:"' + $configPath + '"')) -PassThru -WindowStyle Hidden
try {
    Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop
} catch {
    Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
    throw 'The three-year LTA MT5 test timed out.'
}
if (-not (Test-Path -LiteralPath $reportPath)) {
    throw "MT5 did not create the expected report: $reportPath"
}
Get-ChildItem -LiteralPath $reportFolder -Filter ($reportBase + '*') | Copy-Item -Destination $outputFolder -Force
Write-Host "Three-year LTA report saved to $outputFolder" -ForegroundColor Green
