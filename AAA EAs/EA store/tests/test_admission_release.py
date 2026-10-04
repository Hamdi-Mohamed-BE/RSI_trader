"""Final filter configuration; offline evidence, no live account access."""
import hashlib,json
from pathlib import Path
from datetime import date
import pytest
from fastapi.testclient import TestClient
from app.catalog import get_product,PACKAGE_ROOT
from app.main import app
from app.admission_release import FILTERS,MANAGED_SLUGS,VERSION,ROOT,verified_payload
from app.evidence_cache import load_product_cache,load_portfolio_cache,DEFAULT_PERIOD
from app.store.deliverables import deliverable_for

SELECTION=json.loads((ROOT/'SELECTION.json').read_text())
OLD=PACKAGE_ROOT/'ADX DI Deployment 2026-10-03'
STUDY=PACKAGE_ROOT/'ADX DI Five Bot Review 2026-10-03'
BEFORE=json.loads((ROOT/'BEFORE.json').read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def values(p):return dict(l.split('=',1) for l in p.read_text().splitlines() if '=' in l)
def result(slug,period):
    p=SELECTION['profiles'][slug]
    if period=='1y':
        root=OLD if p['filter_status']=='kept' else STUDY
        return json.loads((root/'native'/(p['key']+'-ORIGINAL')/'result.json').read_text())
    arm='filtered' if p['filter_status']=='kept' else 'baseline'
    rows=json.loads((OLD/'Long Window Comparison/SUMMARY.json').read_text())
    return next(r for r in rows if r['key']==p['key'] and r['period']==period and r['arm']==arm)

@pytest.mark.parametrize('slug',sorted(MANAGED_SLUGS))
def test_catalog_and_buyer_use_exact_final_preset(slug):
    profile=SELECTION['profiles'][slug];p=get_product(slug)
    assert PACKAGE_ROOT/p.expert_source==PACKAGE_ROOT/profile['expert']
    assert not p.recommended_safe_mode and not p.admission_provisional
    assert p.admission_filter==FILTERS.get(slug)
    assert sha(PACKAGE_ROOT/p.expert_source)==profile['expert_sha']
    assert values(PACKAGE_ROOT/p.set_source)==profile['inputs']
    d=deliverable_for(p);assert d.expert_path==PACKAGE_ROOT/p.expert_source
    for k in ('InpUseADXFilter','InpADXMinimum','InpRequireDIAgreement','InpADXTimeframe'):
        if profile['filter_status']=='kept':assert d.inputs[k]==profile['inputs'][k]
        else:assert k not in d.inputs
    if profile['key']=='asia':assert d.inputs['InpUseMarkovRegimeFilter']=='true'
    if profile['key']=='ema3':assert d.inputs['InpUseMarkovRegimeFilter']=='false'
    if profile['key']=='trend':assert float(d.inputs['InpRewardRisk'])==.6

@pytest.mark.parametrize('slug',sorted(MANAGED_SLUGS))
@pytest.mark.parametrize('period',['1y','3y','5y'])
def test_cache_matches_exact_native_selected_arm(slug,period):
    s=result(slug,period)['stats'];p=load_product_cache(slug,'standard',period)
    assert p['configuration_release']==VERSION and p['is_current_configuration']
    assert p['stats']['trades']==s['trades']
    assert p['stats']['profit_factor']==pytest.approx(s['pf'])
    assert p['stats']['net_profit']==pytest.approx(s['net'],abs=.011)
    assert p['stats']['max_equity_drawdown_pct']==s['equity_dd_pct']
    start=date(2026-int(period[:-1]),10,2);end=date(2026,10,2)
    audited,rows=verified_payload(get_product(slug),'standard',period,start,end)
    assert len(rows)==s['trades'] and audited['source_fingerprint']['expert_sha256']==SELECTION['profiles'][slug]['expert_sha']

@pytest.mark.parametrize('slug',sorted(MANAGED_SLUGS))
def test_six_months_honestly_archived(slug):
    p=load_product_cache(slug,'standard','6m')
    assert p and not p['is_current_configuration'] and p['evidence_status']=='Archived configuration'
    assert 'Archived previous configuration' in p['evidence_label'] and 'not a result for the final selection' in p['notice']

def test_ftmo_guard_risk_roster_and_other_binaries_preserved():
    folder=PACKAGE_ROOT/'FTMO Thirteen EA Deployment 2026-09-27'
    after=json.loads((folder/'PACKAGE.json').read_text());before=BEFORE['ftmo_manifest']
    assert after['admission_release']==VERSION and after['risk_usd']==before['risk_usd']==50
    assert not after['news_enabled'] and len(after['entries'])==len(before['entries'])==14
    assert after['guard_sha']==before['guard_sha']==BEFORE['guard_sha']==sha(folder/'CalyxFTMOGuard.mqh')
    changed=set()
    for old,row in zip(before['entries'],after['entries']):
        assert old['slug']==row['slug'] and row['inputs']['InpRiskPercent']=='0.5' and row['inputs']['FTMOExpectedLogin']=='0'
        if old['expert_sha']!=row['expert_sha']:changed.add(row['slug'])
        if row['slug']=='usdjpy-london-open-momentum':
            assert row['inputs']==old['inputs'] and row['expert_sha']==old['expert_sha']
            assert row['inputs']['InpUseADXFilter']=='true' and row['inputs']['InpRequireDIAgreement']=='true'
        elif row['slug'] in ('ema3','xau-trend-progression'):
            assert not any(k in row['inputs'] for k in ('InpUseADXFilter','InpRequireDIAgreement'))
        else:assert row['inputs']==old['inputs'] and row['expert_sha']==old['expert_sha']
    assert changed=={'ema3','xau-trend-progression'}
    assert 'asia-breakout' not in {e['slug'] for e in after['entries']}
    for name,digest in after['files'].items():assert sha(folder/'package'/name)==digest

def test_rsi_and_licensed_client_files_unchanged():
    assert all(sha(Path(p))==h for p,h in BEFORE['unchanged_hashes'].items())
    p=get_product('xau-rsi-vwap');assert not p.admission_filter
    assert load_product_cache(p.slug,'standard','1y')['stats']['trades']==49
    entries=json.loads((PACKAGE_ROOT.parents[1]/'clients/_owner/top5/manifest.json').read_text())['entries']
    assert len(entries)==5 and {e['slug'] for e in entries}.isdisjoint(MANAGED_SLUGS)

def test_old_portfolio_forecasts_not_current():
    p=load_portfolio_cache('standard','1y')
    assert not p['is_current_configuration'] and 'Archived' in p['label'] and 'not been revalidated' in p['notice']

@pytest.mark.parametrize('path',['/eas','/portfolio','/pricing','/risk','/prop-simulator','/eas/ema3','/eas/asia-breakout','/eas/xau-trend-progression','/eas/usdjpy-london-open-momentum'])
def test_release_notice_and_pages_render(path):
    with TestClient(app) as client:r=client.get(path)
    assert r.status_code==200 and 'Entry filters updated:' in r.text
    assert 'USDJPY ADX ≥20 + DI' in r.text and 'Added ADX/DI removed' in r.text
    assert 'provisional: 29 trades' not in r.text

def test_default_year_api_identity():
    assert DEFAULT_PERIOD=='1y'
    with TestClient(app) as c:
        p=c.get('/api/evidence/ema3/series').json()
        assert p['is_current_configuration'] and p['stats']['trades']==44
        assert not c.get('/api/evidence/ema3/series?period=6m').json()['is_current_configuration']

@pytest.mark.parametrize('slug',sorted(MANAGED_SLUGS))
def test_builder_keeps_audited_evidence(slug):
    from tools.precompute_evidence_cache import run_native,product_payload
    p=get_product(slug);start=date(2025,10,2);end=date(2026,10,2)
    payload,rows=verified_payload(p,'standard','1y',start,end)
    report=run_native(p,'standard','1y',start,end,force=False)
    rebuilt,rebuilt_rows=product_payload(p,'standard','1y',start,end,report)
    assert rebuilt==payload and rebuilt_rows==rows
    with pytest.raises(RuntimeError,match='fixed windows'):verified_payload(p,'standard','1y',date(2025,10,1),end)
    with pytest.raises(RuntimeError,match='frozen ADX/DI'):run_native(p,'standard','1y',start,end,force=True)

def test_historical_comparison_preserved():
    from bs4 import BeautifulSoup
    p=BeautifulSoup((OLD/'Long Window Comparison/Comparison.html').read_text(encoding='utf-8'),'html.parser')
    assert len(p.select('table'))==3 and len(p.select('svg'))==15 and len(p.select('tbody tr'))==27
