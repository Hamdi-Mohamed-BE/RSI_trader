import hashlib
import json
from datetime import date

import pytest
from fastapi.testclient import TestClient
from app.catalog import PACKAGE_ROOT, get_product, get_sellable_catalog
from app.main import app
from app.news_evidence import load_news_summary
from app.news_profiles import MULTI_PROFILE, MULTI_SLUGS, event_parameters
from tools.precompute_evidence_cache import independent_news_result

ROOT=PACKAGE_ROOT/'News Pulse Multi Asset Event Parameters 2026-09-19'
DEPLOY=ROOT/'Deployment'
PERIODS={'6m':'2026-03-05','1y':'2025-09-05','3y':'2023-09-05','5y':'2021-09-05'}

@pytest.mark.parametrize('slug', sorted(MULTI_SLUGS))
def test_selected_full_candidates_equal_production_params_and_native_parity(slug):
    asset=slug.removeprefix('news-pulse-').upper()
    product=get_product(slug)
    source=(PACKAGE_ROOT/product.expert_source).with_suffix('.mq5')
    code=source.read_text()
    full=json.loads((ROOT/asset/'selected.json').read_text())
    params=event_parameters(asset)
    for kind,p in params.items():
        assert p==full[kind]['full']['params_price']
        line=next(line for line in code.splitlines() if f'asset=="{asset}" && kind=="{kind}"' in line)
        for key,value in [('g_np_lead',int(p[0])),('g_np_anchor',int(p[1])),('g_np_hold',int(p[7]))]:
            assert f'{key}={value};' in line
        for key,value in [('g_np_offset',p[2]),('g_np_stop',p[3]),('g_np_trail_distance',p[6])]:
            assert f'{key}={value:.10f};' in line
    parity=json.loads((DEPLOY/(asset+'-PARITY.json')).read_text())
    assert parity['passed'] and parity['source_sha256']==hashlib.sha256(source.read_bytes()).hexdigest()
    expected=json.loads((ROOT/'native'/(asset+'Fitted')/'stats.json').read_text())
    assert parity['stats']['final_balance']==expected['final_balance']
    assert 'NP_LeadSeconds(candidate_kind)' in code
    assert 'NP_LeadSeconds(g_cached_event_kind)' in code
    assert 'NP_ApplyEventParameters(g_active_event_kind)' in code
    assert 'NP_KindFromComment(PositionGetString(POSITION_COMMENT))' in code
    assert 'Deliberately not OCO' in code
    assert 'int shift=(g_np_anchor==1 ? 0:1);' in code
    assert 'CALENDAR_IMPORTANCE_HIGH' in code and 'NP_IsPrimaryCPIName' in code

@pytest.mark.parametrize('slug', sorted(MULTI_SLUGS))
@pytest.mark.parametrize('period', PERIODS)
def test_native_cache_card_detail_ledger_agree(slug,period):
    product=get_product(slug)
    result,_=independent_news_result(product,'standard',period,date.fromisoformat(PERIODS[period]),date(2026,9,5))
    payload=load_news_summary(slug,period)
    assert payload and payload['strategy_profile']==MULTI_PROFILE and payload['optimization_in_sample']
    assert payload['stats']['net_profit']==result['stats']['net_profit']
    assert payload['stats']['trades']==len(result['trades'])
    with TestClient(app) as client:
        api=client.get(f'/api/evidence/{slug}/series',params={'period':period})
        assert api.status_code==200
        assert api.json()['cached_trade_count']==len(result['trades'])
        trades=api.json()['trades']
        assert sum(t['net_profit'] for t in trades)==pytest.approx(result['stats']['net_profit'],abs=.05)
        assert all(t['cache_slug']==slug for t in trades)
        assert all('commission' in t and 'swap' in t for t in trades)
        for url in ('/eas',f'/eas/{slug}'):
            page=client.get(url,params={'q':product.label,'period':period})
            assert page.status_code==200
            assert f"{payload['stats']['return_pct']:+,.2f}%" in page.text
            assert 'Hindsight-optimized' in page.text

def test_roster_magics_and_bat_routes():
    products=get_sellable_catalog()
    assert len(products)==33
    news=[p for p in products if p.label.startswith('News Pulse ')]
    assert len(news)==4
    magics=[]
    for product in news:
        text=(PACKAGE_ROOT/product.set_source).read_text()
        settings=dict(line.split('=',1) for line in text.splitlines() if '=' in line)
        magics.append(settings['InpMagic'])
        assert settings['InpEnableBuySide']==settings['InpEnableSellSide']=='true'
        assert settings['InpRiskPercent']=='0.75'
        assert settings['InpAdaptivePortfolioControls']=='false'
    assert len(set(magics))==4
    for name in ('BEST RECOMMENDED 2026-09-01.bat','INSTALL AND RUN DYNAMIC CONFIG ON ACTIVE MT5.bat','INSTALL AND RUN FULL SAFE ON ACTIVE MT5.bat','INSTALL AND RUN ON 100K MT5.bat','INSTALL AND RUN ON 900 USD MT5.bat','INSTALL AND RUN ON ACTIVE MT5.bat','RECOMMENDED ADAPTIVE.bat'):
        assert 'XAG/BTC/EURUSD News Pulse v2.17' in (PACKAGE_ROOT/name).read_text()

def test_eurusd_never_uses_xag_legacy_chart():
    from app.main import _verified_news_payload
    assert _verified_news_payload('news-pulse-eurusd') is None
