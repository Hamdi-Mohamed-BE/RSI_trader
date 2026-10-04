Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$PackageRoot=Split-Path -Parent $PSScriptRoot
$HourlyRiskPercent=0.5
$HourlyUseDefaultRisk=$false
$NasdaqDIFilter='ON'
. (Join-Path $PSScriptRoot 'News-Launcher-Policy.ps1')
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot 'Install-BMTradingPortfolio.ps1'),[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Parse failure'}
foreach($name in @('Get-PortfolioItems','Read-SetInputs','Get-EffectiveInputs','Get-ItemBaseRiskPercent','Test-NewsAdaptiveExemption','Assert-EffectiveRiskInputs','Stop-WithMessage')) {
    $f=$ast.Find({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq $name},$true)
    . ([scriptblock]::Create($f.Extent.Text))
}
foreach($mode in @('Standard','Safe','Recommended','Claude','Adaptive')) {
    $UseRecommendedSelections=$mode -in @('Recommended','Claude','Adaptive')
    $UseClaudeSelections=$mode -eq 'Claude'
    $UseAdaptiveProfile=$mode -eq 'Adaptive'
    $IsFullSafe=$mode -eq 'Safe'
    foreach($riskCase in @('Default','BlankPrompt','SelectedPercent','FixedCash')) {
        $IsAdaptiveAccount=$true;$IsSmallAccount=$false
        $RiskMode=if($riskCase -eq 'FixedCash'){'FIXED_USD'}elseif($riskCase -eq 'Default'){'DEFAULT'}else{'PERCENT'}
        $UsesDynamicRisk=$RiskMode -ne 'DEFAULT'
        $HourlyUseDefaultRisk=$riskCase -eq 'BlankPrompt'
        $EffectiveAdaptiveRiskPercent=1.3;$AdaptiveRiskPercent=1.0;$NewsRiskPercent=0.75
        $items=@(Get-PortfolioItems)
        if($items.Count -ne 37){throw 'Manifest count'}
        $hours=@($items | Where-Object HistoricalLossSizing)
        if($hours.Count -ne 2){throw 'Hourly count'}
        $magics=@()
        foreach($item in $hours) {
            $percent=Get-ItemBaseRiskPercent $item
            $expected=if($riskCase -in @('Default','BlankPrompt')){0.5}else{1.3}
            if([Math]::Abs($percent-$expected) -gt 1e-10){throw 'Default/selected percentage mapping'}
            $item | Add-Member -NotePropertyName EffectiveRiskPercent -NotePropertyValue $percent
            $item | Add-Member -NotePropertyName EffectiveRisk -NotePropertyValue 50.0
            $inp=Get-EffectiveInputs $item
            if($inp['InpSizingMode'] -ne $(if($riskCase -eq 'FixedCash'){'2'}else{'1'})){throw 'Sizing mode'}
            if($inp['InpAdaptivePortfolioControls'] -ne $(if($UseAdaptiveProfile){'true'}else{'false'})){throw 'Adaptive switch'}
            if($inp['InpAllowRealAccount'] -ne 'true' -or [double]$inp['InpHistoricalLossPoints'] -le 0){throw 'Deployment inputs'}
            if($inp.Contains('InpUseMarkovRegimeFilter')){throw 'Unexpected strategy mutation'}
            $magics += $inp['InpMagic']
        }
        if(@($magics | Select-Object -Unique).Count -ne 2){throw 'Magic collision'}
        Write-Host "PASS $mode / ${riskCase}: both hourly charts, defaults, selected sizing, adaptive controls."
    }
}
Write-Host 'Offline only. No account probe, chart installation or orders performed.'
