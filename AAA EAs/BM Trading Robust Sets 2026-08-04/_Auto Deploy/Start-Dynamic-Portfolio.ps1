[CmdletBinding()]
param(
    [ValidateSet('', 'PERCENT', 'FIXED_USD')]
    [string]$RiskMode = '',
    [double]$RiskValue = 0.0,
    [double]$NewsRiskPercent = 0.75,
    [ValidateSet('ON', 'OFF')]
    [string]$NasdaqDIFilter = 'ON',
    [switch]$PromptNasdaqDIFilter,
    [ValidateSet('', 'STANDARD', 'SAFE')]
    [string]$SafetyMode = '',
    [string]$TargetTerminal = '',
    [switch]$UseRecommendedSelections,
    [switch]$UseClaudeSelections,
    [switch]$UseAdaptiveProfile,
    [switch]$ValidateOnly,
    [switch]$PreflightOnly,
    [switch]$Yes
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$installer = Join-Path $PSScriptRoot 'Install-BMTradingPortfolio.ps1'

function Stop-Dynamic([string]$Message) {
    Write-Host "`nSTOPPED: $Message" -ForegroundColor Red
    exit 1
}

if ($ValidateOnly -and -not $RiskMode) {
    $RiskMode = 'PERCENT'
    $RiskValue = 1.0
}
if ($ValidateOnly -and -not $SafetyMode) {
    $SafetyMode = 'STANDARD'
}

if (-not $RiskMode) {
    Write-Host "`nChoose risk sizing for every non-News EA trade:" -ForegroundColor Cyan
    Write-Host '  [1] Percentage of current equity (default: 1%)'
    Write-Host '  [2] Fixed USD target (exact where supported; converted for percentage-only EAs)'
    Write-Host '  Broker-valid lots are rounded UP. If the target is below minimum lot, minimum lot is used; the trade is not skipped.' -ForegroundColor Yellow
    Write-Host '  This means actual stop risk can exceed the selected value on coarse/minimum-lot contracts.' -ForegroundColor Yellow
    Write-Host '  News has a SEPARATE percentage prompt per order, independent of this choice; news bypasses adaptive controls.' -ForegroundColor Yellow
    $choice = (Read-Host 'Enter 1 or 2 [1]').Trim()
    if (-not $choice) { $choice = '1' }
    $RiskMode = switch ($choice) { '1' { 'PERCENT' } '2' { 'FIXED_USD' } default { Stop-Dynamic 'Risk type must be 1 or 2.' } }
}

if ($RiskValue -le 0.0) {
    $label = if ($RiskMode -eq 'PERCENT') { 'Risk per trade in percent [1]' } else { 'Risk per trade in USD (example: 50)' }
    $raw = (Read-Host $label).Trim()
    if (-not $raw -and $RiskMode -eq 'PERCENT') { $raw = '1' }
    $parsed = 0.0
    if (-not [double]::TryParse($raw, [Globalization.NumberStyles]::Float, [Globalization.CultureInfo]::InvariantCulture, [ref]$parsed)) {
        Stop-Dynamic 'Risk value must be a number. Use a dot for decimals.'
    }
    $RiskValue = $parsed
}
if ($RiskValue -le 0.0) { Stop-Dynamic 'Risk must be greater than zero.' }
if ($RiskMode -eq 'PERCENT' -and $RiskValue -gt 10.0) { Stop-Dynamic 'Percentage risk cannot exceed 10% per EA trade.' }

if (-not $PSBoundParameters.ContainsKey('NewsRiskPercent') -and -not $ValidateOnly) {
    Write-Host "`nChoose standalone news risk (not the non-News risk above):" -ForegroundColor Cyan
    Write-Host '  Applies to each News Pulse pending order and each Gold News V9 entry.'
    Write-Host '  Both News Pulse orders stay armed: two triggers can double event exposure.' -ForegroundColor Yellow
    $rawNews = (Read-Host 'News risk per ORDER in percent [0.75]').Trim()
    if (-not $rawNews) { $rawNews = '0.75' }
    $parsedNews = 0.0
    if (-not [double]::TryParse($rawNews, [Globalization.NumberStyles]::Float, [Globalization.CultureInfo]::InvariantCulture, [ref]$parsedNews)) {
        Stop-Dynamic 'News risk must be a number. Use a dot for decimals.'
    }
    $NewsRiskPercent = $parsedNews
}
if ([double]::IsNaN($NewsRiskPercent) -or [double]::IsInfinity($NewsRiskPercent) -or $NewsRiskPercent -lt 0.00000001 -or $NewsRiskPercent -gt 10) {
    Stop-Dynamic 'News risk must be between 0.00000001% and 10% per order (up to eight decimal places in EA settings).'
}

if (-not $SafetyMode) {
    $safe = (Read-Host 'Use Full Safe mode with the independent completed-D1 regime filter? (Y/N)').Trim().ToUpperInvariant()
    $SafetyMode = switch ($safe) { 'Y' { 'SAFE' } 'YES' { 'SAFE' } 'N' { 'STANDARD' } 'NO' { 'STANDARD' } default { Stop-Dynamic 'Safe-mode choice must be Y or N.' } }
}

if ($PromptNasdaqDIFilter -and -not $PSBoundParameters.ContainsKey('NasdaqDIFilter') -and -not $ValidateOnly) {
    $diChoice = (Read-Host 'Nasdaq 5M DI14 filter ON or OFF [ON]').Trim().ToUpperInvariant()
    if (-not $diChoice) { $diChoice = 'ON' }
    if ($diChoice -notin @('ON', 'OFF')) { Stop-Dynamic 'Nasdaq DI filter must be ON or OFF.' }
    $NasdaqDIFilter = $diChoice
}

Write-Host "`nDynamic configuration" -ForegroundColor Green
Write-Host ("  Nasdaq 5M DI14 filter: {0}; EMA12, 0.60% stop, ATR6 from +1R and no TP unchanged." -f $NasdaqDIFilter)
if ($NasdaqDIFilter -eq 'OFF') { Write-Host '  DI OFF is a custom selection; the published DI-ON results do not describe this selection.' -ForegroundColor Yellow }
Write-Host ('  Non-News risk: {0} {1}' -f $RiskValue, $(if ($RiskMode -eq 'PERCENT') { '%' } else { 'USD per EA trade' }))
Write-Host '  Lot policy: round UP to the broker step; use minimum lot when required; never skip solely because of lot sizing' -ForegroundColor Yellow
Write-Host '  NEWS POLICY: all four News Pulse assets and Gold News V9 enabled. FTMO remains news-free.'
Write-Host '  XAU News Pulse event settings unchanged: NFP T-10s, CPI T-5s, FOMC T-60s; both sides retained.'
Write-Host ('  Standalone news risk: {0:N4}% per order; {1:N4}% for both sides on ONE asset. Not a fixed-dollar amount.' -f $NewsRiskPercent, (2 * $NewsRiskPercent)) -ForegroundColor Cyan
Write-Host ('  Four concurrent straddles plan {0:N4}% combined; Gold News V9 can add {1:N4}%. Lot rounding, fees and gaps can increase losses.' -f (8 * $NewsRiskPercent), $NewsRiskPercent) -ForegroundColor Yellow
Write-Host '  News Pulse sizes from current equity; Gold News V9 from current balance. All five remain exempt from adaptive stops/tapers.' -ForegroundColor Yellow
Write-Host '  Historical website results keep their original 0.75% research risk, not your custom risk. No prop-firm safety is implied.' -ForegroundColor Yellow
Write-Host ('  Mode: {0}' -f $SafetyMode)
if (-not $Yes -and -not $ValidateOnly) {
    $confirm = (Read-Host 'Install and run this configuration now? (Y/N)').Trim().ToUpperInvariant()
    if ($confirm -notin @('Y', 'YES')) { Stop-Dynamic 'Cancelled by user.' }
}

$arguments = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $installer, '-AccountProfile', 'AUTO', '-RiskMode', $RiskMode, '-RiskValue', $RiskValue.ToString('R', [Globalization.CultureInfo]::InvariantCulture), '-NewsRiskPercent', $NewsRiskPercent.ToString('R', [Globalization.CultureInfo]::InvariantCulture), '-SafetyMode', $SafetyMode)
$arguments += @('-NasdaqDIFilter', $NasdaqDIFilter)
if ($UseRecommendedSelections) { $arguments += '-UseRecommendedSelections' }
if ($UseClaudeSelections) { $arguments += '-UseClaudeSelections' }
if ($UseAdaptiveProfile) { $arguments += '-UseAdaptiveProfile' }
if ($Yes) { $arguments += '-Yes' }
if ($ValidateOnly) { $arguments += '-ValidateOnly' }
if ($PreflightOnly) { $arguments += '-PreflightOnly' }
if ($TargetTerminal) { $arguments += @('-TargetTerminal', $TargetTerminal) }
& powershell.exe @arguments
exit $LASTEXITCODE
