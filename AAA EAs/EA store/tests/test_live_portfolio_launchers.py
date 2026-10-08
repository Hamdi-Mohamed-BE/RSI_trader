"""Named BAT/file validation and pure input helpers; never probe an MT5 account."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

import pytest
from app.catalog import PACKAGE_ROOT
from app.portfolios import portfolio_catalog

LIVE=PACKAGE_ROOT/'_00 Live profiles'
SHARED=PACKAGE_ROOT/'_Auto Deploy/Install-BMTradingPortfolio.ps1'
CONFIG=json.loads((LIVE/'Profiles.json').read_text())


def powershell(script):
    result=subprocess.run(['powershell.exe','-NoLogo','-NoProfile','-ExecutionPolicy','Bypass','-Command',script],
                          capture_output=True,text=True,timeout=45,cwd=LIVE)
    assert result.returncode==0,result.stdout+result.stderr
    return result.stdout


def quote(path):
    return "'"+str(path).replace("'","''")+"'"


def import_helper(path,names):
    return f"""function Import-CalyxHelpers($path,$names) {{
 $tokens=$null;$errors=$null;$ast=[Management.Automation.Language.Parser]::ParseFile($path,[ref]$tokens,[ref]$errors)
 if($errors.Count){{throw 'PowerShell parse errors'}}
 foreach($name in $names){{
   $found=@($ast.FindAll({{param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst]}},$true)|Where-Object Name -eq $name)
   if($found.Count -ne 1){{throw ('Ambiguous helper '+$name)}}
   . ([scriptblock]::Create($found[0].Extent.Text))
   Set-Item ('Function:global:'+$name) (Get-Item ('Function:'+$name)).ScriptBlock
 }}
}}
Import-CalyxHelpers {quote(path)} @({','.join(quote(n) for n in names)})
"""


def test_named_bats_and_website_are_synchronized():
    publication={p['slug']:p for p in portfolio_catalog()['portfolios']}
    assert len(CONFIG['profiles'])==4 and len(list(LIVE.glob('*.bat')))==4
    for profile in CONFIG['profiles']:
        assert publication[profile['slug']]['launcher']==profile['file']
        assert publication[profile['slug']]['ea_count']==profile['eas']
        bat=(LIVE/profile['file']).read_text()
        assert '%~dp0Start-LiveProfile.ps1' in bat and f'-Portfolio "{profile["slug"]}"' in bat
        assert profile['default_usd']==publication[profile['slug']]['risk_defaults']['fixed']
    assert CONFIG['profiles'][-1]['default_news_percent']==.1
    manifest=json.loads((LIVE/'Packages/FTMO/PACKAGE.json').read_text())
    assert {e['slug']:e['inputs'] for e in manifest['entries']}=={e['slug']:e['inputs'] for e in publication['ftmo']['members']}


@pytest.mark.skipif(os.name!='nt',reason='Windows launcher validation')
@pytest.mark.parametrize('slug',['ftmo','current14-orb05','orbs-only','full-eas'])
def test_validate_only_is_offline_and_does_not_change_files(slug):
    before=hashlib.sha256(SHARED.read_bytes()).hexdigest()
    result=powershell(f"& {quote(LIVE/'Start-LiveProfile.ps1')} -Portfolio '{slug}' -ValidateOnly")
    assert 'Finding MT5' not in result and 'Selected:' not in result and 'Account:' not in result
    assert any(value in result for value in ('No account accessed','No MT5/API/account accessed','No terminal enumeration'))
    assert before==hashlib.sha256(SHARED.read_bytes()).hexdigest()


@pytest.mark.skipif(os.name!='nt',reason='Windows pure input helper')
@pytest.mark.parametrize('mode,value',[('FIXED_USD',75),('PERCENT',.75)])
def test_ftmo_allocation_and_both_di_prompts_preserve_original_strategy(mode,value):
    package=LIVE/'Packages/FTMO'
    script=import_helper(SHARED,['Read-SetInputs'])+import_helper(package/'Install-Portfolio.ps1',['Get-FTMOPresetInputs'])
    script+=f"""
 $Package={quote(package/'package')};$RiskMode='{mode}';[double]$RiskValue={value};$UsdJpyDIFilter='OFF'
 $manifest=Get-Content -Raw -LiteralPath {quote(package/'PACKAGE.json')}|ConvertFrom-Json
 $out=@();foreach($entry in $manifest.entries){{
   $input=Get-FTMOPresetInputs $entry 'OFF'
   $out+=@{{slug=$entry.slug;inputs=$input}}
 }};$out|ConvertTo-Json -Depth 8 -Compress
 """
    entries=json.loads(powershell(script))
    assert len(entries)==14
    for entry in entries:
        inputs=entry['inputs']
        assert inputs['FTMOAllocationMode']==('0' if mode=='FIXED_USD' else '1')
        assert float(inputs['FTMOAllocationValue'])==value
        assert float(inputs['InpRiskPercent'])==.5
        if entry['slug'] in ('nasdaq-5m-candle-momentum','usdjpy-london-open-momentum'):
            assert inputs['InpRequireDIAgreement']=='false'
        if entry['slug']=='usdjpy-london-open-momentum':
            assert inputs['InpUseADXFilter']=='true' and float(inputs['InpADXMinimum'])==20


@pytest.mark.skipif(os.name!='nt',reason='Windows pure input helper')
@pytest.mark.parametrize('mode,value',[('FIXED_USD',75),('PERCENT',.75)])
def test_current_portfolio_risk_and_per_ea_di_inputs(mode,value):
    package=PACKAGE_ROOT/'Current14 Plus ORB05 Portfolio 2026-10-08'
    script=import_helper(SHARED,['Read-SetInputs'])+import_helper(package/'Install-Portfolio.ps1',['Get-EffectiveInputs'])
    script+=f"""
 $RiskMode='{mode}';[double]$RiskValue={value};$NasdaqDIFilter='OFF';$UsdJpyDIFilter='OFF'
 $ActiveLogin=1;$ActiveServer='OFFLINE-FIXTURE';$InstallNonce='offline-fixture'
 $manifest=Get-Content -Raw -LiteralPath {quote(package/'Package.json')}|ConvertFrom-Json
 $out=@();foreach($entry in $manifest.entries){{
   $item=[pscustomobject]@{{Key=$entry.key;SetFullPath=Join-Path {quote(package)} $entry.set;BrokerSymbol=$entry.canonical;Hourly=$false}}
   $out+=@{{slug=$entry.key;inputs=(Get-EffectiveInputs $item)}}
 }};$out|ConvertTo-Json -Depth 8 -Compress
 """
    entries=json.loads(powershell(script))
    assert len(entries)==15
    for entry in entries:
        inputs=entry['inputs']
        assert inputs['InpPortfolioRiskMode']==('1' if mode=='FIXED_USD' else '0')
        assert float(inputs['InpPortfolioFixedUSD' if mode=='FIXED_USD' else 'InpPortfolioPercent'])==value
        if entry['slug'] in ('nasdaq-5m-candle-momentum','usdjpy-london-open-momentum'):
            assert inputs['InpRequireDIAgreement']=='false'


def test_isolated_ftmo_guard_keeps_ceiling_and_origins():
    guard=(LIVE/'Packages/FTMO/CalyxFTMOGuard.mqh').read_text()
    assert 'MathMin(50.0,requested)' in guard and 'FTMOAllocationValid' in guard
    assert 'FTMOAllocationBudget()/unit' in guard
    for folder,n in [('FTMO',14),('ORB-only',5)]:
        package=LIVE/'Packages'/folder
        binaries=list(package.rglob('*.ex5'))
        assert len({hashlib.sha256(p.read_bytes()).hexdigest() for p in binaries})==n
        logs=list(package.rglob('*.compile.log'))
        assert len(logs)==n
        for log in logs:
            raw=log.read_bytes();text=raw.decode('utf-16' if raw.startswith(b'\xff\xfe') else 'utf-8-sig')
            assert '0 errors, 0 warnings' in text
