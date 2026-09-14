[CmdletBinding()]
param(
    [ValidateSet('', 'PERCENT', 'FIXED_USD')]
    [string]$RiskMode = '',
    [double]$RiskValue = 0.0,
    [ValidateSet('', 'STANDARD', 'SAFE')]
    [string]$SafetyMode = '',
    [string]$TargetTerminal = '',
    [switch]$UseRecommendedSelections,
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
    Write-Host '  News Pulse v2.16 is the only exception: high-impact primary events only; 0.75% per pending stop, 1.50% total planned-risk cap.' -ForegroundColor Yellow
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

if (-not $SafetyMode) {
    $safe = (Read-Host 'Use Full Safe mode with the independent completed-D1 regime filter? (Y/N)').Trim().ToUpperInvariant()
    $SafetyMode = switch ($safe) { 'Y' { 'SAFE' } 'YES' { 'SAFE' } 'N' { 'STANDARD' } 'NO' { 'STANDARD' } default { Stop-Dynamic 'Safe-mode choice must be Y or N.' } }
}

Write-Host "`nDynamic configuration" -ForegroundColor Green
Write-Host ('  Non-News risk: {0} {1}' -f $RiskValue, $(if ($RiskMode -eq 'PERCENT') { '%' } else { 'USD per EA trade' }))
Write-Host '  Lot policy: round UP to the broker step; use minimum lot when required; never skip solely because of lot sizing' -ForegroundColor Yellow
Write-Host '  News Pulse v2.16: high-impact primary NFP/CPI/FOMC only; fixed 0.75% per pending stop / 1.50% total planned-risk cap'
Write-Host '  XAU profile: T-15, live Ask/Bid +/- $4, $4 stop, no trailing; both pending sides remain armed'
Write-Host ('  Mode: {0}' -f $SafetyMode)
if (-not $Yes -and -not $ValidateOnly) {
    $confirm = (Read-Host 'Install and run this configuration now? (Y/N)').Trim().ToUpperInvariant()
    if ($confirm -notin @('Y', 'YES')) { Stop-Dynamic 'Cancelled by user.' }
}

$arguments = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $installer, '-AccountProfile', 'AUTO', '-RiskMode', $RiskMode, '-RiskValue', $RiskValue, '-SafetyMode', $SafetyMode)
if ($UseRecommendedSelections) { $arguments += '-UseRecommendedSelections' }
if ($UseAdaptiveProfile) { $arguments += '-UseAdaptiveProfile' }
if ($Yes) { $arguments += '-Yes' }
if ($ValidateOnly) { $arguments += '-ValidateOnly' }
if ($PreflightOnly) { $arguments += '-PreflightOnly' }
if ($TargetTerminal) { $arguments += @('-TargetTerminal', $TargetTerminal) }
& powershell.exe @arguments
exit $LASTEXITCODE
