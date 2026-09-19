$ErrorActionPreference = 'Stop'
$packagePath = Split-Path $PSScriptRoot -Parent
$installerPath = Join-Path $packagePath '_Auto Deploy\Install-BMTradingPortfolio.ps1'
$parseTokens = $null
$parseErrors = $null
$syntax = [System.Management.Automation.Language.Parser]::ParseFile($installerPath, [ref]$parseTokens, [ref]$parseErrors)
if ($parseErrors.Count) { throw 'Installer parse errors' }
# Import only pure input-transform functions: never execute installer top-level actions.
foreach ($name in @('Read-SetInputs','Test-NewsAdaptiveExemption','Get-EffectiveInputs')) {
    $fn = $syntax.Find({ param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq $name }, $true)
    Invoke-Expression $fn.Extent.Text
}
$item = [pscustomobject]@{Label='Gold Overnight Value Area';SetFullPath=(Join-Path $packagePath 'Selected Portfolio Settings 2026-09-01\24 Gold Overnight Value Area - RAW - 1PCT.set');PercentRisk=$true;FixedPercentRisk=1.0;EffectiveRiskPercent=1.0;EffectiveRisk=100.;LockRisk=$false;SupportsSafeFilter=$false}
$IsAdaptiveAccount=$false; $IsSmallAccount=$false; $IsFullSafe=$false; $UsesDynamicRisk=$false; $UseAdaptiveProfile=$true
$v=Get-EffectiveInputs $item
if ($v['InpRiskPercent'] -ne '1' -or $v['InpAdaptivePortfolioControls'] -ne 'true') { throw 'Default/adaptive mapping failed' }
$UsesDynamicRisk=$true; $RiskMode='FIXED_USD';$item.EffectiveRisk=71.43;$item.EffectiveRiskPercent=.7143
$v=Get-EffectiveInputs $item
if ($v['InpRiskMode'] -ne '1' -or $v['InpFixedRiskMoney'] -ne '71.43') { throw 'Fixed cash mapping failed' }
$RiskMode='PERCENT';$item.EffectiveRiskPercent=.5
$v=Get-EffectiveInputs $item
if ($v['InpRiskMode'] -ne '0' -or $v['InpRiskPercent'] -ne '0.5') { throw 'Percent mapping failed' }
$IsFullSafe=$true
$v=Get-EffectiveInputs $item
if ($v.Contains('InpUseMarkovRegimeFilter')) { throw 'Safe installer must preserve the raw Gold rules' }
$bats=@('BEST RECOMMENDED 2026-09-01.bat','INSTALL AND RUN DYNAMIC CONFIG ON ACTIVE MT5.bat','INSTALL AND RUN FULL SAFE ON ACTIVE MT5.bat','INSTALL AND RUN ON 100K MT5.bat','INSTALL AND RUN ON 900 USD MT5.bat','INSTALL AND RUN ON ACTIVE MT5.bat','RECOMMENDED ADAPTIVE.bat')
foreach ($bat in $bats) {
    $content=Get-Content -Raw -LiteralPath (Join-Path $packagePath $bat)
    if ($content -notmatch 'Gold Overnight Value Area RAW') { throw "Gold inclusion message missing: $bat" }
}
Write-Output 'PASS: 7 BATs; default, adaptive, fixed cash, percent and raw-preserving Safe inputs. No installation performed.'
