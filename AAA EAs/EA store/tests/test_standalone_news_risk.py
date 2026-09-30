"""No live-terminal access: pure PowerShell functions and mocked launcher child only."""
import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest
from app.catalog import PACKAGE_ROOT

def ps(script):
    # powershell.exe is Windows PowerShell 5.1; a parent pwsh 7 module path can
    # select its incompatible Utility module (and hide Get-FileHash).
    module_path = ';'.join([str(Path(os.environ['WINDIR'])/'System32/WindowsPowerShell/v1.0/Modules'),
                           str(Path(os.environ['PROGRAMFILES'])/'WindowsPowerShell/Modules')])
    return subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-Command',script],
        env={**os.environ,'CALYX_TEST_PACKAGE_ROOT':str(PACKAGE_ROOT),'PSModulePath':module_path},capture_output=True,text=True,timeout=45)

def test_independent_news_risk_all_modes_and_chart_inputs():
    result=ps(r'''
$ErrorActionPreference='Stop'
$PackageRoot=$env:CALYX_TEST_PACKAGE_ROOT
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PackageRoot '_Auto Deploy\Install-BMTradingPortfolio.ps1'),[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Syntax error'}
$names=@('Get-PortfolioItems','Get-EffectiveInputs','Get-ItemBaseRiskPercent','Test-NewsAdaptiveExemption','Read-SetInputs','Assert-EffectiveRiskInputs','New-ChartText')
foreach($f in $ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -in $names},$true)){. ([scriptblock]::Create($f.Extent.Text))}
function Stop-WithMessage([string]$Message){throw $Message}
$IsAdaptiveAccount=$true;$IsSmallAccount=$false;$UsesDynamicRisk=$true;$UseClaudeSelections=$false
$NasdaqDIFilter='ON'
$GoldNewsRoot=Join-Path $PackageRoot '..\..\AI news';$ExpertFolderName='UnitTest';$EffectiveAdaptiveRiskPercent=1.6
$checks=0
foreach($mode in @('PERCENT','FIXED_USD')){foreach($safe in @($false,$true)){foreach($adaptive in @($false,$true)){foreach($news in @(.30,.75,1.25)){
 $RiskMode=$mode;$IsFullSafe=$safe;$UseAdaptiveProfile=$adaptive;$UseRecommendedSelections=$true;$NewsRiskPercent=$news
 $items=@(Get-PortfolioItems);$n=0
 foreach($item in $items){
  $isNews=Test-NewsAdaptiveExemption $item
  $risk=(Get-ItemBaseRiskPercent $item)*$item.AdaptiveBaseMultiplier
  $item|Add-Member EffectiveRiskPercent $risk;$item|Add-Member EffectiveRisk (10000*$risk/100)
  $item|Add-Member EffectiveLot .01;$item|Add-Member EffectiveStopPercent 1
  $inputs=Get-EffectiveInputs $item
  if($isNews){
   $n++
   if([double]$inputs['InpRiskPercent'] -ne $news -or $inputs['InpAdaptivePortfolioControls'] -ne 'false'){throw 'News was mixed with ordinary risk or tapered'}
   if($item.Label -like 'News Pulse *'){
    if($inputs['InpEnableBuySide'] -ne 'true' -or $inputs['InpEnableSellSide'] -ne 'true'){throw 'Lost two-sided orders'}
    $chart=New-ChartText $item $item.Canonical 1 0
    if(-not $chart.Contains('InpRiskPercent='+$news.ToString('0.########',[Globalization.CultureInfo]::InvariantCulture))){throw 'Chart risk mismatch'}
   }
  }elseif($adaptive -and $inputs['InpAdaptivePortfolioControls'] -ne 'true'){throw 'Non-News protection changed'}
  if($item.Label -eq 'Nasdaq 5M Candle Momentum' -and $adaptive -and $risk -ne .4){throw 'Nasdaq allocation changed'}
 }
 if($n -ne 5 -or $items.Count -ne 35){throw 'Wrong scope'}
 Assert-EffectiveRiskInputs $items;$checks++
}}}}
Write-Output ('PASS configurations='+$checks)
''')
    assert result.returncode==0,result.stdout+result.stderr
    assert 'PASS configurations=24' in result.stdout

@pytest.mark.parametrize('arguments,answer,expected',[
    ('-RiskMode PERCENT -RiskValue 0.5 -SafetyMode STANDARD -Yes','0.3','0.3'),
    ('-RiskMode FIXED_USD -RiskValue 50 -SafetyMode SAFE -Yes','1.25','1.25'),
    ('-RiskMode PERCENT -RiskValue 2 -NewsRiskPercent 0.4 -SafetyMode STANDARD -Yes',None,'0.4'),
    ('-ValidateOnly',None,'0.75'),
    ('-RiskMode PERCENT -RiskValue 0.5 -SafetyMode STANDARD -Yes','','0.75'),
])
def test_wrapper_prompts_separately_and_passes_news_to_child(arguments,answer,expected):
    prompt="throw 'Unexpected prompt'" if answer is None else "return '"+answer+"'"
    script=r'''
$ErrorActionPreference='Stop'
function Read-Host { param([string]$Prompt) PROMPT_BODY }
function powershell.exe { Write-Output ('CAPTURED='+($args|ConvertTo-Json -Compress));$global:LASTEXITCODE=0 }
& (Join-Path $env:CALYX_TEST_PACKAGE_ROOT '_Auto Deploy\Start-Dynamic-Portfolio.ps1') ARGUMENTS
'''.replace('PROMPT_BODY',prompt).replace('ARGUMENTS',arguments)
    result=ps(script)
    assert result.returncode==0,result.stdout+result.stderr
    args=json.loads(next(x.removeprefix('CAPTURED=') for x in result.stdout.splitlines() if x.startswith('CAPTURED=')))
    assert str(args[args.index('-NewsRiskPercent')+1])==expected

@pytest.mark.parametrize('value', ['0','-1','0.000000001','10.01','([double]::NaN)','([double]::PositiveInfinity)'])
def test_invalid_news_percent_fails_before_child(value):
    result=ps(r'''
function powershell.exe { throw 'CHILD_MUST_NOT_RUN' }
& (Join-Path $env:CALYX_TEST_PACKAGE_ROOT '_Auto Deploy\Start-Dynamic-Portfolio.ps1') -RiskMode PERCENT -RiskValue .5 -NewsRiskPercent VALUE -SafetyMode STANDARD -Yes
'''.replace('VALUE',value))
    assert result.returncode!=0
    assert 'CHILD_MUST_NOT_RUN' not in result.stdout+result.stderr
    assert 'News risk must be' in result.stdout

def test_eight_risk_prompt_bats_route_through_shared_prompt_and_ftmo_stays_off():
    bats=[p for p in PACKAGE_ROOT.glob('*.bat') if 'Start-Dynamic-Portfolio.ps1' in p.read_text()]
    assert len(bats)==8
    for p in bats:assert 'News risk is asked SEPARATELY per order' in p.read_text()
    ftmo=json.loads((PACKAGE_ROOT/'FTMO Thirteen EA Deployment 2026-09-27/PACKAGE.json').read_text())
    assert ftmo['news_enabled'] is False and len(ftmo['entries'])==14

def test_active_news_sources_use_runtime_input_without_event_geometry_changes():
    root=PACKAGE_ROOT/'News Standalone Risk 2026-09-28'
    for name in ['AAA Final News Pulse XAU Event Specific EA','AAA Final News Pulse Multi Asset Event EA']:
        code=(PACKAGE_ROOT/'AAA Final EAs'/name/(name+'.mq5')).read_text()
        old=(root/'baseline'/(name+'.mq5')).read_text()
        assert 'double side_risk=InpRiskPercent*adaptive;' in code
        assert 'MathAbs(InpRiskPercent-NP_RISK_PER_STOP_PERCENT)' not in code
        assert '!MathIsValidNumber(InpRiskPercent)' in code and 'InpRiskPercent>10.0' in code
        assert 'Deliberately not OCO' in code
        # Every event-selection/geometry assignment remains unchanged.
        selected=lambda s:[line.strip() for line in s.splitlines() if 'g_np_' in line]
        assert selected(code)==selected(old)
