# Import pure declarations only. No MT5 account, terminal or chart is accessed.
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$PackageRoot=Split-Path -Parent $PSScriptRoot
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PackageRoot '_Auto Deploy\Install-BMTradingPortfolio.ps1'),[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Installer parse error'}
$want=@('Get-PortfolioItems','Read-SetInputs','Test-NewsAdaptiveExemption','Get-EffectiveInputs','Stop-WithMessage')
foreach($def in $ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst]},$true)){
    if($def.Name -in $want){. ([scriptblock]::Create($def.Extent.Text))}
}
$EffectiveAdaptiveRiskPercent=1.0;$NasdaqDIFilter='ON'
$UseClaudeSelections=$false;$UseAdaptiveProfile=$false;$IsFullSafe=$false
$UseRecommendedSelections=$false;$IsAdaptiveAccount=$true;$IsSmallAccount=$false
$UsesDynamicRisk=$false;$RiskMode='DEFAULT'
$rows=@()
foreach($mode in @('STANDARD','SAFE','RECOMMENDED','ADAPTIVE','CLAUDE','100K','900','DYNAMIC')){
    $IsFullSafe=$mode -eq 'SAFE'
    $UseRecommendedSelections=$mode -in @('RECOMMENDED','ADAPTIVE','CLAUDE')
    $UseClaudeSelections=$mode -eq 'CLAUDE';$UseAdaptiveProfile=$mode -eq 'ADAPTIVE'
    $IsAdaptiveAccount=$mode -notin @('100K','900');$IsSmallAccount=$mode -eq '900'
    $UsesDynamicRisk=$mode -eq 'DYNAMIC';$RiskMode=if($UsesDynamicRisk){'FIXED_USD'}else{'DEFAULT'}
    foreach($label in @('XAU Trend Progression','XAU Slow Trend')){
        $item=@(Get-PortfolioItems | Where-Object Label -eq $label)[0]
        $item | Add-Member EffectiveRiskPercent 1.0
        $item | Add-Member EffectiveRisk 100.0
        $v=Get-EffectiveInputs $item
        $target=if($label -eq 'XAU Trend Progression'){0.6}else{1.0}
        if([double]$v['InpRewardRisk'] -ne $target){throw "$mode / $label target mismatch"}
        if(-not(Test-Path -LiteralPath $item.ExpertFullPath)){throw 'Missing compiled build'}
        $rows += [pscustomobject]@{mode=$mode;label=$label;target=$target}
    }
}
$rows | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'LAUNCHER_CHECKS.json') -Encoding utf8
Write-Output 'PASS: all eight normal BAT modes select Trend 0.6R and Slow 1R. No terminal accessed.'
