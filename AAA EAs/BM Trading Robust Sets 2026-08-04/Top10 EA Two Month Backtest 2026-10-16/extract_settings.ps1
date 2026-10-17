# Offline AST-only evaluation of the installer's pure configuration functions.
# No installer top-level code, terminal discovery, probes or deployment is run.
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$PackageRoot=Split-Path -Parent $PSScriptRoot
$UseRecommendedSelections=$true;$UseReviewedSelections=$false;$UseClaudeSelections=$false
$UseAdaptiveProfile=$false;$IsFullSafe=$false;$IsAdaptiveAccount=$true;$IsSmallAccount=$false
$UsesDynamicRisk=$true;$RiskMode='PERCENT';$RiskValue=1.0
$EffectiveAdaptiveRiskPercent=1.0;$AdaptiveRiskPercent=1.0;$NewsRiskPercent=0.10
$HourlyRiskPercent=1.0;$HourlyUseDefaultRisk=$false
$NasdaqDIFilter='ON';$UsdJpyDIFilter='ON';$ApplyLiveProfileDIChoices=$true
$sources=@{
    '_Auto Deploy/Install-BMTradingPortfolio.ps1'=@('Stop-WithMessage','Get-PortfolioItems','Read-SetInputs','Test-NewsAdaptiveExemption','Get-EffectiveInputs')
    '_Auto Deploy/News-Launcher-Policy.ps1'=@('Select-NormalNewsItems')
}
foreach($source in $sources.Keys){
    $tokens=$null;$errors=$null
    $ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PackageRoot $source),[ref]$tokens,[ref]$errors)
    if($errors.Count){throw "Parse failure: $source"}
    foreach($name in $sources[$source]){
        $function=$ast.Find({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq $name},$true)
        if(-not $function){throw "Missing allowlisted pure function: $name"}
        . ([scriptblock]::Create($function.Extent.Text))
    }
}
$rows=@()
foreach($item in @(Get-PortfolioItems)){
    $news=Test-NewsAdaptiveExemption $item
    $percent=if($news){0.10}else{1.0}
    $item | Add-Member -NotePropertyName EffectiveRiskPercent -NotePropertyValue $percent
    $item | Add-Member -NotePropertyName EffectiveRisk -NotePropertyValue (10000*$percent/100)
    $inputs=Get-EffectiveInputs $item
    $rows += [pscustomobject]@{
        label=$item.Label;symbol=$item.Canonical;period_minutes=$item.Period
        expert=$item.ExpertFullPath;preset=$item.SetFullPath;inputs=$inputs
        selected_risk_percent=$percent;news=$news
        safe_by_design=$item.SafeByDesign;dynamic_by_design=$item.DynamicByDesign
        dedicated_safe_preset=$item.UsesDedicatedSafePreset
        historical_loss_sizing=$item.HistoricalLossSizing
    }
}
if($rows.Count -ne 37){throw "Expected full current 37-member roster, got $($rows.Count)"}
$rows | ConvertTo-Json -Depth 20
