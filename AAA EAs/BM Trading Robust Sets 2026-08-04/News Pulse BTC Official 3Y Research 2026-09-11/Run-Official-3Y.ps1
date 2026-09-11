[CmdletBinding()]
param([int]$TimeoutSeconds = 1800)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$researchRoot = $PSScriptRoot
$packageRoot = Split-Path -Parent $researchRoot
$testerRoot = Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'
$terminal = Join-Path $testerRoot 'terminal64.exe'
$expertFolder = 'AAA Research\News Pulse BTC Official 3Y 20260911'
$setRoot = Join-Path $testerRoot 'MQL5\Profiles\Tester'
$configRoot = Join-Path $testerRoot 'backtest-configs\news-pulse-btc-official-3y'
$reportRoot = Join-Path $testerRoot 'reports\news-pulse-btc-official-3y'
$outputRoot = Join-Path $researchRoot 'Backtest Reports'
$baseSet = Join-Path $packageRoot 'Selected Portfolio Settings 2026-09-01\LAST INSTALLED AUTO BALANCE - News Pulse BTC - BTCUSDr.set'

foreach ($path in @($setRoot, $configRoot, $reportRoot, $outputRoot)) {
    [void](New-Item -ItemType Directory -Path $path -Force)
}

function Upsert([string]$text, [string]$key, [string]$value) {
    $pattern = '(?m)^' + [regex]::Escape($key) + '=.*$'
    if ([regex]::IsMatch($text, $pattern)) {
        return [regex]::Replace($text, $pattern, ($key + '=' + $value))
    }
    return $text.TrimEnd() + "`r`n" + $key + '=' + $value + "`r`n"
}

$setName = 'News Pulse BTC Official 3Y.set'
$setText = Get-Content -Raw -LiteralPath $baseSet
$setText = Upsert $setText 'InpTesterFromDateUTC' '20230911'
$setText = Upsert $setText 'InpTesterToDateUTC' '20260910'
[IO.File]::WriteAllText((Join-Path $setRoot $setName), $setText, [Text.UTF8Encoding]::new($false))

$relativeReport = 'reports\news-pulse-btc-official-3y\btcusd__official-3y.htm'
$reportPath = Join-Path $reportRoot 'btcusd__official-3y.htm'
$configPath = Join-Path $configRoot 'btcusd__official-3y.ini'
$config = @"
[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=$expertFolder\News Pulse BTC Official 3Y
ExpertParameters=$setName
Symbol=BTCUSD
Period=M1
Login=472334559
Deposit=10000
Currency=USD
Leverage=1:2000
Model=0
ExecutionMode=1
Optimization=0
FromDate=2023.09.11
ToDate=2026.09.10
ForwardMode=0
Report=$relativeReport
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"@
[IO.File]::WriteAllText($configPath, $config, [Text.UTF8Encoding]::new($true))

Remove-Item -LiteralPath $reportPath -Force -ErrorAction SilentlyContinue
$process = Start-Process -FilePath $terminal -ArgumentList @('/portable', ('/config:"' + $configPath + '"')) -PassThru -WindowStyle Hidden
Write-Output "Started MT5 tester process $($process.Id)."
try {
    Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop
}
catch {
    Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
    throw 'The three-year MT5 replay timed out.'
}

if (-not (Test-Path -LiteralPath $reportPath)) {
    throw 'MT5 did not create the three-year report.'
}
Copy-Item -LiteralPath $reportPath -Destination (Join-Path $outputRoot 'btcusd__official-3y.htm') -Force
Write-Output "Completed: $reportPath"
