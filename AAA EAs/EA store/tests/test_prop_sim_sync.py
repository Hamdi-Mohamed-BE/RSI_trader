"""Website roster + live package defaults must never silently drift apart."""
import json

import pytest
from fastapi.testclient import TestClient

from app.catalog import PACKAGE_ROOT, get_website_catalog
from app.main import app, _prop_limiter
from app.prop_sim import service
from app.prop_sim.ledger import load_ea, hourly_reference

client = TestClient(app)
HOURLIES = ('us30-hourly-profiles', 'us100-hourly-profiles')


def test_simulator_lists_entire_website_catalog_with_missing_evidence_explicit():
    payload = client.get('/api/prop-sim/catalog').json()
    assert {p['slug'] for p in payload['eas']} == {p.slug for p in get_website_catalog()}
    assert len(payload['eas']) == payload['catalog_count'] == len(get_website_catalog())
    assert set(HOURLIES) <= {p['slug'] for p in payload['eas']}
    for row in payload['eas']:
        if not row['supported_periods']:
            assert payload['compatibility']['ftmo-2step-swing'][row['slug']]['status'] == 'blocked'
            assert row['risk_basis'] == 'unavailable'


def test_default_selection_follows_actual_ftmo_package_not_old_suggestions():
    package = json.loads(service.FTMO_PACKAGE.read_text(encoding='utf-8'))
    payload = service.catalog_payload()
    assert payload['default_preset_id'] == 'ftmo-current'
    preset = next(p for p in payload['presets'] if p['id'] == payload['default_preset_id'])
    assert preset['package_version'] == package['version']
    assert {e['slug'] for e in preset['eas']} == {e['slug'] for e in package['entries']}
    assert {e['slug'] for e in payload['eas'] if e['ftmo_profile_member']} == {e['slug'] for e in package['entries']}
    assert preset['period'] == '1y' and preset['sizing'] == 'fixed_usd'
    assert all(e['risk_usd'] == package['risk_usd'] for e in preset['eas'])
    assert not set(HOURLIES) & {e['slug'] for e in preset['eas']}
    assert not any(p['id'] in ('ftmo13', 'ftmo13-controls') for p in payload['presets'])


def test_ftmo_squeeze_uses_standard_not_stale_safe_ledger():
    assert service.ftmo_mode('xau-squeeze-momentum-standard') == 'standard'
    row = next(p for p in service.catalog_payload()['eas'] if p['slug'] == 'xau-squeeze-momentum-standard')
    assert row['mode'] == 'standard'


@pytest.mark.parametrize('slug', HOURLIES)
def test_hourly_reference_is_verified_and_not_invented_stop_r(slug):
    profile, trades = load_ea(slug, '1y')
    assert profile.risk_basis == 'historical_loss_reference'
    assert len(trades) > 100
    reference = hourly_reference(slug)
    expected = 611.53 if slug == HOURLIES[0] else 358.71
    assert reference == pytest.approx(expected)
    assert trades[0].risk_cash == pytest.approx(reference * trades[0].volume)
    assert 'NOT planned-stop R' in profile.risk_note
    assert load_ea(slug, '3y') is None and load_ea(slug, '5y') is None
    assert load_ea(slug, '6m') is not None
    payload = service.catalog_payload()
    row = next(p for p in payload['eas'] if p['slug'] == slug)
    assert row['supported_periods'] == ['1y', '6m']
    assert payload['compatibility']['ftmo-2step-swing'][slug]['status'] == 'adjusted'


@pytest.mark.parametrize('period', ('1y', '6m'))
def test_hourlies_replay_both_recent_windows_with_prominent_unbounded_risk_notice(period):
    _prop_limiter._hits.clear()
    body = dict(programme_id='ftmo-2step-swing', account_size=10000, period=period, paths=100,
                eas=[dict(slug=slug, risk_pct=0.5) for slug in HOURLIES])
    response = client.post('/api/prop-sim/run', json=body)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result['historical_risk_experiment'] is True
    assert result['stats']['trades'] > 500
    assert 'NO-STOP EXPERIMENT' in result['notice']
    assert any('without bound' in a for a in result['assumptions'])
    assert any('minimum-lot override' in a for a in result['assumptions'])


def test_long_window_is_rejected_not_silently_replaced_by_one_year():
    _prop_limiter._hits.clear()
    response = client.post('/api/prop-sim/run', json=dict(programme_id='ftmo-2step-swing', account_size=10000,
        period='3y', paths=100, eas=[dict(slug=HOURLIES[0], risk_pct=0.5)]))
    assert response.status_code == 422 and 'No cached 3y' in response.json()['detail']


def test_current_default_replay_is_available_but_not_claimed_native_guard_validation():
    preset = service.current_ftmo_preset()
    request = service.SimRequest(programme_id=preset['programme_id'], account_size=preset['account_size'],
        eas=preset['eas'], period=preset['period'], paths=100, **preset['guards'])
    result = service.run_simulation(request)
    assert len(result['eas']) == len(preset['eas']) and result['stats']['trades'] > 100
    assert not result['historical_risk_experiment']
    assert 'not an exact replay' in result['notice']


def test_future_package_edits_refresh_selection_and_cache_keys(tmp_path, monkeypatch):
    path = tmp_path / 'PACKAGE.json'
    path.write_text(json.dumps(dict(entries=[dict(slug='ema3')], version='test-one', reference_balance=10000, risk_usd=50)))
    monkeypatch.setattr(service, 'FTMO_PACKAGE', path)
    first = service._data_stamp()
    assert service.catalog_payload()['presets'][0]['eas'][0]['slug'] == 'ema3'
    path.write_text(json.dumps(dict(entries=[dict(slug='xau-rsi-vwap')], version='test-two', reference_balance=10000, risk_usd=25)))
    assert service._data_stamp() != first
    preset = service.catalog_payload()['presets'][0]
    assert preset['eas'][0]['slug'] == 'xau-rsi-vwap' and preset['eas'][0]['risk_usd'] == 25


def test_hourly_risk_reference_fails_closed_on_changed_bound_ledger(tmp_path, monkeypatch):
    from app.prop_sim import ledger
    release = json.loads((PACKAGE_ROOT / 'Hourly Profiles Deployment 2026-10-04/RELEASE.json').read_text())
    root = tmp_path / 'products' / HOURLIES[0] / 'standard'
    root.mkdir(parents=True)
    for filename in release['entries'][0]['ledger_sha256']:
        (root / filename).write_text('[]')
    monkeypatch.setattr(ledger, 'CACHE_ROOT', tmp_path)
    assert ledger.hourly_reference(HOURLIES[0]) is None


def test_page_and_client_use_versioned_catalog_defaults_and_reference_disclosure():
    page = client.get('/prop-simulator').text
    script = client.get('/static/prop-simulator.js').text
    assert '20261004-sync-1' in page
    assert 'data-selection-info' in page and 'data-result-notice' in page
    assert 'default_preset_id' in script and "p.id === 'ftmo13-controls'" not in script
    assert 'NO-STOP EXPERIMENT' in script and 'real answer lies between' not in page
