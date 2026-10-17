"""Freeze CPI-only official-source chronology and all cases before replay."""
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import hashlib, json, re

R = Path(__file__).resolve().parent
B = R.parent

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def persist_same(p, obj):
    if p.exists():
        assert json.loads(p.read_text(encoding='utf-8')) == obj, f'Frozen object changed: {p.name}'
    else:
        p.write_text(json.dumps(obj, indent=2, allow_nan=False), encoding='utf-8')

def main():
    ny = ZoneInfo('America/New_York')
    source = B / 'US100 News Reversion Pipeline 2020-2024 2026-10-08/calendar.json'
    receipts = B / 'News Pulse Full Coverage 2026-09-12/bls-source-receipts.json'
    events = {e['epoch']: e for e in json.loads(source.read_text())['events'] if e['kind'] == 'CPI'}
    for row in json.loads(receipts.read_text()):
        m = re.search(r'([A-Za-z]+,\s+[A-Za-z]+\s+\d{1,2},\s+\d{4})\s+(\d{2}:\d{2}\s+[AP]M)\s+Consumer Price Index for', row['line'])
        if not m:
            continue
        local = datetime.strptime(m[1] + ' ' + m[2], '%A, %B %d, %Y %I:%M %p').replace(tzinfo=ny)
        utc = local.astimezone(timezone.utc)
        epoch = int(utc.timestamp())
        events[epoch] = dict(kind='CPI', epoch=epoch, release_utc=utc.isoformat(), release_ny=local.isoformat(), source=row['source'], receipt=row['line'])
    cfg = json.loads((R / 'config.json').read_text())
    lo = int(datetime.fromisoformat(cfg['start']).replace(tzinfo=timezone.utc).timestamp())
    hi = int(datetime.fromisoformat(cfg['end_exclusive']).replace(tzinfo=timezone.utc).timestamp())
    selected = sorted([e for t, e in events.items() if lo <= t < hi], key=lambda e: e['epoch'])
    for e in selected:
        local = datetime.fromtimestamp(e['epoch'], timezone.utc).astimezone(ny)
        assert (local.hour, local.minute, local.second) == (8, 30, 0)
    assert len({e['epoch'] for e in selected}) == len(selected)
    assert all(sum(datetime.fromtimestamp(e['epoch'], timezone.utc).year == year for e in selected) == 12 for year in range(2020, 2025))
    calendar = dict(events=selected, sources={str(p.relative_to(B)): sha(p) for p in [source, receipts]},
                    calendar_vintage_verified=False, consensus_used=False,
                    note='Official-source documented scheduled dates, not a point-in-time vintage consensus archive; no assumed monthly release rule. 2025 missing release is not manufactured.')
    persist_same(R / 'calendar.json', calendar)
    cases = [dict(mode=mode, require_positive_spread=policy) for policy in [0, 1] for mode in [0, 1, 2]]
    persist_same(R / 'CASES.json', cases)
    frozen = dict(config_sha256=sha(R / 'config.json'), calendar_sha256=sha(R / 'calendar.json'),
                  cases_sha256=sha(R / 'CASES.json'), engine_sha256=sha(R / 'engine.mq5'), build_sha256=sha(R / 'build_engine.py'),
                  parameters_searched=0, enumerated_cases=len(cases), research_only=True, live_changes=False)
    p = R / 'FROZEN.json'
    if p.exists():
        assert json.loads(p.read_text())['locked'] == frozen
    else:
        p.write_text(json.dumps(dict(locked=frozen, frozen_at_utc=datetime.now(timezone.utc).isoformat()), indent=2), encoding='utf-8')
    print(dict(events=len(selected), first=selected[0]['release_utc'], last=selected[-1]['release_utc'], cases=cases), flush=True)

if __name__ == '__main__':
    main()
