param([Parameter(Mandatory=$true)][string]$InstallerPath)
# Full EA portfolio (full-eas route) members with the inputs the canonical installer itself would write, at a 1% research risk:
# Get-PortfolioItems + Get-EffectiveInputs parsed from the installer AST, dynamic PERCENT risk 1%, DI ON (BAT defaults), news EAs dropped.
# No MT5 terminal, account, profile or file is touched.
Set-StrictMode -Version Latest; $ErrorActionPreference='Stop'
$tokens=$null;$e=$null;$ast=[Management.Automation.Language.Parser]::ParseFile($InstallerPath,[ref]$tokens,[ref]$e)
if($e.Count){throw 'Installer parse failure.'}
$PSScriptRoot=Split-Path -Parent $InstallerPath; $PackageRoot=Split-Path -Parent $PSScriptRoot
$SafetyMode='STANDARD';$AccountProfile='AUTO';$IsAdaptiveAccount=$true;$IsSmallAccount=$false;$IsFullSafe=$false
$UseRecommendedSelections=$true;$UseAdaptiveProfile=$true;$UseClaudeSelections=$false;$UseReviewedSelections=$false
$RiskMode='PERCENT';$UsesDynamicRisk=$true;$RequestedRiskMoney=100.0;$ApplyLiveProfileDIChoices=$true;$NasdaqDIFilter='ON';$UsdJpyDIFilter='ON'
. (Join-Path $PSScriptRoot 'News-Launcher-Policy.ps1'); . (Join-Path $PSScriptRoot 'Reviewed-Portfolio-Policy.ps1')
foreach($name in 'Get-PortfolioItems','Read-SetInputs','Get-EffectiveInputs','Stop-WithMessage','Test-NewsAdaptiveExemption'){
    $def=@($ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst]},$true) | Where-Object Name -eq $name)
    if($def.Count -ne 1){throw "$name not found"}
    . ([scriptblock]::Create($def[0].Extent.Text))
}
$out=@()
foreach($item in @(Get-PortfolioItems)){
    if($item.Label -like 'News Pulse *' -or $item.Label -eq 'Gold News V9 Direction'){continue}
    $item | Add-Member -NotePropertyName EffectiveRiskPercent -NotePropertyValue 1.0 -Force
    $item | Add-Member -NotePropertyName EffectiveRisk -NotePropertyValue 100.0 -Force
    $inputs=Get-EffectiveInputs $item
    $map=[ordered]@{}; foreach($k in $inputs.Keys){$map[$k]=[string]$inputs[$k]}
    $out+=[pscustomobject]@{label=$item.Label;canonical=$item.Canonical;period=$item.Period;expert_path=[IO.Path]::GetFullPath($item.ExpertFullPath);
        set_path=[IO.Path]::GetFullPath($item.SetFullPath);inputs=$map}
}
$out | ConvertTo-Json -Depth 4
