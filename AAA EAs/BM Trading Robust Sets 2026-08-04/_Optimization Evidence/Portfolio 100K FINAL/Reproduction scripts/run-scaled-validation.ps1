param(
    [Parameter(Mandatory = $true)]
    [string]$Sandbox,
    [int]$TimeoutSeconds = 600,
    [switch]$OnlyFixedLots
)

$ErrorActionPreference = 'Stop'
$terminal = Join-Path $Sandbox 'terminal64.exe'
$configDir = Join-Path $PSScriptRoot 'configs'
$reportDir = Join-Path $PSScriptRoot 'scaled validation reports'
$sandboxReportDir = Join-Path $Sandbox 'Reports'
$sandboxPresetDir = Join-Path $Sandbox 'MQL5\Profiles\Tester'
$presetDir = Join-Path $PSScriptRoot 'scaled presets'
New-Item -ItemType Directory -Path $configDir, $reportDir, $sandboxReportDir, $sandboxPresetDir -Force | Out-Null
Get-ChildItem -LiteralPath $presetDir -Filter '*.set' | Copy-Item -Destination $sandboxPresetDir -Force

$tasks = @(
    [pscustomobject]@{Name='PORT_SCALED_RB';Expert='BM Trading\Range Breakout EA';Preset='PORTFOLIO 100K FINAL - Range Breakout - USDJPY M5 - 245 USD risk.set';Symbol='USDJPY..';Period='M5'},
    [pscustomobject]@{Name='PORT_SCALED_GL';Expert='BM Trading\Go Long EA';Preset='PORTFOLIO 100K FINAL - Go Long - US30 D1 - 0.50 lot.set';Symbol='US30';Period='D1'},
    [pscustomobject]@{Name='PORT_SCALED_TT';Expert='BM Trading\Turnaround Tuesday EA';Preset='PORTFOLIO 100K FINAL - Turnaround Tuesday - UT100 D1 - 0.24 lot.set';Symbol='UT100';Period='D1'},
    [pscustomobject]@{Name='PORT_SCALED_ATR';Expert='BM Trading\ATR Candle Breakout EA';Preset='PORTFOLIO 100K FINAL - ATR Candle Breakout - XAUUSD H1 - 146 USD risk.set';Symbol='XAUUSD..';Period='H1'}
)
if ($OnlyFixedLots) { $tasks = $tasks | Where-Object { $_.Name -in @('PORT_SCALED_GL', 'PORT_SCALED_TT') } }

$results = @()
foreach ($task in $tasks) {
    $configPath = Join-Path $configDir ($task.Name + '.ini')
    $sandboxReport = Join-Path $sandboxReportDir ($task.Name + '.htm')
    $finalReport = Join-Path $reportDir ($task.Name + '.htm')
    if (Test-Path -LiteralPath $sandboxReport) { Remove-Item -LiteralPath $sandboxReport -Force }
    $configText = @"
[Tester]
Expert=$($task.Expert)
ExpertParameters=$($task.Preset)
Symbol=$($task.Symbol)
Period=$($task.Period)
Model=0
ExecutionMode=0
Optimization=0
FromDate=2025.01.01
ToDate=2026.08.01
Deposit=100000
Currency=USD
Leverage=1:100
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
Report=Reports\$($task.Name)
ReplaceReport=1
ShutdownTerminal=1
"@
    [IO.File]::WriteAllText($configPath, $configText, [Text.Encoding]::ASCII)
    $started = Get-Date
    $process = Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"' + $configPath + '"')) -PassThru -WindowStyle Hidden
    $timedOut = $false
    try { Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop }
    catch { $timedOut = $true; Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue }
    if (Test-Path -LiteralPath $sandboxReport) { Copy-Item -LiteralPath $sandboxReport -Destination $finalReport -Force }
    $result = [pscustomobject]@{
        Name=$task.Name
        TimedOut=$timedOut
        Seconds=[math]::Round(((Get-Date)-$started).TotalSeconds,1)
        ReportExists=(Test-Path -LiteralPath $finalReport)
        ReportBytes=if(Test-Path -LiteralPath $finalReport){(Get-Item -LiteralPath $finalReport).Length}else{0}
    }
    $results += $result
    $result | ConvertTo-Json -Compress
}
$results | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'scaled-validation-status.json') -Encoding UTF8
