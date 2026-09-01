[CmdletBinding()]
param(
    [ValidateSet('Development','Locked')]
    [string]$Stage = 'Development',
    [int]$TimeoutSeconds = 1200
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$researchRoot = $PSScriptRoot
$packageRoot = Split-Path -Parent $researchRoot
$testerRoot = Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'
$terminal = Join-Path $testerRoot 'terminal64.exe'
$expertFolder = 'AAA Research\P Continuation 20260831'
$expertName = 'P Continuation Failed Auction EA'
$expertRoot = Join-Path $testerRoot ('MQL5\Experts\' + $expertFolder)
$setRoot = Join-Path $testerRoot 'MQL5\Profiles\Tester'
$runSlug = 'p-continuation-' + $Stage.ToLowerInvariant()
$configRoot = Join-Path $testerRoot ('backtest-configs\' + $runSlug)
$testerReportRoot = Join-Path $testerRoot ('reports\' + $runSlug)
$outputRoot = Join-Path $researchRoot ('Backtest Reports\' + $Stage)
$localSetRoot = Join-Path $researchRoot 'Sets'
$activeConfigRoot = 'C:\Users\hama101\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\config'
$isolatedConfigRoot = Join-Path $testerRoot 'Config'

foreach ($path in @($expertRoot,$setRoot,$configRoot,$testerReportRoot,$outputRoot,$localSetRoot,$isolatedConfigRoot)) {
    [void](New-Item -ItemType Directory -Path $path -Force)
}
foreach ($name in @('accounts.dat','servers.dat','common.ini')) {
    Copy-Item -LiteralPath (Join-Path $activeConfigRoot $name) -Destination (Join-Path $isolatedConfigRoot $name) -Force
}
Copy-Item -LiteralPath (Join-Path $researchRoot ('EA\' + $expertName + '.ex5')) -Destination (Join-Path $expertRoot ($expertName + '.ex5')) -Force

$symbols = @('XAUUSD','XAGUSD','US30','USTEC','BTCUSD')
$variants = @(
    [pscustomobject]@{Id='m5-impulse-target';TF=5;Period='M5';ImpulseBars=3;MinImpulse=2.0;Efficiency=.65;MinBox=4;MaxBox=10;MaxBoxATR=1.20;Wait=12;MinSweep=.03;MaxSweep=.60;Reject=.60;Volume=1.00;Target=1;RR=2.0;BE=$true;Hold=36},
    [pscustomobject]@{Id='m5-rr15';TF=5;Period='M5';ImpulseBars=3;MinImpulse=2.0;Efficiency=.65;MinBox=4;MaxBox=10;MaxBoxATR=1.20;Wait=12;MinSweep=.03;MaxSweep=.60;Reject=.60;Volume=1.00;Target=0;RR=1.5;BE=$true;Hold=36},
    [pscustomobject]@{Id='m5-rr20';TF=5;Period='M5';ImpulseBars=3;MinImpulse=2.0;Efficiency=.65;MinBox=4;MaxBox=10;MaxBoxATR=1.20;Wait=12;MinSweep=.03;MaxSweep=.60;Reject=.60;Volume=1.00;Target=0;RR=2.0;BE=$true;Hold=36},
    [pscustomobject]@{Id='m5-absorption-rr20';TF=5;Period='M5';ImpulseBars=3;MinImpulse=2.0;Efficiency=.65;MinBox=4;MaxBox=10;MaxBoxATR=1.20;Wait=10;MinSweep=.03;MaxSweep=.55;Reject=.65;Volume=1.25;Target=0;RR=2.0;BE=$true;Hold=36},
    [pscustomobject]@{Id='m1-rr15';TF=1;Period='M1';ImpulseBars=5;MinImpulse=2.2;Efficiency=.65;MinBox=6;MaxBox=15;MaxBoxATR=1.35;Wait=15;MinSweep=.03;MaxSweep=.60;Reject=.60;Volume=1.00;Target=0;RR=1.5;BE=$true;Hold=60},
    [pscustomobject]@{Id='m15-rr20';TF=15;Period='M15';ImpulseBars=2;MinImpulse=1.8;Efficiency=.60;MinBox=3;MaxBox=7;MaxBoxATR=1.10;Wait=8;MinSweep=.03;MaxSweep=.60;Reject=.60;Volume=1.00;Target=0;RR=2.0;BE=$true;Hold=20}
)

if ($Stage -eq 'Development') {
    $period = @{From='2022.01.01';To='2025.08.27';Model=1}
    $cases = foreach ($symbol in $symbols) { foreach ($variant in $variants) { [pscustomobject]@{Symbol=$symbol;Variant=$variant} } }
} else {
    $period = @{From='2025.08.28';To='2026.08.27';Model=0}
    $selectionPath = Join-Path $researchRoot 'selection.json'
    if (-not (Test-Path -LiteralPath $selectionPath)) { throw 'Run Development first; selection.json is missing.' }
    $selection = Get-Content -Raw -LiteralPath $selectionPath | ConvertFrom-Json
    $cases = foreach ($pick in $selection) {
        $variant = $variants | Where-Object Id -eq $pick.variant | Select-Object -First 1
        if ($null -eq $variant) { throw "Unknown selected variant $($pick.variant)" }
        [pscustomobject]@{Symbol=[string]$pick.symbol;Variant=$variant}
    }
}

function Render-Bool([bool]$Value) { if ($Value) { 'true' } else { 'false' } }
function New-SetText($case, [int]$magic) {
    $v = $case.Variant
    @"
InpTimeframe=$($v.TF)
InpATRPeriod=14
InpImpulseBars=$($v.ImpulseBars)
InpMinimumImpulseATR=$($v.MinImpulse)
InpMinimumDirectionalEfficiency=$($v.Efficiency)
InpMinimumConsolidationBars=$($v.MinBox)
InpMaximumConsolidationBars=$($v.MaxBox)
InpMaximumConsolidationATR=$($v.MaxBoxATR)
InpAcceptanceLocation=0.65
InpProfileBins=24
InpValueAreaPercent=70.0
InpMaximumBarsAfterAcceptance=$($v.Wait)
InpMinimumSweepATR=$($v.MinSweep)
InpMaximumSweepATR=$($v.MaxSweep)
InpMinimumRejectionClose=$($v.Reject)
InpVolumeAverageBars=20
InpMinimumVolumeRatio=$($v.Volume)
InpStopBufferATR=0.10
InpTargetMode=$($v.Target)
InpRewardRisk=$($v.RR)
InpMinimumImpulseTargetR=1.0
InpMaximumImpulseTargetR=4.0
InpUseBreakEven=$(Render-Bool $v.BE)
InpBreakEvenAtR=1.0
InpMaximumHoldingBars=$($v.Hold)
InpAllowLong=true
InpAllowShort=true
InpRiskPercent=1.0
InpMaximumSpreadATR=0.0
InpMagic=$magic
InpMaximumDeviationPoints=50
"@
}

$manifest = [Collections.Generic.List[object]]::new()
$index = 0
foreach ($case in $cases) {
    $index++
    $symbol = $case.Symbol
    $variant = $case.Variant
    $caseId = ($symbol + '__' + $variant.Id).ToLowerInvariant()
    $setName = ('P CONTINUATION {0} {1} {2}.set' -f $Stage.ToUpperInvariant(),$symbol,$variant.Id)
    $setText = New-SetText $case (863310 + $index)
    [IO.File]::WriteAllText((Join-Path $setRoot $setName),$setText,[Text.UTF8Encoding]::new($false))
    [IO.File]::WriteAllText((Join-Path $localSetRoot $setName),$setText,[Text.UTF8Encoding]::new($false))

    $configPath = Join-Path $configRoot ($caseId + '.ini')
    $reportPath = Join-Path $testerReportRoot ($caseId + '.htm')
    $relativeReport = 'reports\{0}\{1}.htm' -f $runSlug,$caseId
    $config = @"
[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=$expertFolder\$expertName
ExpertParameters=$setName
Symbol=$symbol
Period=$($variant.Period)
Login=472334559
Deposit=10000
Currency=USD
Leverage=1:2000
Model=$($period.Model)
ExecutionMode=1
Optimization=0
FromDate=$($period.From)
ToDate=$($period.To)
ForwardMode=0
Report=$relativeReport
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"@
    [IO.File]::WriteAllText($configPath,$config,[Text.UTF8Encoding]::new($true))
    Get-ChildItem -LiteralPath $testerReportRoot -Filter ($caseId + '*') -ErrorAction SilentlyContinue | Remove-Item -Force
    Write-Host ('START {0} {1} {2} to {3}' -f $symbol,$variant.Id,$period.From,$period.To) -ForegroundColor Cyan
    $process = Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"' + $configPath + '"')) -PassThru -WindowStyle Hidden
    try { Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop }
    catch { Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue; throw "TIMEOUT $caseId" }
    if (-not (Test-Path -LiteralPath $reportPath)) { throw "NO REPORT $caseId" }
    Get-ChildItem -LiteralPath $testerReportRoot -Filter ($caseId + '*') | Copy-Item -Destination $outputRoot -Force
    $manifest.Add([pscustomobject]@{Symbol=$symbol;Variant=$variant.Id;Stage=$Stage;From=$period.From;To=$period.To;Model=$period.Model;Report=(Join-Path $outputRoot ($caseId+'.htm'))})
}

$manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $outputRoot 'manifest.json') -Encoding utf8
$python = (Get-Command python.exe -ErrorAction Stop).Source
& $python (Join-Path $researchRoot 'Analyze-Reports.py') $outputRoot (Join-Path $researchRoot ($Stage.ToLowerInvariant() + '-results'))
if ($LASTEXITCODE -ne 0) { throw 'Report analysis failed.' }
Write-Host ('Completed ' + $Stage + ' research tests.') -ForegroundColor Green
