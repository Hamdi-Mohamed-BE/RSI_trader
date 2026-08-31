[CmdletBinding()]
param(
    [ValidateSet('', 'PERCENT', 'FIXED_USD')]
    [string]$RiskMode = '',
    [double]$RiskValue = 0.0,
    [ValidateSet('', 'STANDARD', 'SAFE')]
    [string]$SafetyMode = '',
    [switch]$ValidateOnly,
    [switch]$Yes
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$installer = Join-Path $PSScriptRoot 'Install-BMTradingPortfolio.ps1'

function Stop-Dynamic([string]$Message) {
    Write-Host "`nSTOPPED: $Message" -ForegroundColor Red
    exit 1
}

if (-not $RiskMode) {
    Write-Host "`nChoose risk sizing for every EA trade:" -ForegroundColor Cyan
    Write-Host '  [1] Percentage of current equity (compounds automatically)'
    Write-Host '  [2] Fixed USD target (exact where supported; converted for percentage-only EAs)'
    $choice = Read-Host 'Enter 1 or 2'
    $RiskMode = switch ($choice) { '1' { 'PERCENT' } '2' { 'FIXED_USD' } default { Stop-Dynamic 'Risk type must be 1 or 2.' } }
}

if ($RiskValue -le 0.0) {
    $label = if ($RiskMode -eq 'PERCENT') { 'Risk per trade in percent (example: 0.5)' } else { 'Risk per trade in USD (example: 50)' }
    $raw = Read-Host $label
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
Write-Host ('  Risk: {0} {1}' -f $RiskValue, $(if ($RiskMode -eq 'PERCENT') { '%' } else { 'USD per EA trade' }))
Write-Host ('  Mode: {0}' -f $SafetyMode)
if (-not $Yes) {
    $confirm = (Read-Host 'Install and run this configuration now? (Y/N)').Trim().ToUpperInvariant()
    if ($confirm -notin @('Y', 'YES')) { Stop-Dynamic 'Cancelled by user.' }
}

$arguments = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $installer, '-AccountProfile', 'AUTO', '-RiskMode', $RiskMode, '-RiskValue', $RiskValue, '-SafetyMode', $SafetyMode)
if ($ValidateOnly) { $arguments += '-ValidateOnly' }
& powershell.exe @arguments
exit $LASTEXITCODE
