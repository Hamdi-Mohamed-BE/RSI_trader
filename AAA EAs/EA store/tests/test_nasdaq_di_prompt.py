"""Offline launcher tests: no account connection, installation or terminal restart."""
import json
import pytest
from app.catalog import PACKAGE_ROOT
from test_standalone_news_risk import ps


@pytest.mark.parametrize('answer,expected', [('OFF', 'OFF'), (' on ', 'ON'), ('', 'ON')])
def test_best_prompt_propagates_only_di_choice(answer, expected):
    result = ps(r'''
function Read-Host { param([string]$Prompt)
 if($Prompt -notlike 'Nasdaq 5M DI14*'){throw 'Unexpected prompt'}
 return 'ANSWER'
}
function powershell.exe { Write-Output ('CAPTURED='+($args|ConvertTo-Json -Compress));$global:LASTEXITCODE=0 }
& (Join-Path $env:CALYX_TEST_PACKAGE_ROOT '_Auto Deploy\Start-Dynamic-Portfolio.ps1') -RiskMode PERCENT -RiskValue .5 -NewsRiskPercent .3 -SafetyMode STANDARD -PromptNasdaqDIFilter -Yes
'''.replace('ANSWER', answer))
    assert result.returncode == 0, result.stdout + result.stderr
    args = json.loads(next(s[9:] for s in result.stdout.splitlines() if s.startswith('CAPTURED=')))
    assert args[args.index('-NasdaqDIFilter') + 1] == expected
    assert args[args.index('-RiskValue') + 1] == '0.5'
    assert args[args.index('-NewsRiskPercent') + 1] == '0.3'


@pytest.mark.parametrize('args,expected', [
    ('-ValidateOnly -PromptNasdaqDIFilter', 'ON'),
    ('-ValidateOnly -PromptNasdaqDIFilter -NasdaqDIFilter OFF', 'OFF'),
    ('-RiskMode PERCENT -RiskValue .5 -NewsRiskPercent .3 -SafetyMode STANDARD -Yes', 'ON'),
    ('-RiskMode PERCENT -RiskValue .5 -NewsRiskPercent .3 -SafetyMode STANDARD -Yes -PromptNasdaqDIFilter -NasdaqDIFilter OFF', 'OFF'),
])
def test_unattended_default_and_explicit_override(args, expected):
    result = ps(r'''
function Read-Host { throw 'Must not prompt' }
function powershell.exe { Write-Output ('CAPTURED='+($args|ConvertTo-Json -Compress));$global:LASTEXITCODE=0 }
& (Join-Path $env:CALYX_TEST_PACKAGE_ROOT '_Auto Deploy\Start-Dynamic-Portfolio.ps1') ARGS
'''.replace('ARGS', args))
    assert result.returncode == 0, result.stdout + result.stderr
    captured = json.loads(next(s[9:] for s in result.stdout.splitlines() if s.startswith('CAPTURED=')))
    assert captured[captured.index('-NasdaqDIFilter') + 1] == expected


def test_invalid_interactive_choice_never_runs_child():
    result = ps(r'''
function Read-Host { return 'maybe' }
function powershell.exe { throw 'CHILD_MUST_NOT_RUN' }
& (Join-Path $env:CALYX_TEST_PACKAGE_ROOT '_Auto Deploy\Start-Dynamic-Portfolio.ps1') -RiskMode PERCENT -RiskValue .5 -NewsRiskPercent .3 -SafetyMode STANDARD -PromptNasdaqDIFilter -Yes
''')
    assert result.returncode != 0
    assert 'Nasdaq DI filter must be ON or OFF' in result.stdout
    assert 'CHILD_MUST_NOT_RUN' not in result.stdout + result.stderr


def test_effective_inputs_change_one_key_only_on_both_portfolios():
    result = ps(r'''
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop';$PackageRoot=$env:CALYX_TEST_PACKAGE_ROOT
. (Join-Path $PackageRoot '_Auto Deploy\News-Launcher-Policy.ps1')
# Function definitions include their parameter lists, so import at script scope directly.
$t=$null;$e=$null
$ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PackageRoot '_Auto Deploy\Install-BMTradingPortfolio.ps1'),[ref]$t,[ref]$e)
if($e.Count){throw 'Parse error'}
$names=@('Get-PortfolioItems','Read-SetInputs','Test-NewsAdaptiveExemption','Get-EffectiveInputs','New-ChartText')
foreach($f in $ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -in $names},$true)){. ([scriptblock]::Create($f.Extent.Text))}
function Stop-WithMessage([string]$Message){throw $Message}
$UsesDynamicRisk=$true;$RiskMode='PERCENT';$IsAdaptiveAccount=$true;$IsSmallAccount=$false
$UseRecommendedSelections=$true;$UseClaudeSelections=$false;$UseAdaptiveProfile=$false;$IsFullSafe=$false
$ApplyLiveProfileDIChoices=$false
$GoldNewsRoot=Join-Path $PackageRoot '..\..\AI news';$ExpertFolderName='OfflineOnly'
$NewsRiskPercent=.3;$EffectiveAdaptiveRiskPercent=.5
$count=0
$expectedCount=@(Get-PortfolioItems).Count+14
foreach($item in @(Get-PortfolioItems)){
 $item|Add-Member EffectiveRiskPercent .5;$item|Add-Member EffectiveRisk 50
 $item|Add-Member EffectiveLot .01;$item|Add-Member EffectiveStopPercent 1
 $NasdaqDIFilter='ON';$on=Get-EffectiveInputs $item
 $NasdaqDIFilter='OFF';$off=Get-EffectiveInputs $item
 $diff=@($on.Keys|Where-Object {$on[$_] -cne $off[$_]})
 if($item.Label -eq 'Nasdaq 5M Candle Momentum'){
  if($diff.Count -ne 1 -or $diff[0] -ne 'InpRequireDIAgreement' -or $off[$diff[0]] -ne 'false'){throw 'Wrong override'}
  $chart=New-ChartText $item $item.Canonical 1 0
  if(-not $chart.Contains('InpRequireDIAgreement=false')){throw 'Chart missed override'}
 }elseif($diff.Count){throw 'Changed another EA'}
 $count++
}
$ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PackageRoot '_Auto Deploy\Install-FTMO13.ps1'),[ref]$t,[ref]$e)
if($e.Count){throw 'Parse error'}
foreach($f in $ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Get-FTMOPresetInputs'},$true)){. ([scriptblock]::Create($f.Extent.Text))}
$study=Join-Path $PackageRoot 'FTMO Thirteen EA Deployment 2026-09-27';$Package=Join-Path $study 'package'
$manifest=Get-Content -Raw -LiteralPath (Join-Path $study 'PACKAGE.json')|ConvertFrom-Json
foreach($entry in $manifest.entries){
 $on=Get-FTMOPresetInputs $entry ON;$off=Get-FTMOPresetInputs $entry OFF
 $diff=@($on.Keys|Where-Object {$on[$_] -cne $off[$_]})
 if($entry.slug -eq 'nasdaq-5m-candle-momentum'){
  if($diff.Count -ne 1 -or $diff[0] -ne 'InpRequireDIAgreement' -or $off[$diff[0]] -ne 'false'){throw 'FTMO override failed'}
 }elseif($diff.Count){throw 'Changed another FTMO EA'}
 if($off['FTMOExpectedLogin'] -ne '0' -or $off['InpRiskPercent'] -ne '0.5' -or $off['InpAdaptivePortfolioControls'] -ne 'false'){throw 'FTMO policy changed'}
 $count++
}
if($manifest.news_enabled -or $count -ne $expectedCount){throw 'Wrong portfolio scope'}
Write-Output 'PASS 47 presets; exactly one DI key changes in each Nasdaq preset'
''')
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'PASS 47 presets' in result.stdout


@pytest.mark.parametrize('choice', ['ON', 'OFF'])
def test_ftmo_validate_only_no_account_access(choice):
    result = ps(r'''
function Read-Host { throw 'ValidateOnly must not prompt' }
& (Join-Path $env:CALYX_TEST_PACKAGE_ROOT '_Auto Deploy\Install-FTMO13.ps1') -ValidateOnly -PromptNasdaqDIFilter -NasdaqDIFilter CHOICE
'''.replace('CHOICE', choice))
    assert result.returncode == 0, result.stdout + result.stderr
    assert f'DI14 filter: {choice}' in result.stdout
    assert 'No account accessed.' in result.stdout


def test_only_requested_bats_add_prompt_and_baseline_stays_di_on():
    bats = [p.name for p in PACKAGE_ROOT.glob('*.bat') if '-PromptNasdaqDIFilter' in p.read_text()]
    assert sorted(bats) == ['BEST RECOMMENDED 2026-09-01.bat', 'FTMO 10K SWING - 13 EAS - NEWS OFF.bat']
    preset = PACKAGE_ROOT/'Selected Portfolio Settings 2026-09-01/11 Nasdaq 5M - DI WIDE 0P60PCT ATR6 NO TP - 1PCT.set'
    assert 'InpRequireDIAgreement=true' in preset.read_text()


@pytest.mark.parametrize('answer,expected', [('off', 'OFF'), ('', 'ON'), ('maybe', None)])
def test_ftmo_prompt_before_account_detection(answer, expected):
    # Execute only the real script's preflight-free prefix, including package
    # integrity and the prompt. Never enter candidate detection/account probes.
    result = ps(r'''
$file=Join-Path $env:CALYX_TEST_PACKAGE_ROOT '_Auto Deploy\Install-FTMO13.ps1'
$body=Get-Content -Raw -LiteralPath $file
$prefix=$body.Substring(0,$body.IndexOf('$candidates=@('))
$testRoot=Split-Path -Parent $file
$prefix=$prefix.Replace('$PSScriptRoot','$testRoot')
function Read-Host { param([string]$Prompt)
 if($Prompt -notlike 'Nasdaq 5M DI14*'){throw 'Unexpected prompt'}
 return 'ANSWER'
}
& ([scriptblock]::Create($prefix)) -PromptNasdaqDIFilter
'''.replace('ANSWER', answer))
    if expected:
        assert result.returncode == 0, result.stdout + result.stderr
        assert f'DI14 filter: {expected}' in result.stdout
    else:
        assert result.returncode != 0
        assert 'Nasdaq DI filter must be ON or OFF' in result.stderr
