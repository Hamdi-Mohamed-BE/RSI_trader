[CmdletBinding()]
param(
    [ValidateSet('', 'PERCENT', 'FIXED_USD')][string]$RiskMode='',
    [double]$RiskValue=0,
    [double]$NewsRiskPercent=0.75,
    [ValidateSet('ON','OFF')][string]$NasdaqDIFilter='ON',
    [ValidateSet('ON','OFF')][string]$UsdJpyDIFilter='ON',
    [string]$TargetTerminal='',
    [switch]$ValidateOnly,
    [switch]$Yes
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$PackageRoot=Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'Reviewed-Portfolio-Policy.ps1')
$manifest=Get-ReviewedManifest
function Read-PositiveNumber([string]$Prompt, [string]$Default='') {
    $raw=(Read-Host $Prompt).Trim(); if (-not $raw) { $raw=$Default }
    $value=0.0
    if (-not [double]::TryParse($raw,[Globalization.NumberStyles]::Float,[Globalization.CultureInfo]::InvariantCulture,[ref]$value) -or [double]::IsNaN($value) -or [double]::IsInfinity($value) -or $value -le 0) { throw 'Risk must be a positive finite number; use a dot for decimals.' }
    return $value
}
if ($ValidateOnly) {
    if (-not $RiskMode) { $RiskMode='PERCENT' }
    if ($RiskValue -eq 0) { $RiskValue=1 }
} else {
    Write-Host 'REVIWED EAS - 25 owner-selected bots; no research pass or future profit is implied.' -ForegroundColor Cyan
    Write-Host 'Only this reviewed profile is installed. Existing account trades are not closed.'
    Write-Host 'Each EA has its own trade risk; simultaneous trades stack exposure. No shared daily-loss cap.' -ForegroundColor Yellow
    if (-not $RiskMode) {
        $choice=(Read-Host 'Normal bots: 1 = percent of current equity; 2 = fixed USD target [1]').Trim()
        $RiskMode=switch ($choice) { '' {'PERCENT'} '1' {'PERCENT'} '2' {'FIXED_USD'} default { throw 'Choose 1 or 2.' } }
    }
    if ($RiskValue -eq 0) {
        $RiskValue=if ($RiskMode -eq 'PERCENT') { Read-PositiveNumber 'Normal risk per trade in percent [1]' '1' } else { Read-PositiveNumber 'Normal USD risk target per trade (example 50)' }
    }
    if (-not $PSBoundParameters.ContainsKey('NewsRiskPercent')) { $NewsRiskPercent=Read-PositiveNumber 'SEPARATE news risk per ORDER in percent [0.75]' '0.75' }
    foreach ($entry in @($manifest.entries | Where-Object { $_.phase -eq 'live' -and $_.PSObject.Properties['di_input'] })) {
        $parameter=if ($entry.slug -eq 'nasdaq-5m-candle-momentum') {'NasdaqDIFilter'} else {'UsdJpyDIFilter'}
        if (-not $PSBoundParameters.ContainsKey($parameter)) {
            $choice=(Read-Host "$($entry.installer_label): keep DI ON or OFF [ON]").Trim().ToUpperInvariant()
            if (-not $choice) { $choice='ON' }
            if ($choice -notin @('ON','OFF')) { throw 'DI choice must be ON or OFF.' }
            Set-Variable -Name $parameter -Value $choice
        }
    }
}
if ([double]::IsNaN($RiskValue) -or [double]::IsInfinity($RiskValue) -or $RiskValue -le 0 -or ($RiskMode -eq 'PERCENT' -and $RiskValue -gt 10)) { throw 'Normal risk must be positive and finite; percentage cannot exceed 10%.' }
if ([double]::IsNaN($NewsRiskPercent) -or [double]::IsInfinity($NewsRiskPercent) -or $NewsRiskPercent -lt 0.00000001 -or $NewsRiskPercent -gt 10) { throw 'News percentage must be 0.00000001 through 10 per order.' }
Write-Host "Normal risk: $RiskValue $RiskMode; separate news: $NewsRiskPercent% per order."
Write-Host "DI: Nasdaq $NasdaqDIFilter / USDJPY $UsdJpyDIFilter; USDJPY ADX20 remains on."
Write-Host 'Fixed USD is exact only in cash-capable EAs; percentage-only EAs receive its balance-equivalent at installation.' -ForegroundColor Yellow
Write-Host 'Minimum lot / rounding UP, spread and gaps can exceed requested risk. Both news sides may fill; four straddles plan 8x the news percentage plus V9.' -ForegroundColor Yellow
Write-Host 'US30/US100 hourly: chosen USD/% sizes against frozen historical worst loss, NOT a future loss cap. No stop-loss. Published curves remain fixed-lot benchmarks.' -ForegroundColor Yellow
Write-Host 'DI OFF changes the preset: published DI-ON results no longer apply. Existing warnings and failed screens remain valid.' -ForegroundColor Yellow
Write-Host 'Switching to this profile stops excluded EAs from managing their open trades. Trades are NOT closed; review their stops/management before installing.' -ForegroundColor Yellow
if (-not $ValidateOnly -and -not $Yes) {
    if ((Read-Host 'Install this reviewed profile into your chosen active MT5 terminal now? Y/N').Trim().ToUpperInvariant() -notin @('Y','YES')) { throw 'Cancelled; no terminal changed.' }
}
$invoke=@('-NoLogo','-NoProfile','-ExecutionPolicy','Bypass','-File',(Join-Path $PSScriptRoot 'Install-BMTradingPortfolio.ps1'),'-AccountProfile','AUTO','-RiskMode',$RiskMode,'-RiskValue',$RiskValue.ToString('R',[Globalization.CultureInfo]::InvariantCulture),'-NewsRiskPercent',$NewsRiskPercent.ToString('R',[Globalization.CultureInfo]::InvariantCulture),'-SafetyMode','STANDARD','-UseReviewedSelections','-NasdaqDIFilter',$NasdaqDIFilter,'-UsdJpyDIFilter',$UsdJpyDIFilter)
if ($ValidateOnly) { $invoke+='-ValidateOnly' }
if ($Yes) { $invoke+='-Yes' }
if ($TargetTerminal) { $invoke+=@('-TargetTerminal',$TargetTerminal) }
& powershell.exe @invoke
exit $LASTEXITCODE
