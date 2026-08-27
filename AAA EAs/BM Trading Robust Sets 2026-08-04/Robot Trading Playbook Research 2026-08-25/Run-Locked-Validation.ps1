[CmdletBinding()]
param(
    [string]$FromDate = '2025.08.11',
    [string]$ToDate = '2026.08.10',
    [int]$TimeoutSeconds = 900
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$researchRoot = $PSScriptRoot
$packageRoot = Split-Path -Parent $researchRoot
$testerRoot = Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'
$terminal = Join-Path $testerRoot 'terminal64.exe'
$expertRoot = Join-Path $testerRoot 'MQL5\Experts\AAA Research\Robot Trading Playbook'
$setRoot = Join-Path $testerRoot 'MQL5\Profiles\Tester'
$configRoot = Join-Path $testerRoot 'backtest-configs\robot-playbook-locked'
$testerReportRoot = Join-Path $testerRoot 'reports\robot-playbook-locked'
$outputRoot = Join-Path $researchRoot 'Backtest Reports\Locked Validation'
foreach ($path in @($expertRoot,$setRoot,$configRoot,$testerReportRoot,$outputRoot)) {
    [void](New-Item -ItemType Directory -Path $path -Force)
}
Copy-Item -LiteralPath (Join-Path $researchRoot 'EA\Robot Trading Playbook EA.ex5') -Destination (Join-Path $expertRoot 'Robot Trading Playbook EA.ex5') -Force
$setName = 'RTP LOCKED XAU M30 FAKEOUT.set'
Copy-Item -LiteralPath (Join-Path $researchRoot 'Sets\LOCKED RESEARCH - XAUUSD M30 - Fakeout only - 1pct.set') -Destination (Join-Path $setRoot $setName) -Force
$configPath = Join-Path $configRoot 'xauusd-m30-fakeout.ini'
$reportPath = Join-Path $testerReportRoot 'xauusd-m30-fakeout.htm'
$relativeReport = 'reports\robot-playbook-locked\xauusd-m30-fakeout.htm'
$config = @"
[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=AAA Research\Robot Trading Playbook\Robot Trading Playbook EA
ExpertParameters=$setName
Symbol=XAUUSD
Period=M30
Login=472334559
Deposit=10000
Currency=USD
Leverage=1:2000
Model=0
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
Get-ChildItem -LiteralPath $testerReportRoot -Filter 'xauusd-m30-fakeout*' -ErrorAction SilentlyContinue | Remove-Item -Force
Write-Host 'START locked XAUUSD M30 every-tick validation' -ForegroundColor Cyan
$process = Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"' + $configPath + '"')) -PassThru -WindowStyle Hidden
try {
    Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop
} catch {
    Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
    throw 'Locked validation timed out.'
}
if (-not (Test-Path -LiteralPath $reportPath)) { throw 'Locked validation report was not produced.' }
Get-ChildItem -LiteralPath $testerReportRoot -Filter 'xauusd-m30-fakeout*' | Copy-Item -Destination $outputRoot -Force
[pscustomobject]@{Slug='xauusd-m30-fakeout';Status='complete';Report=(Join-Path $outputRoot 'xauusd-m30-fakeout.htm')} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $outputRoot 'manifest.json') -Encoding utf8
Write-Host 'DONE locked validation' -ForegroundColor Green
