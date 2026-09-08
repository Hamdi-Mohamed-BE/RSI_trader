[CmdletBinding()]
param(
    [ValidateSet('screen','validation','locked','full')][string]$Phase = 'screen',
    [int]$TimeoutSeconds = 2400,
    [string[]]$OnlyCases = @()
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$researchRoot = $PSScriptRoot
$packageRoot = Split-Path -Parent $researchRoot
$testerRoot = Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'
$terminal = Join-Path $testerRoot 'terminal64.exe'
$compiled = Join-Path $researchRoot 'EA\LTA Book Fidelity Research EA.ex5'
$baseSet = Join-Path $researchRoot 'Sets\CONTROL - Current Standard 1pct.set'
$expertFolder = 'AAA Research\LTA Book Fidelity 20260907'
$expertName = 'LTA Book Fidelity Research EA'
$expertRoot = Join-Path (Join-Path $testerRoot 'MQL5\Experts') $expertFolder
$testerSetRoot = Join-Path $testerRoot 'MQL5\Profiles\Tester'
$configRoot = Join-Path $testerRoot ('backtest-configs\lta-book-' + $Phase)
$terminalReportRoot = Join-Path $testerRoot ('reports\lta-book-' + $Phase)
$outputRoot = Join-Path $researchRoot ('Backtest Reports\' + $Phase)
$savedSetRoot = Join-Path $researchRoot ('Sets\' + $Phase)

foreach ($path in @($expertRoot, $testerSetRoot, $configRoot, $terminalReportRoot, $outputRoot, $savedSetRoot)) {
    [void](New-Item -ItemType Directory -Path $path -Force)
}
if (-not (Test-Path -LiteralPath $compiled)) { throw "Compile the isolated research EA first: $compiled" }
if (-not (Test-Path -LiteralPath $terminal)) { throw "Portable MT5 tester is missing: $terminal" }
Copy-Item -LiteralPath $compiled -Destination (Join-Path $expertRoot ($expertName + '.ex5')) -Force

function Set-Input([string]$Text, [string]$Name, [string]$Value) {
    $pattern = '(?m)^' + [regex]::Escape($Name) + '=.*$'
    $line = $Name + '=' + $Value
    if ([regex]::IsMatch($Text, $pattern)) { return [regex]::Replace($Text, $pattern, $line) }
    return $Text.TrimEnd() + "`r`n" + $line + "`r`n"
}

function New-Case([string]$Slug, [hashtable]$Overrides, [string]$Purpose) {
    [pscustomobject]@{ Slug = $Slug; Overrides = $Overrides; Purpose = $Purpose }
}

function Stop-StalePortableTester {
    $resolvedTerminal = [IO.Path]::GetFullPath($terminal)
    Get-CimInstance Win32_Process -Filter "Name='terminal64.exe'" |
        Where-Object { $_.ExecutablePath -and [IO.Path]::GetFullPath($_.ExecutablePath) -eq $resolvedTerminal } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
}

$cases = @(
    (New-Case 'baseline-standard' @{} 'Frozen current LTA control, Safe gate off'),
    (New-Case 'baseline-safe' @{ InpUseMarkovRegimeFilter = 'true' } 'Frozen current LTA control, current recommended Safe gate on'),
    (New-Case 'm1-vap' @{ InpBookProfileMode = '1' } 'M1 typical-price volume-at-price reconstruction'),
    (New-Case 'structural-swing' @{ InpUseSwingProfile = 'true'; InpUseStructuralSwingProfile = 'true' } 'Confirmed structural swing anchor instead of rolling bars'),
    (New-Case 'fixed-range' @{ InpUseFixedRangeProfile = 'true' } 'Completed consolidation fixed-range profile'),
    (New-Case 'multiple-nodes' @{ InpUseMultipleVolumeNodes = 'true' } 'Local HVN/LVN levels in addition to POC and value area'),
    (New-Case 'auction-confirm' @{ InpBookAuctionMode = '1'; InpUseMultipleVolumeNodes = 'true' } 'Auction acceptance/rejection as confirmation gate'),
    (New-Case 'auction-priority' @{ InpBookAuctionMode = '2'; InpUseMultipleVolumeNodes = 'true' } 'Auction acceptance/rejection levels receive entry priority'),
    (New-Case 'quality-zones' @{ InpUseBookZoneQuality = 'true' } 'Freshness, strength and prior-touch supply/demand scoring'),
    (New-Case 'structural-targets' @{ InpBookTargetMode = '1'; InpUseMultipleVolumeNodes = 'true' } 'Next profile/zone target with minimum 1.5R'),
    (New-Case 'execution-guard' @{ InpBlockRolloverWindow = 'true'; InpMaxSpreadPoints = '500'; InpBookBrokerUtcOffsetMinutes = '180' } 'Measured spread ceiling and 21:00-23:00 UTC rollover block'),
    (New-Case 'book-full-stack' @{
        InpBookProfileMode = '1'; InpUseSwingProfile = 'true'; InpUseStructuralSwingProfile = 'true';
        InpUseFixedRangeProfile = 'true'; InpUseMultipleVolumeNodes = 'true'; InpBookAuctionMode = '2';
        InpUseBookZoneQuality = 'true'; InpBookTargetMode = '1'; InpBlockRolloverWindow = 'true';
        InpMaxSpreadPoints = '500'; InpBookBrokerUtcOffsetMinutes = '180'
    } 'All implementable book-fidelity changes together')
)

if ($OnlyCases.Count -gt 0) { $cases = @($cases | Where-Object { $_.Slug -in $OnlyCases }) }
if ($cases.Count -eq 0) { throw 'No matching research cases were selected.' }

$window = switch ($Phase) {
    'screen'     { [pscustomobject]@{ From = '2021.09.01'; To = '2024.08.31' } }
    'validation' { [pscustomobject]@{ From = '2024.09.01'; To = '2025.08.31' } }
    'locked'     { [pscustomobject]@{ From = '2025.09.01'; To = '2026.09.01' } }
    'full'       { [pscustomobject]@{ From = '2021.09.01'; To = '2026.09.01' } }
}

$manifest = [Collections.Generic.List[object]]::new()
$sequence = 0
foreach ($case in $cases) {
    $sequence++
    $id = 'xauusd--' + $case.Slug + '--' + $Phase
    $setName = 'LTA-Book-' + $id + '.set'
    $set = Get-Content -LiteralPath $baseSet -Raw

    # Research invariants: one symbol, exactly 1% requested risk, no unrelated
    # dynamic trailing/session experiment, and all new switches off by default.
    $invariants = @{
        InpMomentumRiskPercent = '1'; InpContrarianRiskPercent = '1'; InpAbsoluteRiskCapPercent = '1';
        InpUseDynamicTrailingSL = 'false'; InpResearchSession = '0'; InpUseMarkovRegimeFilter = 'false';
        InpBookProfileMode = '0'; InpUseStructuralSwingProfile = 'false'; InpUseFixedRangeProfile = 'false';
        InpUseMultipleVolumeNodes = 'false'; InpBookAuctionMode = '0'; InpUseBookZoneQuality = 'false';
        InpBookTargetMode = '0'; InpBlockRolloverWindow = 'false'; InpMagicNumber = [string](7277000 + $sequence)
    }
    foreach ($name in $invariants.Keys) { $set = Set-Input $set $name ([string]$invariants[$name]) }
    foreach ($name in $case.Overrides.Keys) { $set = Set-Input $set $name ([string]$case.Overrides[$name]) }

    $testerSet = Join-Path $testerSetRoot $setName
    $savedSet = Join-Path $savedSetRoot ($id + '.set')
    [IO.File]::WriteAllText($testerSet, $set, [Text.UTF8Encoding]::new($false))
    [IO.File]::WriteAllText($savedSet, $set, [Text.UTF8Encoding]::new($false))

    $configPath = Join-Path $configRoot ($id + '.ini')
    $reportRelative = 'reports\lta-book-' + $Phase + '\' + $id + '.htm'
    $reportPath = Join-Path $terminalReportRoot ($id + '.htm')
    $config = @"
[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=$expertFolder\$expertName
ExpertParameters=$setName
Symbol=XAUUSD
Period=M15
Login=472334559
Deposit=10000
Currency=USD
Leverage=1:2000
Model=0
ExecutionMode=1
Optimization=0
FromDate=$($window.From)
ToDate=$($window.To)
ForwardMode=0
Report=$reportRelative
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"@
    [IO.File]::WriteAllText($configPath, $config, [Text.UnicodeEncoding]::new($false, $true))
    Get-ChildItem -LiteralPath $terminalReportRoot -Filter ($id + '*') -ErrorAction SilentlyContinue | Remove-Item -Force

    Write-Host ("[{0}/{1}] {2}: {3}" -f $sequence, $cases.Count, $case.Slug, $case.Purpose) -ForegroundColor Cyan
    $attempt = 0
    while (-not (Test-Path -LiteralPath $reportPath) -and $attempt -lt 3) {
        $attempt++
        Stop-StalePortableTester
        Start-Sleep -Seconds 3
        $process = Start-Process -FilePath $terminal -ArgumentList @('/portable', ('/config:"' + $configPath + '"')) -PassThru -WindowStyle Hidden
        try { Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop }
        catch {
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            throw "MT5 timed out: $id"
        }
        if (-not (Test-Path -LiteralPath $reportPath)) {
            # MT5 occasionally returns while the prior portable instance is
            # still shutting down. A short retry prevents a false failed test.
            Start-Sleep -Seconds 8
        }
    }
    if (-not (Test-Path -LiteralPath $reportPath)) { throw "MT5 did not create report: $reportPath" }
    Get-ChildItem -LiteralPath $terminalReportRoot -Filter ($id + '*') | Copy-Item -Destination $outputRoot -Force
    [void]$manifest.Add([pscustomobject]@{
        id = $id; case = $case.Slug; phase = $Phase; purpose = $case.Purpose;
        from = $window.From; to = $window.To; report = (Join-Path $outputRoot ($id + '.htm'));
        set = $savedSet; overrides = $case.Overrides
    })
}

$manifestPath = Join-Path $outputRoot 'manifest.json'
[IO.File]::WriteAllText($manifestPath, ($manifest | ConvertTo-Json -Depth 8), [Text.UTF8Encoding]::new($false))
Write-Host "Completed $sequence isolated native MT5 Every Tick tests. Production files were not touched." -ForegroundColor Green
