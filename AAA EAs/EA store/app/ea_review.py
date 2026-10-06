"""Owner deployment phase, deliberately separate from statistical evidence status."""
import hashlib
import json
from collections import Counter
from functools import lru_cache

from .catalog import PACKAGE_ROOT, STORE_ROOT

PHASE_LABELS = {'all':'All EAs', 'live':'Passed to live trading phase', 'paused':'Pause live / demo only', 'review':'Deeper review'}
SELECTION = PACKAGE_ROOT / 'Reviewed EA Deployment 2026-10-06' / 'selection.json'
SNAPSHOT = STORE_ROOT / 'data' / 'ea-review.json'

@lru_cache(maxsize=1)
def review_data():
    manifest=json.loads(SELECTION.read_text(encoding='utf-8'))
    snapshot=json.loads(SNAPSHOT.read_text(encoding='utf-8'))
    if snapshot['selection_sha256'] != hashlib.sha256(SELECTION.read_bytes()).hexdigest():
        raise ValueError('Reviewed website snapshot is stale; rebuild it from the shared roster')
    entries={r['slug']:r for r in manifest['entries']}
    rows=snapshot['rows']
    if len(rows) != 37 or len(entries) != 37 or {r['slug'] for r in rows} != set(entries):
        raise ValueError('Reviewed website / launcher inventory mismatch')
    for row in rows:
        if row['phase'] not in ('live','paused','review') or row['phase'] != entries[row['slug']]['phase']:
            raise ValueError('Reviewed website / launcher phase mismatch')
        row['phase_label']=PHASE_LABELS[row['phase']]
    counts=dict(Counter(r['phase'] for r in rows))
    if counts != manifest['expected_counts']:
        raise ValueError('Reviewed phase counts disagree with launcher')
    return dict(version=snapshot['version'], scope=snapshot['scope'], rows=rows, counts=counts, total=len(rows), by_slug={r['slug']:r for r in rows})

def phase_links(request):
    from urllib.parse import urlencode
    params=dict(request.query_params)
    return {phase:request.url.path+'?'+urlencode(params | {'phase':phase}) for phase in PHASE_LABELS}
