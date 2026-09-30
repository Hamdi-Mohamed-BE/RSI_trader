from pathlib import Path
import hashlib
import json
from fastapi.testclient import TestClient
from app.catalog import PACKAGE_ROOT, get_product
from app.main import app

STORE = Path(__file__).resolve().parents[1]
SLUG = 'nasdaq-5m-candle-momentum'

def test_selected_management_and_archive_sources():
    p = get_product(SLUG)
    assert p.recommended_dynamic_mode and p.dynamic_mode_label == 'DI + Wide Stop + ATR'
    assert 'DI ATR Deployment 2026-09-28' in p.dynamic_expert_source
    assert 'OPTIMIZED 2P5R - HARD' in p.set_source
    values = dict(l.split('=',1) for l in (PACKAGE_ROOT/p.dynamic_set_source).read_text().splitlines() if '=' in l)
    expected = dict(InpRequireDIAgreement='true', InpDIPeriod='14', InpEMAPeriod='12',
                    InpStopMode='2', InpInitialStopPercent='0.60', InpUseFixedTarget='false',
                    InpUseATRTrailing='true', InpTrailingATR='6.0', InpTrailStartR='1.0',
                    InpCloseAtSessionEnd='false', InpUseMATrailing='false')
    assert all(values[k] == v for k,v in expected.items())

def test_each_period_uses_exact_selected_binary_and_ledger():
    p = get_product(SLUG)
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    for period,n,ret in [('6m',89,18.97),('1y',179,55.45),('3y',536,162.16),('5y',923,212.72)]:
        folder = STORE/'data/evidence-cache/v1/products'/SLUG/'dynamic'
        cache = json.loads((folder/f'{period}.json').read_text())
        trades = json.loads((folder/f'{period}.trades.json').read_text())
        assert cache['stats']['trades'] == len(trades) == n
        assert cache['stats']['return_pct'] == ret
        assert cache['available_to'] == '2026-09-25'
        assert cache['source_fingerprint']['expert_sha256'] == sha(PACKAGE_ROOT/p.dynamic_expert_source)
        assert cache['source_fingerprint']['settings_sha256'] == sha(PACKAGE_ROOT/p.dynamic_set_source)
        assert abs(sum(t['net_profit'] for t in trades)-cache['stats']['net_profit']) < .02
        assert 'Retrospective' in cache['notice'] and 'generated' in cache['notice']

def test_public_page_explains_new_default_without_old_launcher_claim():
    response = TestClient(app).get(f'/eas/{SLUG}?period=1y')
    assert response.status_code == 200
    assert 'DI + Wide Stop + ATR' in response.text
    assert '0.60%' in response.text and 'overnight' in response.text
    assert 'keep the original Standard EA' not in response.text
    assert '51.4' in response.text

def test_ftmo_guarded_package_keeps_risk_and_news_policy():
    root = PACKAGE_ROOT/'FTMO Thirteen EA Deployment 2026-09-27'
    manifest = json.loads((root/'PACKAGE.json').read_text())
    assert manifest['risk_usd'] == 50 and manifest['news_enabled'] is False
    assert len(manifest['entries']) == 14  # 13 original + 3 Way Gold (2026-09-30)
    entry = next(e for e in manifest['entries'] if e['slug']==SLUG)
    assert entry['inputs']['InpRiskPercent'] == '0.5'
    assert entry['inputs']['FTMOExpectedLogin'] == '0'
    assert entry['inputs']['InpAdaptivePortfolioControls'] == 'false'
    assert entry['inputs']['InpUseATRTrailing'] == 'true'
    assert entry['inputs']['InpUseFixedTarget'] == 'false'
    for name,digest in manifest['files'].items():
        assert hashlib.sha256((root/'package'/name).read_bytes()).hexdigest()==digest
