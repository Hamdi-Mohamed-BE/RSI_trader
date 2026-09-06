[CmdletBinding()]
param(
    [ValidateSet('Calibration','Management','Locked','Full','Stress')]
    [string]$Stage = 'Calibration',
    [int]$TimeoutSeconds = 1200
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$researchRoot = $PSScriptRoot
$packageRoot = Split-Path -Parent $researchRoot
$testerRoot = Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'
$terminal = Join-Path $testerRoot 'terminal64.exe'
$testerLogin = '472334559'
$testerServer = 'Exness-MT5Trial16'
$expertFolder = 'AAA Research\News Pulse Multi Market 20260905'
$expertRoot = Join-Path $testerRoot ('MQL5\Experts\' + $expertFolder)
$setRoot = Join-Path $testerRoot 'MQL5\Profiles\Tester'
$configRoot = Join-Path $testerRoot ('backtest-configs\news-pulse-multi-' + $Stage.ToLowerInvariant())
$testerReportRoot = Join-Path $testerRoot ('reports\news-pulse-multi-' + $Stage.ToLowerInvariant())
$outputRoot = Join-Path $researchRoot ('Backtest Reports\' + $Stage)
$localSetRoot = Join-Path $researchRoot 'Sets'
$sourceExpert = Join-Path $packageRoot 'AAA Final EAs\AAA Final News Pulse EA\AAA Final News Pulse EA.ex5'
$baseSet = Join-Path $packageRoot 'Selected Portfolio Settings 2026-09-01\12 News Pulse Long Only - DYNAMIC 50-20 - ALL DAY.set'

foreach ($path in @($expertRoot,$setRoot,$configRoot,$testerReportRoot,$outputRoot,$localSetRoot)) {
    [void](New-Item -ItemType Directory -Path $path -Force)
}
foreach ($path in @($terminal,$sourceExpert,$baseSet)) {
    if (-not (Test-Path -LiteralPath $path)) { throw "Missing required file: $path" }
}
Copy-Item -LiteralPath $sourceExpert -Destination (Join-Path $expertRoot 'AAA Final News Pulse EA.ex5') -Force

$assets = @(
    [pscustomobject]@{ Id='xauusd'; Symbol='XAUUSD'; Period='M1'; Magic=861301; Geometries=@(
        [pscustomobject]@{Id='base'; Entry=6.0; Stop=6.0; Trail=15.0},
        [pscustomobject]@{Id='wide'; Entry=8.0; Stop=8.0; Trail=20.0}) },
    [pscustomobject]@{ Id='xagusd'; Symbol='XAGUSD'; Period='M1'; Magic=861302; Geometries=@(
        [pscustomobject]@{Id='tight'; Entry=0.08; Stop=0.08; Trail=0.20},
        [pscustomobject]@{Id='wide'; Entry=0.12; Stop=0.12; Trail=0.30}) },
    [pscustomobject]@{ Id='ustec'; Symbol='USTEC'; Period='M1'; Magic=861303; Geometries=@(
        [pscustomobject]@{Id='tight'; Entry=30.0; Stop=30.0; Trail=75.0},
        [pscustomobject]@{Id='wide'; Entry=60.0; Stop=60.0; Trail=150.0}) },
    [pscustomobject]@{ Id='eurusd'; Symbol='EURUSD'; Period='M1'; Magic=861304; Geometries=@(
        [pscustomobject]@{Id='tight'; Entry=0.0006; Stop=0.0006; Trail=0.0015},
        [pscustomobject]@{Id='wide'; Entry=0.0010; Stop=0.0010; Trail=0.0025}) },
    [pscustomobject]@{ Id='btcusd'; Symbol='BTCUSD'; Period='M1'; Magic=861305; Geometries=@(
        [pscustomobject]@{Id='tight'; Entry=150.0; Stop=150.0; Trail=375.0},
        [pscustomobject]@{Id='wide'; Entry=300.0; Stop=300.0; Trail=750.0}) }
)
$management = @(
    [pscustomobject]@{ Id='native60'; Dynamic=$false; CloseSeconds=60 },
    [pscustomobject]@{ Id='dynamic60'; Dynamic=$true; CloseSeconds=60 },
    [pscustomobject]@{ Id='dynamic90'; Dynamic=$true; CloseSeconds=90 }
)
$directions = @(
    [pscustomobject]@{ Id='buy-only'; Buy=$true; Sell=$false },
    [pscustomobject]@{ Id='sell-only'; Buy=$false; Sell=$true },
    [pscustomobject]@{ Id='two-sided'; Buy=$true; Sell=$true }
)

$developmentPeriod = @{ From='2025.09.01'; To='2026.05.31'; Execution=1 }
if ($Stage -eq 'Calibration') {
    $period = $developmentPeriod
    $cases = foreach ($asset in $assets) {
        foreach ($direction in $directions) {
            foreach ($geometry in $asset.Geometries) {
                [pscustomobject]@{ Asset=$asset; Direction=$direction; Geometry=$geometry; Management=($management | Where-Object Id -eq 'dynamic60') }
            }
        }
    }
} elseif ($Stage -eq 'Management') {
    $period = $developmentPeriod
    $selectionPath = Join-Path $researchRoot 'CALIBRATION SELECTION.json'
    if (-not (Test-Path -LiteralPath $selectionPath)) { throw 'Run Calibration first; CALIBRATION SELECTION.json is missing.' }
    $selection = Get-Content -Raw -LiteralPath $selectionPath | ConvertFrom-Json
    $cases = foreach ($pick in $selection) {
        $asset = $assets | Where-Object { $_.Id -eq $pick.asset } | Select-Object -First 1
        $direction = $directions | Where-Object { $_.Id -eq $pick.direction } | Select-Object -First 1
        if ($null -eq $asset -or $null -eq $direction) { throw "Invalid calibrated selection for $($pick.asset)." }
        $geometry = $asset.Geometries | Where-Object { $_.Id -eq $pick.geometry } | Select-Object -First 1
        foreach ($exit in $management) {
            [pscustomobject]@{ Asset=$asset; Direction=$direction; Geometry=$geometry; Management=$exit }
        }
    }
} else {
    $period = if ($Stage -eq 'Locked') {
        @{ From='2026.06.01'; To='2026.09.01'; Execution=1 }
    } elseif ($Stage -eq 'Stress') {
        @{ From='2025.09.01'; To='2026.09.01'; Execution=-1 }
    } else {
        @{ From='2025.09.01'; To='2026.09.01'; Execution=1 }
    }
    $selectionPath = Join-Path $researchRoot 'DEVELOPMENT SELECTION.json'
    if (-not (Test-Path -LiteralPath $selectionPath)) { throw 'Run Management first; DEVELOPMENT SELECTION.json is missing.' }
    $selection = Get-Content -Raw -LiteralPath $selectionPath | ConvertFrom-Json
    $cases = foreach ($pick in $selection) {
        $asset = $assets | Where-Object { $_.Id -eq $pick.asset } | Select-Object -First 1
        $direction = $directions | Where-Object { $_.Id -eq $pick.direction } | Select-Object -First 1
        if ($null -eq $asset -or $null -eq $direction) { throw "Invalid development selection for $($pick.asset)." }
        $geometry = $asset.Geometries | Where-Object { $_.Id -eq $pick.geometry } | Select-Object -First 1
        $exit = $management | Where-Object { $_.Id -eq $pick.management } | Select-Object -First 1
        [pscustomobject]@{ Asset=$asset; Direction=$direction; Geometry=$geometry; Management=$exit }
    }
}

function BoolText([bool]$value) { if ($value) { 'true' } else { 'false' } }
function Invariant([double]$value) { $value.ToString('0.########',[Globalization.CultureInfo]::InvariantCulture) }
function Upsert-Input([string]$text,[string]$key,[string]$value) {
    $pattern = '(?m)^' + [regex]::Escape($key) + '=.*$'
    if ([regex]::IsMatch($text,$pattern)) { return [regex]::Replace($text,$pattern,($key+'='+$value)) }
    return $text.TrimEnd() + "`r`n" + $key + '=' + $value + "`r`n"
}

$manifest = [Collections.Generic.List[object]]::new()
foreach ($case in $cases) {
    $asset=$case.Asset; $direction=$case.Direction; $geometry=$case.Geometry; $exit=$case.Management
    $caseId = ($asset.Id+'__'+$direction.Id+'__'+$geometry.Id+'__'+$exit.Id).ToLowerInvariant()
    $setName = 'News Pulse Multi ' + $caseId + '.set'
    $setText = Get-Content -Raw -LiteralPath $baseSet
    $setText = Upsert-Input $setText 'InpEnableBuySide' (BoolText $direction.Buy)
    $setText = Upsert-Input $setText 'InpEnableSellSide' (BoolText $direction.Sell)
    $setText = Upsert-Input $setText 'InpUseDynamicTrailingSL' (BoolText $exit.Dynamic)
    $setText = Upsert-Input $setText 'InpDynamicTriggerFraction' '0.50'
    $setText = Upsert-Input $setText 'InpDynamicLockFraction' '0.20'
    $setText = Upsert-Input $setText 'InpForceCloseSecondsAfterEvent' ([string]$exit.CloseSeconds)
    $setText = Upsert-Input $setText 'InpEntryOffsetPrice' (Invariant $geometry.Entry)
    $setText = Upsert-Input $setText 'InpStopLossPrice' (Invariant $geometry.Stop)
    $setText = Upsert-Input $setText 'InpTrailDistancePrice' (Invariant $geometry.Trail)
    $setText = Upsert-Input $setText 'InpRiskPercent' '1'
    $setText = Upsert-Input $setText 'InpMagic' ([string]$asset.Magic)
    [IO.File]::WriteAllText((Join-Path $setRoot $setName),$setText,[Text.UTF8Encoding]::new($false))
    [IO.File]::WriteAllText((Join-Path $localSetRoot $setName),$setText,[Text.UTF8Encoding]::new($false))

    $relativeReport = 'reports\news-pulse-multi-' + $Stage.ToLowerInvariant() + '\' + $caseId + '.htm'
    $reportPath = Join-Path $testerReportRoot ($caseId + '.htm')
    $completedReport = Join-Path $outputRoot ($caseId + '.htm')
    $configPath = Join-Path $configRoot ($caseId + '.ini')
    $config = @"
[Common]
Login=$testerLogin
Server=$testerServer

[Tester]
Expert=$expertFolder\AAA Final News Pulse EA
ExpertParameters=$setName
Symbol=$($asset.Symbol)
Period=$($asset.Period)
Login=$testerLogin
Deposit=10000
Currency=USD
Leverage=1:2000
Model=0
ExecutionMode=$($period.Execution)
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

    if (-not (Test-Path -LiteralPath $completedReport)) {
        Get-ChildItem -LiteralPath $testerReportRoot -Filter ($caseId+'*') -ErrorAction SilentlyContinue | Remove-Item -Force
        Write-Host ("START {0} / {1} / {2} / {3} / {4}" -f $Stage,$asset.Symbol,$direction.Id,$geometry.Id,$exit.Id) -ForegroundColor Cyan
        $process = Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"'+$configPath+'"')) -PassThru -WindowStyle Hidden
        try { Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop }
        catch { Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue; throw "TIMEOUT: $caseId" }
        if (-not (Test-Path -LiteralPath $reportPath)) { throw "No MT5 report produced for $caseId" }
        Get-ChildItem -LiteralPath $testerReportRoot -Filter ($caseId+'*') | Copy-Item -Destination $outputRoot -Force
        Write-Host ("DONE  {0} / {1} / {2} / {3} / {4}" -f $Stage,$asset.Symbol,$direction.Id,$geometry.Id,$exit.Id) -ForegroundColor Green
    } else {
        Write-Host ("SKIP  {0} / {1} / {2} / {3} / {4}" -f $Stage,$asset.Symbol,$direction.Id,$geometry.Id,$exit.Id) -ForegroundColor DarkGray
    }
    $manifest.Add([pscustomobject]@{
        case_id=$caseId; stage=$Stage; asset=$asset.Id; symbol=$asset.Symbol; period=$asset.Period;
        direction=$direction.Id; geometry=$geometry.Id; entry_offset=[double]$geometry.Entry;
        stop_distance=[double]$geometry.Stop; trail_distance=[double]$geometry.Trail;
        management=$exit.Id; buy=[bool]$direction.Buy; sell=[bool]$direction.Sell;
        dynamic=[bool]$exit.Dynamic; close_seconds=[int]$exit.CloseSeconds;
        risk_per_enabled_side_pct=1.0; from=$period.From; to=$period.To;
        execution_mode=[int]$period.Execution; report=$completedReport
    })
}
$manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $outputRoot 'manifest.json') -Encoding utf8

$python = (Get-Command python.exe -ErrorAction Stop).Source
& $python (Join-Path $researchRoot 'Analyze-News-Pulse-Multi.py') --stage $Stage
if ($LASTEXITCODE -ne 0) { throw 'News Pulse analysis failed.' }
