from collections import Counter
import hashlib
import json

import pytest
from fastapi.testclient import TestClient
from app.catalog import get_website_catalog
from app.ea_review import SELECTION, SNAPSHOT, review_data
from app.main import app

client=TestClient(app)

def test_reviewed_launcher_and_website_share_roster_and_identity():
    d=review_data(); manifest=json.loads(SELECTION.read_text())
    assert d['total']==37 and d['counts']=={'live':25,'paused':6,'review':6}
    assert set(d['by_slug'])=={p.slug for p in get_website_catalog()}
    assert json.loads(SNAPSHOT.read_text())['selection_sha256']==hashlib.sha256(SELECTION.read_bytes()).hexdigest()
    assert {r['slug'] for r in d['rows'] if r['phase']=='live'}=={e['slug'] for e in manifest['entries'] if e['phase']=='live'}
    for slug in ('dmc-current-xau','dmc-fresh-reaction-xau','dmc-fresh-reaction-us100','gold-overnight-value-area','news-pulse-xau','news-pulse-xag','news-pulse-btc','news-pulse-eurusd','gold-news-v9-direction','us30-hourly-profiles','us100-hourly-profiles'):
        assert d['by_slug'][slug]['phase']=='live'

@pytest.mark.parametrize('phase,n',[('all',37),('live',25),('paused',6),('review',6)])
def test_server_filters_are_consistent(phase,n):
    result=client.get(f'/ea-review?phase={phase}')
    assert result.status_code==200
    assert result.text.count('data-review-phase=')==n
    assert 'not a statistical validation pass' in result.text
    page=client.get(f'/eas?period=1y&phase={phase}')
    assert page.status_code==200
    assert page.text.count('class="product-card group"')==n

def test_search_missing_evidence_and_unqualified_candidate_remain_explicit():
    page=client.get('/ea-review?q=News')
    assert page.text.count('data-review-phase=')==5
    assert 'Current-version evidence not available' in page.text
    assert 'robustness screen failed' in client.get('/ea-review?q=Trend').text
    assert 'These normal-preset card results are not that candidate' in client.get('/eas?phase=live&period=1y&q=Trend').text
    assert client.get('/ea-review?phase=bogus').status_code==422
    assert client.get('/eas?phase=bogus').status_code==422
    assert Counter(r['phase'] for r in client.get('/api/ea-review').json()['rows'])=={'live':25,'paused':6,'review':6}
    for slug in ('us30-hourly-profiles','us100-hourly-profiles'):
        row=review_data()['by_slug'][slug]
        assert 'no SL' in row['variant'] and 'not the history-sized' in row['next_review']

def test_snapshot_staleness_fails_closed(tmp_path,monkeypatch):
    import app.ea_review as module
    bad=json.loads(SNAPSHOT.read_text());bad['selection_sha256']='stale'
    path=tmp_path/'snapshot.json';path.write_text(json.dumps(bad))
    monkeypatch.setattr(module,'SNAPSHOT',path);review_data.cache_clear()
    try:
        with pytest.raises(ValueError,match='stale'): review_data()
    finally: review_data.cache_clear()
