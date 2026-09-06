[CmdletBinding()]
param(
    [ValidateSet('Full','Stress')]
    [string]$Stage = 'Full',
    [int]$TimeoutSeconds = 1200
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$researchRoot = $PSScriptRoot
$packageRoot = Split-Path -Parent $researchRoot
$testerRoot = Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'
$terminal = Join-Path $testerRoot 'terminal64.exe'
$expertFolder = 'AAA Research\News Pulse Hard 1p5 20260905'
$expertRoot = Join-Path $testerRoot ('MQL5\Experts\' + $expertFolder)
$setRoot = Join-Path $testerRoot 'MQL5\Profiles\Tester'
$stageId = 'news-pulse-hard-1p5-' + $Stage.ToLowerInvariant()
$configRoot = Join-Path $testerRoot ('backtest-configs\' + $stageId)
$testerReportRoot = Join-Path $testerRoot ('reports\' + $stageId)
$outputRoot = Join-Path $researchRoot ('Backtest Reports\Hard 1.5 ' + $Stage)
$sourceExpert = Join-Path $packageRoot 'AAA Final EAs\AAA Final News Pulse EA\AAA Final News Pulse EA.ex5'

foreach ($path in @($expertRoot,$setRoot,$configRoot,$testerReportRoot,$outputRoot)) {
    [void](New-Item -ItemType Directory -Path $path -Force)
}
foreach ($path in @($terminal,$sourceExpert)) {
    if (-not (Test-Path -LiteralPath $path)) { throw "Missing required file: $path" }
}
Copy-Item -LiteralPath $sourceExpert -Destination (Join-Path $expertRoot 'AAA Final News Pulse EA.ex5') -Force

$cases = @(
    [pscustomobject]@{ Id='xauusd'; Symbol='XAUUSD'; Magic=861301; Entry=6.0; Stop=6.0; Trail=15.0; Set='Selected Portfolio Settings 2026-09-01\12A News Pulse XAU Two Sided - HARD 1.5 TOTAL.set' },
    [pscustomobject]@{ Id='xagusd'; Symbol='XAGUSD'; Magic=861302; Entry=0.08; Stop=0.08; Trail=0.20; Set='Selected Portfolio Settings 2026-09-01\12B News Pulse XAG Two Sided - HARD 1.5 TOTAL.set' },
    [pscustomobject]@{ Id='eurusd'; Symbol='EURUSD'; Magic=861304; Entry=0.0006; Stop=0.0006; Trail=0.0015; Set='Selected Portfolio Settings 2026-09-01\12C News Pulse EURUSD Two Sided - HARD 1.5 TOTAL.set' }
)
$executionMode = if ($Stage -eq 'Stress') { -1 } else { 1 }
$manifest = [Collections.Generic.List[object]]::new()

foreach ($case in $cases) {
    $setPath = Join-Path $packageRoot $case.Set
    if (-not (Test-Path -LiteralPath $setPath)) { throw "Missing selected set: $setPath" }
    $caseId = $case.Id + '__two-sided__hard1p5__native60'
    $setName = 'News Pulse Hard 1p5 ' + $case.Id + '.set'
    Copy-Item -LiteralPath $setPath -Destination (Join-Path $setRoot $setName) -Force

    $relativeReport = 'reports\' + $stageId + '\' + $caseId + '.htm'
    $reportPath = Join-Path $testerReportRoot ($caseId + '.htm')
    $completedReport = Join-Path $outputRoot ($caseId + '.htm')
    $configPath = Join-Path $configRoot ($caseId + '.ini')
    $config = @"
[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=$expertFolder\AAA Final News Pulse EA
ExpertParameters=$setName
Symbol=$($case.Symbol)
Period=M1
Login=472334559
Deposit=10000
Currency=USD
Leverage=1:2000
Model=0
ExecutionMode=$executionMode
Optimization=0
FromDate=2025.09.01
ToDate=2026.09.01
ForwardMode=0
Report=$relativeReport
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"@
    [IO.File]::WriteAllText($configPath,$config,[Text.UTF8Encoding]::new($true))

    Get-ChildItem -LiteralPath $testerReportRoot -Filter ($caseId + '*') -ErrorAction SilentlyContinue | Remove-Item -Force
    Get-ChildItem -LiteralPath $outputRoot -Filter ($caseId + '*') -ErrorAction SilentlyContinue | Remove-Item -Force
    Write-Host ("START {0} / {1} / fixed 0.75% + 0.75%" -f $Stage,$case.Symbol) -ForegroundColor Cyan
    $process = Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"'+$configPath+'"')) -PassThru -WindowStyle Hidden
    try { Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop }
    catch { Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue; throw "TIMEOUT: $caseId" }
    if (-not (Test-Path -LiteralPath $reportPath)) { throw "No MT5 report produced for $caseId" }
    Get-ChildItem -LiteralPath $testerReportRoot -Filter ($caseId + '*') | Copy-Item -Destination $outputRoot -Force
    Write-Host ("DONE  {0} / {1}" -f $Stage,$case.Symbol) -ForegroundColor Green

    $manifest.Add([pscustomobject]@{
        case_id=$caseId; stage=$Stage; asset=$case.Id; symbol=$case.Symbol; period='M1';
        direction='two-sided'; geometry='optimized'; entry_offset=[double]$case.Entry;
        stop_distance=[double]$case.Stop; trail_distance=[double]$case.Trail;
        management='native60'; buy=$true; sell=$true; dynamic=$false; close_seconds=60;
        risk_per_enabled_side_pct=0.75; total_planned_event_risk_pct=1.50;
        from='2025.09.01'; to='2026.09.01'; execution_mode=$executionMode; report=$completedReport
    })
}

$manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $outputRoot 'manifest.json') -Encoding utf8
$python = (Get-Command python.exe -ErrorAction Stop).Source
& $python (Join-Path $researchRoot 'Analyze-News-Pulse-Hard-1p5.py') --stage $Stage
if ($LASTEXITCODE -ne 0) { throw 'News Pulse hard-1.5 analysis failed.' }
