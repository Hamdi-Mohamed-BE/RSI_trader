Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$PackageRoot=Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'News-Launcher-Policy.ps1')
. (Join-Path $PSScriptRoot 'Reviewed-Portfolio-Policy.ps1')
$installer=Join-Path $PSScriptRoot 'Install-BMTradingPortfolio.ps1'
foreach ($file in @($installer,(Join-Path $PSScriptRoot 'Start-Reviewed-Portfolio.ps1'),(Join-Path $PSScriptRoot 'Reviewed-Portfolio-Policy.ps1'))) {
    $tokens=$null;$errors=$null
    $ast=[Management.Automation.Language.Parser]::ParseFile($file,[ref]$tokens,[ref]$errors)
    if ($errors.Count) { throw "Parse errors: $file $errors" }
}
# Extract only pure functions; NEVER invoke installer bodies or terminal/account APIs.
$ast=[Management.Automation.Language.Parser]::ParseFile($installer,[ref]$null,[ref]$null)
foreach ($name in @('Get-PortfolioItems','Read-SetInputs','Test-NewsAdaptiveExemption','Get-EffectiveInputs','Get-ItemBaseRiskPercent','Assert-EffectiveRiskInputs')) {
    $node=$ast.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq $name},$true)
    . ([scriptblock]::Create($node.Extent.Text))
}
function Stop-WithMessage([string]$Message) { throw $Message }
$IsAdaptiveAccount=$true;$IsSmallAccount=$false;$IsFullSafe=$false
$UseRecommendedSelections=$true;$UseClaudeSelections=$false;$UseAdaptiveProfile=$false
$UseReviewedSelections=$false
if (@(Get-PortfolioItems).Count -ne 37) { throw 'Original roster changed.' }
$UseReviewedSelections=$true
$manifest=Get-ReviewedManifest
$expected=@($manifest.entries | Where-Object phase -eq 'live' | ForEach-Object installer_label | Sort-Object)
foreach ($risk in @('PERCENT','FIXED_USD')) {
    $RiskMode=$risk;$UsesDynamicRisk=$true;$RiskValue=if ($risk -eq 'PERCENT') {1.2} else {50}
    $EffectiveAdaptiveRiskPercent=if ($risk -eq 'PERCENT') {1.2} else {0.5}
    $RequestedRiskMoney=if ($risk -eq 'PERCENT') {120} else {50}
    $NewsRiskPercent=0.3;$AdaptiveRiskPercent=1;$HourlyRiskPercent=0.5;$HourlyUseDefaultRisk=$false
    foreach ($choices in @(@('ON','ON'),@('OFF','OFF'),@('ON','OFF'),@('OFF','ON'))) {
        $NasdaqDIFilter=$choices[0];$UsdJpyDIFilter=$choices[1]
        $items=@(Get-PortfolioItems)
        if ($items.Count -ne 25 -or (Compare-Object $expected @($items.Label | Sort-Object))) { throw 'Reviewed roster mismatch.' }
        foreach ($item in $items) {
            if (-not (Test-Path -LiteralPath $item.ExpertFullPath) -or -not (Test-Path -LiteralPath $item.SetFullPath)) { throw "Missing package file: $($item.Label)" }
            $base=Get-ItemBaseRiskPercent $item
            $item | Add-Member -NotePropertyName EffectiveRiskPercent -NotePropertyValue $base
            $item | Add-Member -NotePropertyName EffectiveRisk -NotePropertyValue $(if ($item.LockRisk) {10000*$NewsRiskPercent/100} else {$RequestedRiskMoney})
            $inputs=Get-EffectiveInputs $item
            if ($item.HistoricalLossSizing) {
                $expectedSizing=if($risk -eq 'FIXED_USD'){'2'}else{'1'}
                if ($inputs['InpSizingMode'] -ne $expectedSizing -or [double]$inputs['InpRiskPercent'] -ne $EffectiveAdaptiveRiskPercent -or [double]$inputs['InpFixedRiskMoney'] -ne $RequestedRiskMoney) {throw 'Hourly chosen risk not applied.'}
                $original=Read-SetInputs $item.SetFullPath
                foreach($key in $original.Keys){if($key -notin @('InpSizingMode','InpRiskPercent','InpFixedRiskMoney','InpAdaptivePortfolioControls') -and $inputs[$key] -ne $original[$key]){throw "Hourly rule changed: $key"}}
            }
            $activeDI=@($inputs.Keys | Where-Object { $_ -match 'DIAgreement|DIFilter|DIConfirm|Dmi|DirectionalIndex' -and $inputs[$_] -eq 'true' })
            if ($activeDI.Count -and -not $item.ReviewedEntry.PSObject.Properties['di_input']) { throw "Active DI missing an individual prompt: $($item.Label)" }
            if ($item.PSObject.Properties['ReviewedEntry'] -and $item.ReviewedEntry.PSObject.Properties['di_input']) {
                $choice=if ($item.Label -eq 'Nasdaq 5M Candle Momentum') {$NasdaqDIFilter} else {$UsdJpyDIFilter}
                if ($inputs['InpRequireDIAgreement'] -ne $(if ($choice -eq 'ON') {'true'} else {'false'})) { throw "DI choice not applied: $($item.Label)" }
            }
            if ($item.Label -eq 'USDJPY London Open Momentum' -and ($inputs['InpUseADXFilter'] -ne 'true' -or $inputs['InpADXMinimum'] -ne '20')) { throw 'USDJPY ADX changed.' }
            if ($item.Label -eq 'XAU Trend Progression' -and ($inputs['InpRewardRisk'] -ne '1.5' -or $inputs['InpSwingLookback'] -ne '3' -or $inputs['InpUseBreakEven'] -ne 'false' -or $inputs['InpUseATRTrailing'] -ne 'false')) { throw 'Trend candidate mismatch.' }
            if (Test-NewsAdaptiveExemption $item) {
                if ($inputs['InpAdaptivePortfolioControls'] -ne 'false' -or [double]$inputs['InpRiskPercent'] -ne 0.3) { throw 'News risk/governor changed.' }
                if ($item.Label -like 'News Pulse *' -and ($inputs['InpEnableBuySide'] -ne 'true' -or $inputs['InpEnableSellSide'] -ne 'true' -or $inputs['InpMarketFallbackOnCrossedLevel'] -ne 'true')) { throw 'News execution policy changed.' }
            }
            # All DMC strategy/exit inputs must remain identical; only supported user risk inputs may differ.
            if ($item.Label -like 'DMC *') {
                $original=Read-SetInputs $item.SetFullPath
                foreach ($key in $original.Keys) {
                    if ($key -notin @('InpRiskPercent','InpMomentumRiskPercent','InpContrarianRiskPercent','InpAbsoluteRiskCapPercent','RiskPercent','RiskMoney','InpRiskAmount','InpRiskMode','InpFixedRiskMoney','Volume','VolumeMode') -and $inputs[$key] -ne $original[$key]) { throw "DMC rule changed: $key" }
                }
            }
        }
        Assert-EffectiveRiskInputs $items
        Write-Host "PASS: 25 reviewed EAs / $risk / Nasdaq DI $NasdaqDIFilter / USDJPY DI $UsdJpyDIFilter / hourly risk / separate news risk / DMC unchanged / Trend1.5R. No account accessed."
    }
}
$UseReviewedSelections=$false
if (@(Get-PortfolioItems).Count -ne 37) { throw 'Original roster not restored.' }
Write-Host 'PASS: original launcher roster retained. Only pure functions were evaluated; no install, probe, compile or terminal restart.'
