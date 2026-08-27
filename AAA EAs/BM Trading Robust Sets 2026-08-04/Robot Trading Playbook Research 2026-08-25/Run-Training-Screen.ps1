[CmdletBinding()]
param(
    [string]$FromDate = '2021.08.11',
    [string]$ToDate = '2025.08.10',
    [int]$TimeoutSeconds = 300
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$researchRoot = $PSScriptRoot
$packageRoot = Split-Path -Parent $researchRoot
$testerRoot = Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'
$terminal = Join-Path $testerRoot 'terminal64.exe'
$expertRoot = Join-Path $testerRoot 'MQL5\Experts\AAA Research\Robot Trading Playbook'
$setRoot = Join-Path $testerRoot 'MQL5\Profiles\Tester'
$configRoot = Join-Path $testerRoot 'backtest-configs\robot-playbook-training'
$testerReportRoot = Join-Path $testerRoot 'reports\robot-playbook-training'
$outputRoot = Join-Path $researchRoot 'Backtest Reports\Training'

foreach ($path in @($expertRoot,$setRoot,$configRoot,$testerReportRoot,$outputRoot)) {
    [void](New-Item -ItemType Directory -Path $path -Force)
}

Copy-Item -LiteralPath (Join-Path $researchRoot 'EA\Robot Trading Playbook EA.ex5') -Destination (Join-Path $expertRoot 'Robot Trading Playbook EA.ex5') -Force

$cases = New-Object System.Collections.Generic.List[object]
foreach ($timeframe in @('M15','M30')) {
    $periodValue = if ($timeframe -eq 'M15') { 15 } else { 30 }
    foreach ($lookback in @(8,12,20)) {
        foreach ($bias in @(@(20,50),@(50,200))) {
            foreach ($rr in @(1.0,1.5,2.0)) {
                $slug = ('{0}-lb{1}-ema{2}x{3}-rr{4}' -f $timeframe.ToLower(),$lookback,$bias[0],$bias[1],($rr.ToString('0.0').Replace('.','')))
                $cases.Add([pscustomobject]@{
                    Slug=$slug; Timeframe=$timeframe; PeriodValue=$periodValue; Lookback=$lookback;
                    Fast=$bias[0]; Slow=$bias[1]; RR=$rr
                })
            }
        }
    }
}

$manifest = New-Object System.Collections.Generic.List[object]
foreach ($case in $cases) {
    $setName = 'RTP TRAIN ' + $case.Slug + '.set'
    $setPath = Join-Path $setRoot $setName
    $set = @"
InpSignalTimeframe=$($case.PeriodValue)
InpRangeLookbackBars=$($case.Lookback)
InpBreakoutBufferATR=0.05
InpMaximumSignalRangeATR=2.5
InpAllowLong=true
InpAllowShort=true
InpUseBreakoutContinuation=true
InpUseStarterPlay=true
InpUseBreakoutRetest=true
InpUseFakeoutReclaim=true
InpSetupLifeBars=2
InpRetestToleranceATR=0.15
InpUseBiasFilter=true
InpBiasTimeframe=16388
InpBiasFastEMA=$($case.Fast)
InpBiasSlowEMA=$($case.Slow)
InpATRPeriod=14
InpEntryBufferATR=0.02
InpStopBufferATR=0.1
InpMinimumStopATR=0.4
InpMaximumStopATR=3
InpRewardRisk=$($case.RR.ToString([Globalization.CultureInfo]::InvariantCulture))
InpPendingExpiryBars=2
InpBreakEvenAtR=0
InpTrailingStartR=0
InpTrailingDistanceR=1
InpMaximumHoldingBars=16
InpEnableTrading=true
InpRiskPercent=1
InpMaximumSpreadATR=0.08
InpMagic=862508
InpMaximumDeviationPoints=50
"@
    [IO.File]::WriteAllText($setPath,$set,[Text.UTF8Encoding]::new($true))

    $configPath = Join-Path $configRoot ($case.Slug + '.ini')
    $reportPath = Join-Path $testerReportRoot ($case.Slug + '.htm')
    $relativeReport = 'reports\robot-playbook-training\' + $case.Slug + '.htm'
    $config = @"
[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=AAA Research\Robot Trading Playbook\Robot Trading Playbook EA
ExpertParameters=$setName
Symbol=XAUUSD
Period=$($case.Timeframe)
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
Report=$relativeReport
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"@
    [IO.File]::WriteAllText($configPath,$config,[Text.UTF8Encoding]::new($true))
    Get-ChildItem -LiteralPath $testerReportRoot -Filter ($case.Slug + '*') -ErrorAction SilentlyContinue | Remove-Item -Force

    Write-Host ("START {0}" -f $case.Slug) -ForegroundColor Cyan
    $process = Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"' + $configPath + '"')) -PassThru -WindowStyle Hidden
    try {
        Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop
    } catch {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        $manifest.Add(($case | Select-Object *,@{n='Status';e={'timeout'}},@{n='Report';e={$null}}))
        continue
    }
    if (-not (Test-Path -LiteralPath $reportPath)) {
        $manifest.Add(($case | Select-Object *,@{n='Status';e={'no-report'}},@{n='Report';e={$null}}))
        continue
    }
    Get-ChildItem -LiteralPath $testerReportRoot -Filter ($case.Slug + '*') | Copy-Item -Destination $outputRoot -Force
    $manifest.Add(($case | Select-Object *,@{n='Status';e={'complete'}},@{n='Report';e={Join-Path $outputRoot ($case.Slug + '.htm')}}))
    Write-Host ("DONE  {0}" -f $case.Slug) -ForegroundColor Green
}

$manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $outputRoot 'manifest.json') -Encoding utf8
Write-Host ("Completed {0} training cases." -f (($manifest | Where-Object Status -eq 'complete').Count)) -ForegroundColor Green
