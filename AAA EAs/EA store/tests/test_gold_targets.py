"""User-selected Gold target mapping and evidence identity, never live deployment."""
import hashlib
import json
import re
from datetime import date

import pytest
from fastapi.testclient import TestClient
from app.catalog import PACKAGE_ROOT, get_product
from app.gold_targets import ROOT, verified_payload
from app.main import app

def read(path): return path.read_text(encoding='utf-8-sig')
def values(path): return dict(l.split('=',1) for l in read(path).splitlines() if '=' in l)

@pytest.mark.parametrize('slug,target',[('xau-trend-progression',.6),('xau-slow-trend',1)])
def test_normal_catalog_selects_target_and_research_status(slug,target):
    p=get_product(slug)
    assert float(values(PACKAGE_ROOT/p.set_source)['InpRewardRisk'])==target
    assert p.evidence.status=='Research evidence'
    assert not p.recommended_dynamic_mode
    if slug=='xau-slow-trend':
        assert float(values(PACKAGE_ROOT/p.dynamic_set_source)['InpRewardRisk'])==.5
        assert p.dynamic_evidence.status=='Research evidence'

@pytest.mark.parametrize('slug,mode,trades,net,pf',[
    ('xau-trend-progression','standard',38,437.90,1.24067184),
    ('xau-slow-trend','standard',184,2538.13,1.198),
    ('xau-slow-trend','dynamic',231,1090.14,1.106),
])
def test_exact_native_ledgers_and_dates(slug,mode,trades,net,pf):
    p,rows=verified_payload(get_product(slug),mode,'1y',date(2025,10,1),date(2026,10,2))
    assert len(rows)==p['stats']['trades']==trades
    assert sum(r['net_profit'] for r in rows)==pytest.approx(net,abs=.011)
    assert p['stats']['profit_factor']==pytest.approx(pf,abs=.001)
    assert p['evidence_status']=='Research evidence'
    assert 'not untouched validation' in p['notice']
    if mode=='dynamic': assert 'NOT guarded' in p['notice']
    with pytest.raises(RuntimeError,match='independent fixed windows'):
        verified_payload(get_product(slug),mode,'1y',date(2025,9,1),date(2026,10,2))

def test_source_only_changes_reward_default():
    release=json.loads(read(ROOT/'SELECTION.json'))
    original={
        'xau-trend-progression':PACKAGE_ROOT/'Trend Progression Research 2026-09-02/EA/Trend Progression EA.mq5',
        'xau-slow-trend':PACKAGE_ROOT/'Slow Multi Asset Trend Research 2026-09-06/EA/Calyx Slow Trend EA.mq5',
    }
    strip=lambda t: re.sub(r'(input\s+double\s+InpRewardRisk\s*=\s*)[\d.]+',r'\g<1>TARGET',t)
    for slug,p in release['profiles'].items():
        source=(PACKAGE_ROOT/p['expert']).with_suffix('.mq5')
        assert strip(read(source))==strip(read(original[slug]))
        assert hashlib.sha256(original[slug].read_bytes()).hexdigest()==p['original_source_sha']

def test_pages_label_normal_and_ftmo_target_comparison():
    c=TestClient(app)
    page=c.get('/eas/xau-slow-trend?mode=dynamic&period=1y')
    assert page.status_code==200
    assert 'Normal target 1R' in page.text and 'FTMO target 0.5R' in page.text
    assert 'Research evidence' in page.text and 'NOT guarded' in page.text
    data=c.get('/api/evidence/xau-slow-trend/series?mode=dynamic&period=1y').json()
    assert data['stats']['trades']==231
    comparison=c.get('/api/evidence/xau-slow-trend/series?mode=compare&period=1y').json()
    assert {d['label'] for d in comparison['datasets']}=={'Normal target 1R','FTMO target 0.5R'}

def test_ftmo_preserves_guard_and_selected_trend_target():
    m=json.loads(read(PACKAGE_ROOT/'FTMO Thirteen EA Deployment 2026-09-27/PACKAGE.json'))
    assert m['risk_usd']==50 and not m['news_enabled']
    entry=next(e for e in m['entries'] if e['slug']=='xau-trend-progression')
    assert float(entry['inputs']['InpRewardRisk'])==.6
    assert entry['inputs']['FTMOExpectedLogin']=='0'
    assert entry['inputs']['InpRiskPercent']=='0.5'
