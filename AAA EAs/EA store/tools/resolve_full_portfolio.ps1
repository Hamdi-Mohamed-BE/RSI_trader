param([Parameter(Mandatory=$true)][string]$InstallerPath)
# Prints the exact EA/SET files the canonical installer selects for the named "Full EA portfolio - Recommended Adaptive"
# launcher (Start-LiveProfile full-eas route). Runs only the installer's own Get-PortfolioItems function, parsed from its
# AST: no MT5 terminal, account, profile or file is touched.
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$tokens=$null;$parseErrors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($InstallerPath,[ref]$tokens,[ref]$parseErrors)
if($parseErrors.Count){throw 'Installer parse failure.'}
$PSScriptRoot=Split-Path -Parent $InstallerPath
# Script-scope values exactly as the full-eas route passes them (Start-LiveProfile.ps1).
$PackageRoot=Split-Path -Parent $PSScriptRoot
$SafetyMode='STANDARD';$AccountProfile='AUTO'
$IsAdaptiveAccount=$true;$IsSmallAccount=$false;$IsFullSafe=$false
$UseRecommendedSelections=$true;$UseAdaptiveProfile=$true;$UseClaudeSelections=$false;$UseReviewedSelections=$false
. (Join-Path $PSScriptRoot 'News-Launcher-Policy.ps1')
. (Join-Path $PSScriptRoot 'Reviewed-Portfolio-Policy.ps1')
$definition=@($ast.FindAll({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst]},$true) | Where-Object Name -eq 'Get-PortfolioItems')
if($definition.Count -ne 1){throw 'Get-PortfolioItems not found.'}
. ([scriptblock]::Create($definition[0].Extent.Text))
$items=@(Get-PortfolioItems)
@($items | ForEach-Object {
    [pscustomobject]@{label=$_.Label;canonical=$_.Canonical;period=$_.Period;expert=$_.Expert;
        expert_path=[IO.Path]::GetFullPath($_.ExpertFullPath);set_path=[IO.Path]::GetFullPath($_.SetFullPath)}
}) | ConvertTo-Json -Depth 3
