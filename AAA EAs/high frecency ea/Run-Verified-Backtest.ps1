[CmdletBinding()]
param(
    [datetime]$FromDate = '2026-08-01',
    [datetime]$ToDate = '2026-08-31',
    [int]$TimeoutSeconds = 1800
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$PackageRoot = $PSScriptRoot
$PortfolioRoot = Split-Path -Parent $PackageRoot
$TesterRoot = Join-Path $PortfolioRoot 'BM Trading Robust Sets 2026-08-04\_Backtests\MT5-DMC-20260811'
$Terminal = Join-Path $TesterRoot 'terminal64.exe'
$ExpertFolder = 'AAA Research\High Frequency OCO Verified'
$ExpertTarget = Join-Path $TesterRoot ('MQL5\Experts\' + $ExpertFolder)
$TesterSetRoot = Join-Path $TesterRoot 'MQL5\Profiles\Tester'
$ConfigRoot = Join-Path $TesterRoot 'backtest-configs\high-frequency-oco-verified'
$PortableReportRoot = Join-Path $TesterRoot 'reports\high-frequency-oco-verified'
$OutputRoot = Join-Path $PackageRoot 'Backtest Reports'
$SetName = 'VERIFIED - XAUUSD M1 - Current Price OCO.set'
$ReportName = 'XAUUSD-M1-OCO-' + $FromDate.ToString('yyyyMMdd') + '-' + $ToDate.ToString('yyyyMMdd')

foreach ($required in @(
    $Terminal,
    (Join-Path $PackageRoot 'EA\XAU M1 Current Price OCO EA.ex5'),
    (Join-Path $PackageRoot 'EA\XAU M1 Current Price OCO EA.mq5'),
    (Join-Path $PackageRoot 'EA\XAU M1 OCO Core.mqh'),
    (Join-Path $PackageRoot 'Settings\LAST INSTALLED - XAUUSD M1 - Current Price OCO.set')
)) {
    if (-not (Test-Path -LiteralPath $required)) { throw "Missing required file: $required" }
}

foreach ($directory in @($ExpertTarget,$TesterSetRoot,$ConfigRoot,$PortableReportRoot,$OutputRoot,(Join-Path $TesterRoot 'Config'))) {
    [void](New-Item -ItemType Directory -Path $directory -Force)
}

$manifestPath = Join-Path $PackageRoot 'LAST INSTALL.txt'
$dataLine = Select-String -LiteralPath $manifestPath -Pattern '^Data folder:\s*(.+)$' | Select-Object -First 1
if (-not $dataLine) { throw 'LAST INSTALL.txt does not identify the active MT5 data folder.' }
$activeDataRoot = $dataLine.Matches[0].Groups[1].Value.Trim()
$activeConfigRoot = Join-Path $activeDataRoot 'config'
$activeCommon = Join-Path $activeConfigRoot 'common.ini'
if (-not (Test-Path -LiteralPath $activeCommon)) { throw "Active MT5 common.ini is missing: $activeCommon" }
$loginMatch = Select-String -LiteralPath $activeCommon -Pattern '^Login=(\d+)$' | Select-Object -First 1
$serverMatch = Select-String -LiteralPath $activeCommon -Pattern '^Server=(.+)$' | Select-Object -First 1
if (-not $loginMatch -or -not $serverMatch) { throw 'Could not read the current MT5 login/server from common.ini.' }
$activeLogin = $loginMatch.Matches[0].Groups[1].Value
$activeServer = $serverMatch.Matches[0].Groups[1].Value.Trim()
$detector = Join-Path $PackageRoot 'Detect-GoldSymbol.py'
$python = Get-Command python.exe -ErrorAction Stop
$detected = @(& $python.Source $detector (Select-String -LiteralPath $manifestPath -Pattern '^Terminal:\s*(.+)$' | Select-Object -First 1).Matches[0].Groups[1].Value.Trim() 2>$null)
$symbol = if ($LASTEXITCODE -eq 0 -and $detected.Count -gt 0) { ([string]$detected[-1]).Trim() } else { 'XAUUSD' }
foreach ($name in @('accounts.dat','servers.dat','common.ini')) {
    $source = Join-Path $activeConfigRoot $name
    if (Test-Path -LiteralPath $source) {
        Copy-Item -LiteralPath $source -Destination (Join-Path $TesterRoot ('Config\' + $name)) -Force
    }
}

Copy-Item -LiteralPath (Join-Path $PackageRoot 'EA\XAU M1 Current Price OCO EA.ex5') -Destination $ExpertTarget -Force
Copy-Item -LiteralPath (Join-Path $PackageRoot 'EA\XAU M1 Current Price OCO EA.mq5') -Destination $ExpertTarget -Force
Copy-Item -LiteralPath (Join-Path $PackageRoot 'EA\XAU M1 OCO Core.mqh') -Destination $ExpertTarget -Force
Copy-Item -LiteralPath (Join-Path $PackageRoot 'Settings\LAST INSTALLED - XAUUSD M1 - Current Price OCO.set') -Destination (Join-Path $TesterSetRoot $SetName) -Force

$configPath = Join-Path $ConfigRoot ($ReportName + '.ini')
$portableReport = Join-Path $PortableReportRoot ($ReportName + '.htm')
$relativeReport = 'reports\high-frequency-oco-verified\' + $ReportName + '.htm'
$config = @"
[Common]
Login=$activeLogin
Server=$activeServer

[Tester]
Expert=$ExpertFolder\XAU M1 Current Price OCO EA
ExpertParameters=$SetName
Symbol=$symbol
Period=M1
Login=$activeLogin
Deposit=10000
Currency=USD
Leverage=1:2000
Model=0
ExecutionMode=1
Optimization=0
FromDate=$($FromDate.ToString('yyyy.MM.dd'))
ToDate=$($ToDate.ToString('yyyy.MM.dd'))
ForwardMode=0
Report=$relativeReport
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"@
[IO.File]::WriteAllText($configPath,$config,[Text.UTF8Encoding]::new($true))
Get-ChildItem -LiteralPath $PortableReportRoot -Filter ($ReportName + '*') -ErrorAction SilentlyContinue | Remove-Item -Force

Write-Host "Running verified MT5 Every Tick test" -ForegroundColor Cyan
Write-Host "EA:     XAU M1 Current Price OCO EA"
Write-Host "Symbol: $symbol (auto-detected; the current tester UI selection is ignored)" -ForegroundColor Yellow
Write-Host "Period: $($FromDate.ToString('yyyy-MM-dd')) through $($ToDate.ToString('yyyy-MM-dd'))"
$process = Start-Process -FilePath $Terminal -ArgumentList @('/portable',('/config:"' + $configPath + '"')) -PassThru -WindowStyle Hidden
try {
    Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop
} catch {
    Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
    throw 'The MT5 test exceeded the allowed time.'
}
if (-not (Test-Path -LiteralPath $portableReport)) {
    $log = Join-Path $TesterRoot ('Tester\logs\' + (Get-Date -Format 'yyyyMMdd') + '.log')
    if (Test-Path -LiteralPath $log) {
        Get-Content -LiteralPath $log | Select-Object -Last 30 | Write-Host
    }
    throw 'MT5 did not create a report. Check the tester log printed above.'
}
Copy-Item -LiteralPath $portableReport -Destination (Join-Path $OutputRoot ($ReportName + '.htm')) -Force
Get-ChildItem -LiteralPath $PortableReportRoot -Filter ($ReportName + '.*') | Where-Object {$_.Extension -ne '.htm'} | Copy-Item -Destination $OutputRoot -Force
Write-Host "SUCCESS: $OutputRoot" -ForegroundColor Green
