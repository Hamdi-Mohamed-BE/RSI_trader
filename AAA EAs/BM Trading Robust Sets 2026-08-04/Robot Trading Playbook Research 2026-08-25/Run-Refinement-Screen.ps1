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
$configRoot = Join-Path $testerRoot 'backtest-configs\robot-playbook-refinement'
$testerReportRoot = Join-Path $testerRoot 'reports\robot-playbook-refinement'
$outputRoot = Join-Path $researchRoot 'Backtest Reports\Refinement'
foreach ($path in @($expertRoot,$setRoot,$configRoot,$testerReportRoot,$outputRoot)) {
    [void](New-Item -ItemType Directory -Path $path -Force)
}
Copy-Item -LiteralPath (Join-Path $researchRoot 'EA\Robot Trading Playbook EA.ex5') -Destination (Join-Path $expertRoot 'Robot Trading Playbook EA.ex5') -Force

$families = @(
    [pscustomobject]@{Name='breakout';Continuation='true';Starter='false';Retest='false';Fakeout='false'},
    [pscustomobject]@{Name='breakoutplus';Continuation='true';Starter='true';Retest='true';Fakeout='false'},
    [pscustomobject]@{Name='fakeout';Continuation='false';Starter='false';Retest='false';Fakeout='true'},
    [pscustomobject]@{Name='all';Continuation='true';Starter='true';Retest='true';Fakeout='true'}
)
$management = @(
    [pscustomobject]@{Name='fixed';BreakEven=0;TrailStart=0;TrailDistance=1},
    [pscustomobject]@{Name='be1';BreakEven=1;TrailStart=0;TrailDistance=1},
    [pscustomobject]@{Name='trail15';BreakEven=1;TrailStart=1.5;TrailDistance=0.75}
)
$manifest = New-Object System.Collections.Generic.List[object]
foreach ($family in $families) {
    foreach ($manage in $management) {
        $slug = $family.Name + '-' + $manage.Name
        $setName = 'RTP REFINE ' + $slug + '.set'
        $setPath = Join-Path $setRoot $setName
        $set = @"
InpSignalTimeframe=30
InpRangeLookbackBars=20
InpBreakoutBufferATR=0.05
InpMaximumSignalRangeATR=2.5
InpAllowLong=true
InpAllowShort=true
InpUseBreakoutContinuation=$($family.Continuation)
InpUseStarterPlay=$($family.Starter)
InpUseBreakoutRetest=$($family.Retest)
InpUseFakeoutReclaim=$($family.Fakeout)
InpSetupLifeBars=2
InpRetestToleranceATR=0.15
InpUseBiasFilter=true
InpBiasTimeframe=16388
InpBiasFastEMA=50
InpBiasSlowEMA=200
InpATRPeriod=14
InpEntryBufferATR=0.02
InpStopBufferATR=0.1
InpMinimumStopATR=0.4
InpMaximumStopATR=3
InpRewardRisk=1.5
InpPendingExpiryBars=2
InpBreakEvenAtR=$($manage.BreakEven)
InpTrailingStartR=$($manage.TrailStart)
InpTrailingDistanceR=$($manage.TrailDistance)
InpMaximumHoldingBars=16
InpEnableTrading=true
InpRiskPercent=1
InpMaximumSpreadATR=0.08
InpMagic=862508
InpMaximumDeviationPoints=50
"@
        [IO.File]::WriteAllText($setPath,$set,[Text.UTF8Encoding]::new($true))
        $configPath = Join-Path $configRoot ($slug + '.ini')
        $reportPath = Join-Path $testerReportRoot ($slug + '.htm')
        $relativeReport = 'reports\robot-playbook-refinement\' + $slug + '.htm'
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
        Get-ChildItem -LiteralPath $testerReportRoot -Filter ($slug + '*') -ErrorAction SilentlyContinue | Remove-Item -Force
        Write-Host ("START {0}" -f $slug) -ForegroundColor Cyan
        $process = Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"' + $configPath + '"')) -PassThru -WindowStyle Hidden
        try {
            Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop
        } catch {
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            $manifest.Add([pscustomobject]@{Slug=$slug;Family=$family.Name;Management=$manage.Name;Status='timeout';Report=$null})
            continue
        }
        if (-not (Test-Path -LiteralPath $reportPath)) {
            $manifest.Add([pscustomobject]@{Slug=$slug;Family=$family.Name;Management=$manage.Name;Status='no-report';Report=$null})
            continue
        }
        Get-ChildItem -LiteralPath $testerReportRoot -Filter ($slug + '*') | Copy-Item -Destination $outputRoot -Force
        $manifest.Add([pscustomobject]@{Slug=$slug;Family=$family.Name;Management=$manage.Name;Status='complete';Report=(Join-Path $outputRoot ($slug + '.htm'))})
        Write-Host ("DONE  {0}" -f $slug) -ForegroundColor Green
    }
}
$manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $outputRoot 'manifest.json') -Encoding utf8
Write-Host ("Completed {0} refinement cases." -f (($manifest | Where-Object Status -eq 'complete').Count)) -ForegroundColor Green
