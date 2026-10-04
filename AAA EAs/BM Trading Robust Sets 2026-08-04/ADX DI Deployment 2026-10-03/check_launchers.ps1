# Offline AST-only checks. Never executes installer top-level or accesses MT5.
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$PackageRoot=Split-Path -Parent $PSScriptRoot
$tokens=$null;$parseErrors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PackageRoot '_Auto Deploy\Install-BMTradingPortfolio.ps1'),[ref]$tokens,[ref]$parseErrors)
if($parseErrors.Count){throw 'Installer parse error'}
$names=@('Get-PortfolioItems','Read-SetInputs','Get-EffectiveInputs','Test-NewsAdaptiveExemption','New-ChartText')
foreach($f in $ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -in $names},$true)){. ([scriptblock]::Create($f.Extent.Text))}
. (Join-Path $PackageRoot '_Auto Deploy\News-Launcher-Policy.ps1')
function Stop-WithMessage([string]$Message){throw $Message}
$want=Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'SELECTION.json') | ConvertFrom-Json
$GoldNewsRoot=Join-Path $PackageRoot '..\..\AI news'
$NasdaqDIFilter='ON';$NewsRiskPercent=.3;$EffectiveAdaptiveRiskPercent=.5;$ExpertFolderName='OfflineADXDI'
$checks=0
foreach($mode in @('STANDARD','SAFE','RECOMMENDED','ADAPTIVE','CLAUDE','100K','900','FIXED_USD')){
 $UseRecommendedSelections=$mode -in @('RECOMMENDED','ADAPTIVE','CLAUDE')
 $UseClaudeSelections=$mode -eq 'CLAUDE';$UseAdaptiveProfile=$mode -eq 'ADAPTIVE';$IsFullSafe=$mode -eq 'SAFE'
 $IsAdaptiveAccount=$mode -notin @('100K','900');$IsSmallAccount=$mode -eq '900'
 $UsesDynamicRisk=$mode -eq 'FIXED_USD';$RiskMode=if($UsesDynamicRisk){'FIXED_USD'}else{'DEFAULT'}
 $items=@(Get-PortfolioItems)
 if(@($items|Where-Object {$_.Label -match 'News Pulse (XAG|BTC|EURUSD)'}).Count){throw 'Non-gold news restored'}
 foreach($profile in $want.profiles.PSObject.Properties){
  $p=$profile.Value;$matches=@($items|Where-Object Label -eq $p.label)
  if($matches.Count -ne 1){throw "Missing or duplicate $($p.label)"}
  $item=$matches[0];$item|Add-Member EffectiveRiskPercent .5;$item|Add-Member EffectiveRisk 50
  $item|Add-Member EffectiveLot .01;$item|Add-Member EffectiveStopPercent 1
  if($item.ExpertFullPath -ne (Join-Path $PackageRoot $p.expert) -or $item.SetFullPath -ne (Join-Path $PackageRoot $p.settings)){throw "$mode wrong source"}
  $in=Get-EffectiveInputs $item
  foreach($key in @('InpUseADXFilter','InpADXMinimum','InpRequireDIAgreement','InpADXTimeframe')){
   if($in[$key] -ne $p.inputs.$key){throw "$mode $($p.label) incorrect $key"};$checks++
  }
  $expectedRisk=if($IsAdaptiveAccount -or $UsesDynamicRisk -or $item.FixedPercentRisk -gt 0){.5}else{1.0}
  if([double]$in['InpRiskPercent'] -ne $expectedRisk){throw 'Requested risk changed'}
  $chart=New-ChartText $item $item.Canonical 1 0
  if(-not $chart.Contains('InpRequireDIAgreement='+$p.inputs.InpRequireDIAgreement)){throw 'Chart filter omitted'}
 }
 Write-Host "PASS $mode : all four selected filters; requested risk preserved"
}
$bats=@(Get-ChildItem -LiteralPath $PackageRoot -Filter '*.bat' -File|Where-Object Name -notlike 'AVA *')
foreach($bat in $bats){
 $body=Get-Content -Raw -LiteralPath $bat.FullName
 if($body -notmatch 'ADXDI-20261003' -or $body -notmatch '(Start-Dynamic-Portfolio|Install-FTMO13)\.ps1'){throw "Unverified BAT $($bat.Name)"}
}
$result=@{filter_assertions=$checks;launcher_modes=8;normal_and_ftmo_bats=$bats.Count;live_account_accessed=$false;terminal_changed=$false}
$result|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $PSScriptRoot 'LAUNCHER_CHECKS.json') -Encoding UTF8
Write-Host 'PASS: offline launchers and generated chart inputs.'
