import json
import math
from datetime import date,timedelta

import pytest
from fastapi.testclient import TestClient

from app.catalog import PACKAGE_ROOT, get_website_catalog, get_sellable_catalog
from app.ea_review import review_data
from app.main import app
from app.portfolios import portfolio_catalog, portfolio_by_slug

client = TestClient(app)


def test_publication_preserves_individual_catalogue_and_review():
    d = portfolio_catalog()
    assert d['counts'] == {'active':3,'disabled':1}
    assert not d['warnings']
    assert len(get_website_catalog())==37 and len(get_sellable_catalog())==35
    assert review_data()['counts']=={'live':25,'paused':6,'review':6}
    assert {p['slug']:p['ea_count'] for p in d['portfolios']}=={'ftmo':14,'current14-orb05':15,'orbs-only':5,'full-eas':37}


def test_current_portfolio_matches_saved_manifests():
    ft = json.loads((PACKAGE_ROOT/'FTMO Thirteen EA Deployment 2026-09-27/PACKAGE.json').read_text())
    new = json.loads((PACKAGE_ROOT/'Current14 Plus ORB05 Portfolio 2026-10-08/Package.json').read_text())
    assert {m['slug'] for m in portfolio_by_slug('ftmo')['members']}=={m['slug'] for m in ft['entries']}
    p = portfolio_by_slug('current14-orb05')
    assert {m['slug'] for m in p['members']}=={m['key'] for m in new['entries']}
    assert {m['slug'] for m in p['members'] if m['target_rr']==.5 and 'ORB' in m['variant']}==set(new['orb_keys'])
    for m in p['members']:
        assert m['inputs']==next(e['inputs'] for e in new['entries'] if e['key']==m['slug'])
    assert next(m for m in p['members'] if m['slug']=='nasdaq-5m-candle-momentum')['target_rr'] is None


def test_orb_thresholds_no_duplicates_or_undefined_pf():
    p = portfolio_by_slug('orbs-only')
    assert p['status']=='disabled' and p['launcher']=='ORB-only - 50pct+ PF1.15+.bat'
    for member in p['members']:
        assert member['stats']['win_rate']>=50
        assert math.isfinite(member['stats']['pf']) and member['stats']['pf']>=1.15
    assert {m['target_rr'] for m in p['members']}=={.5,2,4}
    assert 'Not selected' in client.get('/portfolios/orbs-only').text
    assert 'Undefined' in client.get('/portfolios/orbs-only').text


@pytest.mark.parametrize('slug,n',[('ftmo',14),('current14-orb05',15),('orbs-only',5),('full-eas',37)])
def test_detail_contains_history_and_risk_and_members(slug,n):
    response = client.get('/portfolios/'+slug)
    assert response.status_code==200
    html=response.text
    assert html.count('data-member=')==n
    for text in ('Deep risk &amp; drawdown rules','Historical closed-balance curve','Profit factor','Win rate','Max win streak','Max losing streak','Payoff ratio','end exclusive'):
        assert text in html
    assert client.get('/api/portfolios/'+slug).json()['ea_count']==n


@pytest.mark.parametrize('status,count',[('all',4),('active',3),('disabled',1)])
def test_portfolio_status_filter(status,count):
    page=client.get('/portfolios?status='+status)
    assert page.status_code==200 and page.text.count('data-portfolio=')==count
    assert 'not observed live installation' in page.text


def test_no_other_portfolio_period_substituted_or_stale_claims():
    current=client.get('/api/portfolios/current14-orb05?period=5y').json()
    page=client.get('/portfolios/current14-orb05?period=5y')
    assert page.status_code==200
    if current['available']:
        assert current['start']=='2021-10-06' and current['end_exclusive']=='2026-10-06'
        assert current['evidence_kind']=='matched-five-year-native-signal-ledger-offline-portfolio-replay'
    else:
        assert 'No matching 5 years history' in page.text and 'data-evidence-available="false"' in page.text
    assert client.get('/portfolios/no-such-portfolio').status_code==404
    assert client.get('/api/portfolios/no-such-portfolio').status_code==404
    assert client.get('/portfolios?status=nonsense').status_code==422
    for period in ('6m','1y','3y','5y'):
        page=client.get('/portfolios/full-eas?period='+period)
        assert page.status_code==200
        history=client.get('/api/portfolios/full-eas?period='+period).json()
        if history.get('evidence_kind'):
            assert 'not a native simultaneous shared-margin portfolio' in page.text
        else:assert 'Not a current 37-EA shared-account backtest' in page.text
        assert 'Current members missing' in page.text
    assert 'No shared daily stop' in client.get('/portfolios/current14-orb05').text
    assert 'NOT forced liquidation' in client.get('/portfolios/ftmo').text


def test_metrics_reconcile_with_curves_and_months():
    for p in portfolio_catalog()['portfolios']:
        for h in p['history']:
            if not h['available']:
                assert not h['stats'] and not h['curve'] and not h['streaks']
                continue
            s=h['stats']
            assert s['final_balance']-s['initial_balance']==pytest.approx(s['net_profit'],abs=.05)
            assert (s['final_balance']/s['initial_balance']-1)*100==pytest.approx(s['return_pct'],abs=.005)
            assert h['curve'][-1]['balance']==pytest.approx(s['final_balance'],abs=.05)
            assert sum(m['net_profit'] for m in h['months'])==pytest.approx(s['net_profit'],abs=.05)
            start,end=date.fromisoformat(h['start']),date.fromisoformat(h['end_exclusive'])
            days=sum((start+timedelta(days=i)).weekday()<5 for i in range((end-start).days))
            assert s['trades_per_weekday']==pytest.approx(s['trades']/days)
            assert s['trades_per_day']==pytest.approx(s['trades']/(end-start).days)


def test_full_basket_presets_are_preserved_and_not_mislabelled_ftmo():
    p=portfolio_by_slug('full-eas')
    assert all(m['inputs'] for m in p['members'])
    assert {m['slug'] for m in p['members']}=={m.slug for m in get_website_catalog()}
    assert 'closed' in next(r['detail'] for r in p['rules'] if r['title']=='Daily closed-loss stop').lower()


def test_publication_does_not_need_research_files_on_web_host(tmp_path,monkeypatch):
    import app.portfolios as module
    monkeypatch.setattr(module,'PACKAGE_ROOT',tmp_path)
    module._load.cache_clear()
    try:
        assert portfolio_catalog()['counts']=={'active':3,'disabled':1}
    finally:
        module._load.cache_clear()


@pytest.mark.parametrize('slug',['ftmo','current14-orb05','orbs-only','full-eas'])
@pytest.mark.parametrize('period',['3m','6m','1y','3y','5y'])
def test_periods_have_matched_api_and_inline_metrics(slug,period):
    response=client.get(f'/api/portfolios/{slug}?period={period}')
    assert response.status_code==200
    h=response.json()
    assert h['id']==period
    page=client.get(f'/portfolios/{slug}/history?period={period}&compact=true')
    assert page.status_code==200 and f'data-loaded-period="{period}"' in page.text
    if h['available']:
        assert h['start']>=h['requested_start']
        assert h['stats']['max_win_streak']==h['streaks']['max_win_streak']
        assert h['stats']['max_loss_streak']==h['streaks']['max_loss_streak']
        assert h['chart']
    else:
        assert not h['stats'] and h['chart'] is None and not h['sharpe_svg'] and not h['streak_svg']


def test_recent_windows_are_calendar_months_and_do_not_change_members():
    p=portfolio_by_slug('current14-orb05')
    assert [(h['id'],h['start']) for h in p['history'][:3]]==[
        ('3m','2026-07-06'),('6m','2026-04-06'),('1y','2025-10-06')]
    assert p['history'][0]['stats']['trades']<p['history'][1]['stats']['trades']<p['history'][2]['stats']['trades']
    full=portfolio_by_slug('full-eas')
    assert full['history'][-1]['coverage']=='partial'
    end='2026-10-06' if full['history'][-1].get('evidence_kind') else '2026-08-31'
    assert all(h['end_exclusive']==end for h in full['history'])
    assert client.get('/portfolios?period=3m').text.count('data-loaded-period="3m"')==4
    assert client.get('/api/portfolios/ftmo?period=invalid').status_code==422
    assert client.get('/portfolios/ftmo?period=invalid').status_code==404


def test_ready_long_history_has_exact_roster_and_quality_disclosures():
    profile=portfolio_by_slug('orbs-only')
    assert profile['history_provenance']['tested_members']==5
    assert profile['history_provenance']['selection_frozen']
    for period,start,count in [('3y','2023-10-06',358),('5y','2021-10-06',574)]:
        h=client.get('/api/portfolios/orbs-only?period='+period).json()
        assert h['available'] and h['coverage']=='complete' and not h['missing_members']
        assert h['start']==start and h['end_exclusive']=='2026-10-06'
        assert h['stats']['trades']==count and h['member_coverage']=={'tested':5,'total':5}
        assert 'not independent native tests' in h['scope']
        assert 'MT5 may synthesize' in h['scope'] and h['source_history_quality']


@pytest.mark.parametrize('slug,members',[('ftmo',14),('current14-orb05',15),('orbs-only',5)])
def test_selected_portfolio_long_windows_are_ready_and_current(slug,members):
    p=portfolio_by_slug(slug)
    assert p['history_provenance']['tested_members']==p['ea_count']==members
    for period,start in [('3y','2023-10-06'),('5y','2021-10-06')]:
        h=client.get('/api/portfolios/'+slug,params={'period':period}).json()
        assert h['available'] and h['coverage']=='complete'
        assert h['member_coverage']=={'tested':members,'total':members}
        assert h['start']==start and h['end_exclusive']=='2026-10-06'
        assert h['evidence_kind']=='matched-five-year-native-signal-ledger-offline-portfolio-replay'
        assert h['stats']['max_daily_equity_drawdown_pct'] is None
        assert h['source_history_quality']
        assert h['stats']['trades']>0


def test_forced_boundary_exits_are_disclosed_in_long_current_history():
    h=client.get('/api/portfolios/current14-orb05?period=5y').json()
    assert h['stats']['trades']==5086
    assert h['source_boundary_exclusions']=={'ema3':1,'nasdaq-5m-candle-momentum':1}
    assert 'end-of-test liquidations are excluded' in h['scope']


def test_changed_manifest_is_disclosed(tmp_path,monkeypatch):
    import app.portfolios as module
    location=tmp_path/'Current14 Plus ORB05 Portfolio 2026-10-08/Package.json'
    location.parent.mkdir();location.write_text('{}')
    monkeypatch.setattr(module,'PACKAGE_ROOT',tmp_path);module._load.cache_clear()
    try:
        assert 'manifest changed' in portfolio_catalog()['warnings'][0]
    finally:
        module._load.cache_clear()


@pytest.mark.parametrize('period',['3m','6m','1y','3y','5y'])
def test_full_long_history_is_current_partial_not_archived_or_zero_filled(period):
    h=client.get('/api/portfolios/full-eas',params={'period':period}).json()
    assert h['available'] and h['coverage']=='partial'
    assert h['member_coverage']=={'tested':36,'total':37}
    assert h['missing_members']==['gold-news-v9-direction']
    assert h['end_exclusive']=='2026-10-06'
    assert h['evidence_kind']=='matched-five-year-native-signal-ledger-offline-portfolio-replay'
    assert len(h['source_calendar_audits'])==4
    for audit in h['source_calendar_audits'].values():
        assert audit['expected']==159 and not audit['boundary_violation']
        assert 0<=audit['placed']<=audit['attempted']<=audit['expected']
        assert audit['parity_verified']
    assert 'not a native simultaneous shared-margin portfolio' in h['scope']
    assert h['stats']['max_daily_equity_drawdown_pct'] is None
