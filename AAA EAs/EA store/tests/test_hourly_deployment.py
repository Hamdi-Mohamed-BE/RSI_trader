import hashlib
import json
import math
from app.catalog import PACKAGE_ROOT, get_catalog, get_sellable_catalog, parse_installer_items
from app.evidence_cache import load_product_summary

ROOT=PACKAGE_ROOT/'Hourly Profiles Deployment 2026-10-04'

def test_build_and_reference_fingerprints():
    release=json.loads((ROOT/'RELEASE.json').read_text())
    assert release['compile_clean'] and release['not_installed_on_active_terminal']
    source=ROOT/'EA/CalyxHourlyProfiles History Sized.mq5'
    assert hashlib.sha256(source.read_bytes()).hexdigest()==release['source_sha256']
    assert hashlib.sha256(source.with_suffix('.ex5').read_bytes()).hexdigest()==release['expert_sha256']
    code=source.read_text()
    assert 'AccountInfoDouble(ACCOUNT_BALANCE)*InpRiskPercent/100.0' in code
    assert 'OrderCalcProfit(' in code and 'CalyxAdaptiveRiskMultiplier(InpAdaptivePortfolioControls,InpMagic)' in code
    assert 'MathFloor((requested-lo)/step+1e-10)' in code
    assert 'trade.Buy(lots,_Symbol,0,0,0,comment)' in code and 'trade.Sell(lots,_Symbol,0,0,0,comment)' in code
    for row in release['entries']:
        worst=row['worst_trade']
        reference=math.ceil(abs(worst['net_profit'])/abs(worst['gross_profit']/worst['price_move'])*100000)/100000
        assert row['historical_loss_points']==reference
        original=PACKAGE_ROOT/'Indices Hourly EA Pipeline 2026-10-03/CalyxHourlyProfiles.mq5'
        assert hashlib.sha256(original.read_bytes()).hexdigest()==release['original_source_sha256']

def test_installed_roster_is_37_but_checkout_stays_35():
    assert len(parse_installer_items())==len(get_catalog())==37
    assert len(get_sellable_catalog())==35
    for slug in ('us30-hourly-profiles','us100-hourly-profiles'):
        assert load_product_summary(slug,'standard','1y')['is_current_configuration'] is False

def test_default_and_selected_risk_contract():
    script=(PACKAGE_ROOT/'_Auto Deploy/Start-Dynamic-Portfolio.ps1').read_text()
    assert '[double]$HourlyRiskPercent = 0.5' in script
    assert 'if ($raw) { $riskWasSelected = $true }' in script
    assert '$HourlyRiskPercent = $RiskValue' in script
    assert "'-HourlyUseDefaultRisk'" in script

def test_native_smoke_matches_current_compiled_build():
    release=json.loads((ROOT/'RELEASE.json').read_text())
    smoke=json.loads((ROOT/'FUNCTIONAL.json').read_text())
    assert smoke['passed'] and smoke['no_active_terminal_changed']
    assert len(smoke['checks'])==4
    for row in smoke['checks']:
        assert row['expert_sha256']==release['expert_sha256']
        assert row['entries']>0 and row['no_account_failure']
