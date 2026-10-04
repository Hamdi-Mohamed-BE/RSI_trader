from copy import deepcopy
import hashlib
import json
import re
from html import unescape

import pytest
from fastapi.testclient import TestClient

from app.catalog import PACKAGE_ROOT, get_catalog, get_product, get_sellable_catalog, get_website_catalog, get_website_product
from app.evidence_cache import CACHE_ROOT, load_product_cache, load_product_summary, product_trades_path
from app.hourly_profiles import PROFILES, verified_cache
from app.main import app

client = TestClient(app)


def test_website_previews_do_not_change_the_active_roster_or_ledger():
    slugs = set(PROFILES)
    assert {p.slug for p in get_website_catalog()} - {p.slug for p in get_sellable_catalog()} == slugs
    assert not slugs.intersection(p.slug for p in get_catalog())
    assert all(get_product(slug) is None for slug in slugs)  # checkout/simulator lookup excludes them
    assert get_website_product('sp500-hourly-profiles') is None
    release = json.loads((PACKAGE_ROOT/'Indices Hourly EA Pipeline 2026-10-03/WEBSITE-RELEASE.json').read_text())
    for name, digest in release['unchanged_active_artifacts'].items():
        from pathlib import Path
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest
    portfolio = client.get('/portfolio').text
    assert all(f'/eas/{slug}?' not in portfolio for slug in slugs)


@pytest.mark.parametrize('slug', PROFILES)
@pytest.mark.parametrize('period', ('1y','6m'))
def test_recent_pages_have_matching_period_cards_chart_stats_and_ledger(slug, period):
    response = client.get(f'/eas/{slug}?period={period}')
    assert response.status_code == 200
    html = response.text
    text = unescape(re.sub('<[^>]+>', '', html))
    controls = re.search(r'<select[^>]+data-chart-period[^>]*>(.*?)</select>',html,re.S).group(1)
    assert re.findall(r'<option value="([^"]+)"', controls) == ['6m','1y']
    assert 'Research evidence' in text
    assert 'failed the long-history validation gate' in text
    assert 'Zero-spread quotes' in text
    assert 'action="/cart/add"' not in html
    assert 'Current default installer configuration.' not in text
    data = client.get(f'/api/evidence/{slug}/series?period={period}').json()
    rows = json.loads(product_trades_path(slug,'standard',period).read_text())
    stats = data['stats']
    assert stats['trades'] == len(rows) == data['cached_trade_count']
    assert len(data['trades']) == min(500,len(rows))
    net = sum(t['net_profit'] for t in rows)
    assert net == pytest.approx(stats['net_profit'])
    assert data['series'][-1]['balance'] == pytest.approx(10000+net,abs=.011)
    winners = sum(t['net_profit'] for t in rows if t['net_profit']>0)
    losers = -sum(t['net_profit'] for t in rows if t['net_profit']<0)
    assert stats['profit_factor'] == pytest.approx(winners/losers)
    assert all(t['estimated_r'] is None and t['stop_loss'] is None for t in rows)
    for key in ('return_pct','profit_factor','win_rate_pct','max_drawdown_pct','trades'):
        value = re.search(rf'<strong[^>]+data-dynamic-stat="{key}"[^>]*>(.*?)</strong>',html,re.S).group(1)
        expected = str(stats[key]) if key=='trades' else f'{stats[key]:.2f}'
        assert expected in value
    risk = client.get(f'/api/evidence/{slug}/risk-series?period={period}')
    assert risk.status_code == 200
    assert risk.json()['streaks']['max_win_streak'] == stats['max_win_streak']
    assert risk.json()['streaks']['max_loss_streak'] == stats['max_loss_streak']
    assert risk.json()['rolling_sharpe']
    assert stats['max_drawdown_pct'] >= stats['max_closed_balance_drawdown_pct']


@pytest.mark.parametrize('slug', PROFILES)
def test_only_two_recent_periods_are_published(slug):
    for period in ('3y','5y'):
        response=client.get(f'/eas/{slug}?period={period}',follow_redirects=False)
        assert response.status_code == 302 and response.headers['location']==f'/eas/{slug}?period=1y'
        assert client.get(f'/api/evidence/{slug}/series?period={period}').status_code==422
        assert client.get(f'/api/evidence/{slug}/risk-series?period={period}').status_code==422
        assert client.get(f'/api/evidence/{slug}/cached-trades/{period}/1/chart').status_code==404
        assert load_product_cache(slug,'standard',period) is None
        assert f'/eas/{slug}?' not in client.get(f'/eas?period={period}').text
    for period in ('6m','1y'):
        assert f'/eas/{slug}?period={period}' in client.get(f'/eas?period={period}').text
    assert client.get(f'/api/evidence/{slug}/series?mode=dynamic').status_code==409


@pytest.mark.parametrize('slug', PROFILES)
def test_stale_source_binding_fails_closed(slug):
    data=load_product_summary(slug,'standard','1y')
    assert data and verified_cache(slug,'standard','1y',data)
    bad=deepcopy(data)
    bad['source_fingerprint']['expert_sha256']='stale'
    assert verified_cache(slug,'standard','1y',bad) is None
    bad=deepcopy(data)
    bad['source_fingerprint']['cached_trades_sha256']='stale'
    assert verified_cache(slug,'standard','1y',bad) is None


def test_all_four_recent_native_receipts_are_retained():
    release=json.loads((PACKAGE_ROOT/'Indices Hourly EA Pipeline 2026-10-03/WEBSITE-RELEASE.json').read_text())
    assert len(release['products'])==4
    for row in release['products']:
        summary=load_product_summary(row['slug'],'standard',row['period'])
        assert summary['stats']==row['stats']
        assert summary['source_fingerprint']==row['source_fingerprint']
        assert summary['evidence_status']=='Research evidence'
