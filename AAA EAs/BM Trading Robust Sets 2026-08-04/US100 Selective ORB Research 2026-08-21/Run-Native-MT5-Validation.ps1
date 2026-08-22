[CmdletBinding()]
param(
    [int]$Model = 4,
    [int]$TimeoutSeconds = 1200,
    [string]$CaseRegex = '',
    [string]$SetName = 'RESEARCH - US100 USTEC M5 - OR30 Retest RV - 1pct.set',
    [string]$RunTag = 'baseline'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$researchRoot = $PSScriptRoot
$packageRoot = Split-Path -Parent $researchRoot
$testerRoot = Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'
$terminal = Join-Path $testerRoot 'terminal64.exe'
$expertFolder = 'AAA Research\US100 Selective ORB'
$expertRoot = Join-Path $testerRoot ('MQL5\Experts\' + $expertFolder)
$setRoot = Join-Path $testerRoot 'MQL5\Profiles\Tester'
$configRoot = Join-Path $testerRoot ('backtest-configs\us100-selective-orb-' + $RunTag + '-20260821')
$testerReportRoot = Join-Path $testerRoot ('reports\us100-selective-orb-' + $RunTag + '-20260821')
$activeConfigRoot = 'C:\Users\hama101\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\config'
$isolatedConfigRoot = Join-Path $testerRoot 'Config'
$expertName = 'US100 Selective ORB Retest EA'

$cases = @(
    [pscustomobject]@{ Slug='training-2020-2023'; Label='Training'; From='2020.01.01'; To='2023.12.31' },
    [pscustomobject]@{ Slug='validation-2024-h1-2025'; Label='Validation'; From='2024.01.01'; To='2025.06.30' },
    [pscustomobject]@{ Slug='locked-2025h2-2026'; Label='Locked'; From='2025.07.01'; To='2026.08.20' },
    [pscustomobject]@{ Slug='one-year-2025-2026'; Label='One Year'; From='2025.08.21'; To='2026.08.20' },
    [pscustomobject]@{ Slug='full-2020-2026'; Label='Full'; From='2020.01.01'; To='2026.08.20' }
)
if ($CaseRegex) {
    $cases = @($cases | Where-Object Slug -Match $CaseRegex)
    if ($cases.Count -eq 0) { throw "CaseRegex selected no cases: $CaseRegex" }
}

foreach ($path in @($expertRoot,$setRoot,$configRoot,$testerReportRoot,$isolatedConfigRoot)) {
    [void](New-Item -ItemType Directory -Path $path -Force)
}
foreach ($case in $cases) {
    [void](New-Item -ItemType Directory -Path (Join-Path $researchRoot ('Backtest Reports\' + $RunTag + '\' + $case.Label)) -Force)
}
foreach ($name in @('accounts.dat','servers.dat','common.ini')) {
    Copy-Item -LiteralPath (Join-Path $activeConfigRoot $name) -Destination (Join-Path $isolatedConfigRoot $name) -Force
}
Copy-Item -LiteralPath (Join-Path $researchRoot ('EA\' + $expertName + '.ex5')) -Destination (Join-Path $expertRoot ($expertName + '.ex5')) -Force
Copy-Item -LiteralPath (Join-Path $researchRoot ('Sets\' + $SetName)) -Destination (Join-Path $setRoot $SetName) -Force

$manifest = New-Object System.Collections.Generic.List[object]
foreach ($case in $cases) {
    $outputRoot = Join-Path $researchRoot ('Backtest Reports\' + $RunTag + '\' + $case.Label)
    $configPath = Join-Path $configRoot ($case.Slug + '.ini')
    $reportPath = Join-Path $testerReportRoot ($case.Slug + '.htm')
    $relativeReport = 'reports\us100-selective-orb-' + $RunTag + '-20260821\' + $case.Slug + '.htm'
    $config = @"
[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=$expertFolder\$expertName
ExpertParameters=$SetName
Symbol=USTEC
Period=M5
Login=472334559
Deposit=10000
Currency=USD
Leverage=1:2000
Model=$Model
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
    Get-ChildItem -LiteralPath $testerReportRoot -Filter ($case.Slug + '*') -ErrorAction SilentlyContinue | Remove-Item -Force
    Write-Host ('START {0}: {1} to {2}' -f $case.Label,$case.From,$case.To) -ForegroundColor Cyan
    $process = Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"' + $configPath + '"')) -PassThru -WindowStyle Hidden
    try {
        Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop
    }
    catch {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        $manifest.Add([pscustomobject]@{Strategy='US100 Selective ORB';Slug=$case.Slug;Symbol='USTEC';Period='M5';Segment=$case.Label;FromDate=$case.From;ToDate=$case.To;Status='timeout';Report=$null})
        Write-Warning ('TIMEOUT ' + $case.Slug)
        continue
    }
    if (-not (Test-Path -LiteralPath $reportPath)) {
        $manifest.Add([pscustomobject]@{Strategy='US100 Selective ORB';Slug=$case.Slug;Symbol='USTEC';Period='M5';Segment=$case.Label;FromDate=$case.From;ToDate=$case.To;Status='no-report';Report=$null})
        Write-Warning ('NO REPORT ' + $case.Slug)
        continue
    }
    Get-ChildItem -LiteralPath $testerReportRoot -Filter ($case.Slug + '*') | Copy-Item -Destination $outputRoot -Force
    $copiedReport = Join-Path $outputRoot ($case.Slug + '.htm')
    $manifest.Add([pscustomobject]@{Strategy='US100 Selective ORB';Slug=$case.Slug;Symbol='USTEC';Period='M5';Segment=$case.Label;FromDate=$case.From;ToDate=$case.To;Status='complete';Report=$copiedReport})
    Write-Host ('DONE  ' + $case.Slug) -ForegroundColor Green
}

$manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $researchRoot ('native-' + $RunTag + '-manifest.json')) -Encoding utf8
$completedCount=@($manifest | Where-Object Status -eq 'complete').Count
Write-Host ('Completed {0} of {1} native tests.' -f $completedCount,@($cases).Count) -ForegroundColor Green
