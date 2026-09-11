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
$expertFolder = 'AAA Research\News Pulse Hard 1p5 20260905'
$expertPath = Join-Path $testerRoot ('MQL5\Experts\' + $expertFolder + '\AAA Final News Pulse EA.ex5')
$setRoot = Join-Path $testerRoot 'MQL5\Profiles\Tester'
$configRoot = Join-Path $testerRoot ('backtest-configs\news-pulse-crypto-' + $Stage.ToLowerInvariant())
$testerReportRoot = Join-Path $testerRoot ('reports\news-pulse-crypto-' + $Stage.ToLowerInvariant())
$outputRoot = Join-Path $researchRoot ('Backtest Reports\' + $Stage)
$localSetRoot = Join-Path $researchRoot 'Sets'
$baseSet = Join-Path $packageRoot 'Selected Portfolio Settings 2026-09-01\12A News Pulse XAU Two Sided - HARD 1.5 TOTAL.set'

foreach ($path in @($setRoot,$configRoot,$testerReportRoot,$outputRoot,$localSetRoot)) {
    [void](New-Item -ItemType Directory -Path $path -Force)
}
foreach ($path in @($terminal,$expertPath,$baseSet)) {
    if (-not (Test-Path -LiteralPath $path)) { throw "Missing required file: $path" }
}

function Geometry([string]$id,[double]$entry,[double]$stop) {
    [pscustomobject]@{ Id=$id; Entry=$entry; Stop=$stop; Trail=(2.5*$stop) }
}

$assets = @(
    [pscustomobject]@{ Id='btcusd'; Symbol='BTCUSD'; Magic=861305; Geometries=@(
        (Geometry 'e75-s75' 75 75),
        (Geometry 'e100-s100' 100 100),
        (Geometry 'e150-s100' 150 100),
        (Geometry 'e150-s150' 150 150),
        (Geometry 'e200-s150' 200 150),
        (Geometry 'e225-s225' 225 225),
        (Geometry 'e300-s300' 300 300),
        (Geometry 'e450-s300' 450 300)
    )},
    [pscustomobject]@{ Id='ethusd'; Symbol='ETHUSD'; Magic=861306; Geometries=@(
        (Geometry 'e3-s3' 3 3),
        (Geometry 'e4-s4' 4 4),
        (Geometry 'e6-s4' 6 4),
        (Geometry 'e6-s6' 6 6),
        (Geometry 'e8-s6' 8 6),
        (Geometry 'e9-s9' 9 9),
        (Geometry 'e12-s12' 12 12),
        (Geometry 'e18-s12' 18 12)
    )}
)
$directions = @(
    [pscustomobject]@{ Id='buy-only'; Buy=$true; Sell=$false },
    [pscustomobject]@{ Id='sell-only'; Buy=$false; Sell=$true },
    [pscustomobject]@{ Id='two-sided'; Buy=$true; Sell=$true }
)
$defaultManagement = [pscustomobject]@{ Id='lead30-close60-trail250'; Lead=30; Close=60; TrailFactor=2.5; Dynamic=$false }
$management = @(
    [pscustomobject]@{ Id='lead15-close60-trail250'; Lead=15; Close=60; TrailFactor=2.5; Dynamic=$false },
    [pscustomobject]@{ Id='lead30-close30-trail250'; Lead=30; Close=30; TrailFactor=2.5; Dynamic=$false },
    [pscustomobject]@{ Id='lead30-close60-trail150'; Lead=30; Close=60; TrailFactor=1.5; Dynamic=$false },
    $defaultManagement,
    [pscustomobject]@{ Id='lead30-close60-trail400'; Lead=30; Close=60; TrailFactor=4.0; Dynamic=$false },
    [pscustomobject]@{ Id='lead30-close90-trail250'; Lead=30; Close=90; TrailFactor=2.5; Dynamic=$false },
    [pscustomobject]@{ Id='lead60-close60-trail250'; Lead=60; Close=60; TrailFactor=2.5; Dynamic=$false },
    [pscustomobject]@{ Id='lead30-close60-dynamic'; Lead=30; Close=60; TrailFactor=2.5; Dynamic=$true }
)

$development = @{ From='2025.09.01'; To='2026.05.31'; Execution=1 }
if ($Stage -eq 'Calibration') {
    $period = $development
    $cases = foreach ($asset in $assets) {
        foreach ($direction in $directions) {
            foreach ($geometry in $asset.Geometries) {
                [pscustomobject]@{ Asset=$asset; Direction=$direction; Geometry=$geometry; Management=$defaultManagement }
            }
        }
    }
} elseif ($Stage -eq 'Management') {
    $period = $development
    $selectionPath = Join-Path $researchRoot 'CALIBRATION SELECTION.json'
    if (-not (Test-Path -LiteralPath $selectionPath)) { throw 'Run Calibration first.' }
    $selection = Get-Content -Raw -LiteralPath $selectionPath | ConvertFrom-Json
    $cases = foreach ($pick in $selection) {
        $asset = $assets | Where-Object Id -eq $pick.asset | Select-Object -First 1
        $direction = $directions | Where-Object Id -eq $pick.direction | Select-Object -First 1
        $geometry = $asset.Geometries | Where-Object Id -eq $pick.geometry | Select-Object -First 1
        foreach ($manage in $management) {
            [pscustomobject]@{ Asset=$asset; Direction=$direction; Geometry=$geometry; Management=$manage }
        }
    }
} else {
    $selectionPath = Join-Path $researchRoot 'DEVELOPMENT SELECTION.json'
    if (-not (Test-Path -LiteralPath $selectionPath)) { throw 'Run Management first.' }
    $selection = Get-Content -Raw -LiteralPath $selectionPath | ConvertFrom-Json
    $period = if ($Stage -eq 'Locked') {
        @{ From='2026.06.01'; To='2026.09.01'; Execution=1 }
    } elseif ($Stage -eq 'Stress') {
        @{ From='2025.09.01'; To='2026.09.01'; Execution=-1 }
    } else {
        @{ From='2025.09.01'; To='2026.09.01'; Execution=1 }
    }
    $cases = foreach ($pick in $selection) {
        $asset = $assets | Where-Object Id -eq $pick.asset | Select-Object -First 1
        $direction = $directions | Where-Object Id -eq $pick.direction | Select-Object -First 1
        $geometry = $asset.Geometries | Where-Object Id -eq $pick.geometry | Select-Object -First 1
        $manage = $management | Where-Object Id -eq $pick.management | Select-Object -First 1
        [pscustomobject]@{ Asset=$asset; Direction=$direction; Geometry=$geometry; Management=$manage }
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
    $asset=$case.Asset; $direction=$case.Direction; $geometry=$case.Geometry; $manage=$case.Management
    $caseId = ($asset.Id+'__'+$direction.Id+'__'+$geometry.Id+'__'+$manage.Id).ToLowerInvariant()
    $setName = 'News Pulse Crypto ' + $caseId + '.set'
    $setText = Get-Content -Raw -LiteralPath $baseSet
    $setText = Upsert-Input $setText 'InpEnableBuySide' (BoolText $direction.Buy)
    $setText = Upsert-Input $setText 'InpEnableSellSide' (BoolText $direction.Sell)
    $setText = Upsert-Input $setText 'InpRiskPercent' '0.75'
    $setText = Upsert-Input $setText 'InpMagic' ([string]$asset.Magic)
    $setText = Upsert-Input $setText 'InpPlacementLeadSeconds' ([string]$manage.Lead)
    $setText = Upsert-Input $setText 'InpEntryOffsetPrice' (Invariant $geometry.Entry)
    $setText = Upsert-Input $setText 'InpStopLossPrice' (Invariant $geometry.Stop)
    $setText = Upsert-Input $setText 'InpTrailStartR' '1.5'
    $setText = Upsert-Input $setText 'InpTrailDistancePrice' (Invariant ([double]$geometry.Stop*[double]$manage.TrailFactor))
    $setText = Upsert-Input $setText 'InpForceCloseSecondsAfterEvent' ([string]$manage.Close)
    $setText = Upsert-Input $setText 'InpUseDynamicTrailingSL' (BoolText $manage.Dynamic)
    $setText = Upsert-Input $setText 'InpDynamicTriggerFraction' '0.50'
    $setText = Upsert-Input $setText 'InpDynamicLockFraction' '0.20'
    [IO.File]::WriteAllText((Join-Path $setRoot $setName),$setText,[Text.UTF8Encoding]::new($false))
    [IO.File]::WriteAllText((Join-Path $localSetRoot $setName),$setText,[Text.UTF8Encoding]::new($false))

    $relativeReport = 'reports\news-pulse-crypto-' + $Stage.ToLowerInvariant() + '\' + $caseId + '.htm'
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
Symbol=$($asset.Symbol)
Period=M1
Login=472334559
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
        Write-Host ("START {0} / {1}" -f $Stage,$caseId) -ForegroundColor Cyan
        $process = Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"'+$configPath+'"')) -PassThru -WindowStyle Hidden
        try { Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop }
        catch { Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue; throw "TIMEOUT: $caseId" }
        if (-not (Test-Path -LiteralPath $reportPath)) { throw "No MT5 report produced for $caseId" }
        Get-ChildItem -LiteralPath $testerReportRoot -Filter ($caseId+'*') | Copy-Item -Destination $outputRoot -Force
        Write-Host ("DONE  {0} / {1}" -f $Stage,$caseId) -ForegroundColor Green
    } else {
        Write-Host ("SKIP  {0} / {1}" -f $Stage,$caseId) -ForegroundColor DarkGray
    }
    $manifest.Add([pscustomobject]@{
        case_id=$caseId; stage=$Stage; asset=$asset.Id; symbol=$asset.Symbol; period='M1';
        direction=$direction.Id; geometry=$geometry.Id; entry_offset=[double]$geometry.Entry;
        stop_distance=[double]$geometry.Stop; trail_distance=[double]$geometry.Stop*[double]$manage.TrailFactor;
        management=$manage.Id; placement_lead_seconds=[int]$manage.Lead; close_seconds=[int]$manage.Close;
        dynamic=[bool]$manage.Dynamic; buy=[bool]$direction.Buy; sell=[bool]$direction.Sell;
        risk_per_enabled_side_pct=0.75; total_planned_event_risk_pct=1.50;
        from=$period.From; to=$period.To; execution_mode=[int]$period.Execution; report=$completedReport
    })
}
$manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $outputRoot 'manifest.json') -Encoding utf8
python (Join-Path $researchRoot 'Analyze-News-Pulse-Crypto.py') --stage $Stage
if ($LASTEXITCODE -ne 0) { throw 'Crypto News Pulse analysis failed.' }
