param(
    [Parameter(Mandatory = $true)]
    [string]$Sandbox,
    [int]$TimeoutSeconds = 600
)

$ErrorActionPreference = 'Stop'
$terminal = Join-Path $Sandbox 'terminal64.exe'
$configDir = Join-Path $PSScriptRoot 'configs'
$reportDir = Join-Path $PSScriptRoot 'base reports'
$sandboxReportDir = Join-Path $Sandbox 'Reports'
New-Item -ItemType Directory -Path $configDir, $reportDir, $sandboxReportDir -Force | Out-Null

$tasks = @(
    [pscustomobject]@{Name='PORT_BASE_RB';Expert='BM Trading\Range Breakout EA';Preset='PORT_BASE_RB.set';Symbol='USDJPY..';Period='M5'},
    [pscustomobject]@{Name='PORT_BASE_GL';Expert='BM Trading\Go Long EA';Preset='PORT_BASE_GL.set';Symbol='US30';Period='D1'},
    [pscustomobject]@{Name='PORT_BASE_TT';Expert='BM Trading\Turnaround Tuesday EA';Preset='PORT_BASE_TT.set';Symbol='UT100';Period='D1'},
    [pscustomobject]@{Name='PORT_BASE_Ninja';Expert='BM Trading\Ninja Turtle Scalper EA';Preset='PORT_BASE_Ninja.set';Symbol='EURUSD..';Period='M5'},
    [pscustomobject]@{Name='PORT_BASE_Fisher';Expert='BM Trading\The Fisherman EA';Preset='PORT_BASE_Fisher.set';Symbol='EURUSD..';Period='H1'},
    [pscustomobject]@{Name='PORT_BASE_ATR';Expert='BM Trading\ATR Candle Breakout EA';Preset='PORT_BASE_ATR.set';Symbol='XAUUSD..';Period='H1'}
)

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
FromDate=2023.01.01
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
    $result = [pscustomobject]@{Name=$task.Name;TimedOut=$timedOut;Seconds=[math]::Round(((Get-Date)-$started).TotalSeconds,1);ReportExists=(Test-Path -LiteralPath $finalReport);ReportBytes=if(Test-Path -LiteralPath $finalReport){(Get-Item -LiteralPath $finalReport).Length}else{0}}
    $results += $result
    $result | ConvertTo-Json -Compress
}
$results | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'common-test-status.json') -Encoding UTF8
