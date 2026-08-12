[CmdletBinding()]
param([int]$TimeoutSeconds = 1200)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$packageRoot = Split-Path -Parent $PSScriptRoot
$btRoot = Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'
$terminal = Join-Path $btRoot 'terminal64.exe'
$expertRoot = Join-Path $btRoot 'MQL5\Experts'
$setRoot = Join-Path $btRoot 'MQL5\Profiles\Tester'
$configRoot = Join-Path $btRoot 'backtest-configs\dmc-video-20260811-validation'
$reportRoot = Join-Path $btRoot 'reports\dmc-video-20260811-validation'
$isolatedConfigRoot = Join-Path $btRoot 'Config'
$exnessConfigRoot = Join-Path $env:APPDATA 'MetaQuotes\Terminal\03EE49753890DF4365DAB4F329CD1335\config'

foreach ($path in @($expertRoot,$setRoot,$configRoot,$reportRoot,$isolatedConfigRoot)) {
    [void](New-Item -ItemType Directory -Path $path -Force)
}
foreach ($name in @('accounts.dat','servers.dat','common.ini')) {
    Copy-Item -LiteralPath (Join-Path $exnessConfigRoot $name) -Destination (Join-Path $isolatedConfigRoot $name) -Force
}

$oldExpertSource = Join-Path $packageRoot 'AAA Final EAs\AAA Final DmC EA\AAA Final DmC EA.ex5'
$newExpertSource = Join-Path $packageRoot 'AAA Final EAs\AAA Final DmC Video EA\AAA Final DmC Video EA.ex5'
$oldExpertTarget = Join-Path $expertRoot 'BM Trading\AAA Final\AAA Final DmC EA\AAA Final DmC EA.ex5'
$newExpertTarget = Join-Path $expertRoot 'BM Trading\AAA Final\AAA Final DmC Video EA\AAA Final DmC Video EA.ex5'
[void](New-Item -ItemType Directory -Path (Split-Path -Parent $oldExpertTarget) -Force)
[void](New-Item -ItemType Directory -Path (Split-Path -Parent $newExpertTarget) -Force)
Copy-Item -LiteralPath $oldExpertSource -Destination $oldExpertTarget -Force
Copy-Item -LiteralPath $newExpertSource -Destination $newExpertTarget -Force

$oldSetName = 'DMC VALIDATION OLD - 1pct.set'
$newSetName = 'DMC VALIDATION VIDEO USTEC v05 - 1pct.set'
Copy-Item -LiteralPath (Join-Path $packageRoot 'Retest All Bots 2026-08-07\Settings\RETEST 04 - AAA Final DmC USTEC - 1pct.set') -Destination (Join-Path $setRoot $oldSetName) -Force
Copy-Item -LiteralPath (Join-Path $packageRoot 'AAA Final EAs\AAA Final DmC Video EA\USTEC CANDIDATE v05 - DAILY LEVELS - 1pct.set') -Destination (Join-Path $setRoot $newSetName) -Force

$cases = @(
    [pscustomobject]@{ Slug='old-ustec-oos'; Label='Old USTEC OOS'; Expert='BM Trading\AAA Final\AAA Final DmC EA\AAA Final DmC EA'; SetName=$oldSetName; From='2026.04.07'; To='2026.08.06' },
    [pscustomobject]@{ Slug='video-v05-ustec-oos'; Label='Video v05 USTEC OOS'; Expert='BM Trading\AAA Final\AAA Final DmC Video EA\AAA Final DmC Video EA'; SetName=$newSetName; From='2026.04.07'; To='2026.08.06' },
    [pscustomobject]@{ Slug='video-v05-ustec-full'; Label='Video v05 USTEC full year'; Expert='BM Trading\AAA Final\AAA Final DmC Video EA\AAA Final DmC Video EA'; SetName=$newSetName; From='2025.08.07'; To='2026.08.06' }
)

foreach ($case in $cases) {
    $configPath = Join-Path $configRoot ($case.Slug + '.ini')
    $reportPath = Join-Path $reportRoot ($case.Slug + '.htm')
    $relativeReport = 'reports\dmc-video-20260811-validation\' + $case.Slug + '.htm'
    $config = @"
[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=$($case.Expert)
ExpertParameters=$($case.SetName)
Symbol=USTEC
Period=H1
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
    Remove-Item -LiteralPath $reportPath -Force -ErrorAction SilentlyContinue
    Write-Host ("START {0}" -f $case.Label) -ForegroundColor Cyan
    $process = Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"' + $configPath + '"')) -PassThru -WindowStyle Hidden
    try {
        Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop
        $process.Refresh()
    } catch {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        throw "$($case.Label) exceeded $TimeoutSeconds seconds."
    }
    if (-not (Test-Path -LiteralPath $reportPath)) { throw "$($case.Label) did not create a report." }
}

$cases | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath (Join-Path $reportRoot 'manifest.json') -Encoding utf8
Write-Host 'USTEC validation completed.' -ForegroundColor Green

