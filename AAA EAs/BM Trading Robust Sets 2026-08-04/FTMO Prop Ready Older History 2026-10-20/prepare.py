"""Build candidate streams for any window from the same native 5-year source runs as FTMO Faster Portfolio Screen 2026-10-16.

Generalisation of that study's prepare.py (same sources, stop-risk reference, mark ownership, costs). No outcomes.
A parity gate rebuilds 2025-10-06..2026-10-06 and must equal the Faster Screen INPUTS for the nine Prop Ready EAs.

python prepare.py
"""
from pathlib import Path
from datetime import datetime, date, timedelta, timezone
from zoneinfo import ZoneInfo
from bisect import bisect_left
from collections import defaultdict
import csv, hashlib, json, math

R = Path(__file__).resolve().parent; B = R.parent; Z = ZoneInfo('Europe/Prague')
LONG = B / 'Portfolio Long History All ORB05 2026-10-14'
FASTER = B / 'FTMO Faster Portfolio Screen 2026-10-16'
SLUGS = ['nasdaq-5m-candle-momentum', 'usdjpy-london-open-momentum', 'us100-month-end-flow', 'xau-rsi-vwap', 'us100-h1-orb-13utc',
         'us100-orb-new-york-m30', 'us100-selective-orb-v3', 'xau-orb-new-york-m30', 'xau-orb-london-ny-overlap-m30']


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def midnight(d): return datetime.combine(d, datetime.min.time(), tzinfo=Z).timestamp()


def load_sources():
    p = read(LONG / 'PLAN.json'); state = read(LONG / 'RUN_STATUS.json')
    lookup = {(x['key'], x['position_id']): x for x in read(LONG / 'RISK_ROWS.json')['ftmo']}
    out, hashes = {}, {str(x): sha(x) for x in (LONG / 'PLAN.json', LONG / 'RUN_STATUS.json', LONG / 'RISK_ROWS.json')}
    for slug in SLUGS:
        cid = p['mappings']['ftmo'][slug]; row = next(x for x in p['cases'] if x['case_id'] == cid); receipt = state['complete'][cid]
        for file, digest in row['production_hashes'].items():
            assert sha(file) == digest, ('Production source changed', file)
        path = Path(receipt['path']); assert sha(path) == receipt['sha256']; case = read(path); folder = path.parent
        for f in (path, folder / 'deals.csv', folder / 'equity.csv', folder / 'manifest.json'):
            hashes[str(f)] = sha(f)
        out[slug] = dict(row=row, case=case, folder=folder)
    return out, lookup, hashes


def candidates(src, lookup, slug, begin, end):
    row, case, folder = src['row'], src['case'], src['folder']
    ds = list(csv.DictReader((folder / 'deals.csv').open(encoding='utf-8-sig')))
    source_trades = sorted(case['trades'], key=lambda t: (t['open_epoch'], t['position_id']))
    assert all(not t['partial'] for t in source_trades)
    assert all(a['close_epoch'] <= b['open_epoch'] for a, b in zip(source_trades, source_trades[1:]))
    opens = [t['open_epoch'] for t in source_trades]; by_pid = defaultdict(list)
    for d in ds: by_pid[int(d['position_id'])].append(d)
    owner_marks = defaultdict(list); boundaries = {int(t[k]) for t in source_trades for k in ('open_epoch', 'close_epoch')}
    previous = None; gfirst = glast = None
    with (folder / 'equity.csv').open(encoding='utf-8-sig') as stream:
        for mark in csv.DictReader(stream):
            epoch = int(mark['epoch']); gfirst = epoch if gfirst is None else gfirst; glast = epoch
            if epoch < begin - 900 or epoch >= end: continue
            assert previous is None or epoch >= previous
            if epoch == previous: continue
            previous = epoch
            balance, equity = float(mark['balance']), float(mark['equity'])
            if epoch in boundaries: continue
            i = bisect_left(opens, epoch) - 1
            if i >= 0 and source_trades[i]['open_epoch'] < epoch < source_trades[i]['close_epoch']:
                t = source_trades[i]; volume = float(t['volume'])
                owner_marks[t['position_id']].append([epoch, (equity - balance) / volume, volume, balance, equity])
            else:
                assert abs(equity - balance) < .021, ('Unowned nonzero floating mark', slug, epoch)
    assert gfirst <= begin and glast >= end, ('Incomplete native coverage', slug)
    contract = {'USTEC': 1., 'XAUUSD': 100., 'USDJPY': 100000.}[row['symbol']]; out = []
    for t in source_trades:
        if not begin <= t['open_epoch'] < end: continue
        boundary = any('end of test' in x.lower() for x in t['exit_comments']); old = lookup.get((slug, t['position_id']))
        if old is None: assert boundary, ('Unmapped ordinary trade', slug, t['position_id'])
        unit_risk = old['unit_risk'] if old else abs(t['open_price'] - t['sl']) * contract / (t['sl'] if row['symbol'] == 'USDJPY' else 1.)
        parts = by_pid[t['position_id']]; opened = [d for d in parts if int(d['entry']) == 0]; assert len(opened) == 1
        entry_unit = sum(float(opened[0][k]) for k in ('gross', 'commission', 'swap', 'fee')) / t['volume']
        out.append(dict(id=slug + '|' + str(t['position_id']), ea=slug, symbol=row['symbol'], position_id=t['position_id'], op=t['open_epoch'],
                        cl=None if boundary else t['close_epoch'], source_forced_close_epoch=t['close_epoch'] if boundary else None, end_censored=boundary,
                        side=t['side'], open_price=t['open_price'], close_price=t['close_price'], sl=t['sl'], tp=t['tp'], unit_risk=unit_risk,
                        source_volume=t['volume'], entry_unit_cost=entry_unit, unit_gross=t['gross'] / t['volume'],
                        unit_commission=(t['commission'] + t['fee']) / t['volume'], unit_swap=t['swap'] / t['volume'], marks=owner_marks[t['position_id']]))
    return out


def starts_for(start_day, end_day):
    out, d = [], start_day
    while d < end_day:
        if d.weekday() < 5 and d + timedelta(days=180) <= end_day:
            out.append(dict(date=d.isoformat(), epoch=midnight(d), horizon_date=(d + timedelta(days=180)).isoformat(), horizon_epoch=midnight(d + timedelta(days=180))))
        d += timedelta(days=1)
    return out


def build(src, lookup, start_day, end_day):
    begin, end = midnight(start_day), midnight(end_day)
    cands = [c for slug in SLUGS for c in candidates(src[slug], lookup, slug, begin, end)]
    return dict(candidates=cands, starts=starts_for(start_day, end_day), year_begin_epoch=begin, year_end_exclusive_epoch=end,
                window=[start_day.isoformat(), end_day.isoformat()])


def main():
    src, lookup, hashes = load_sources()
    # parity gate against the Faster Screen inputs
    ref = read(FASTER / 'INPUTS.json')
    mine = build(src, lookup, date(2025, 10, 6), date(2026, 10, 6))
    for slug in SLUGS:
        a = [x for x in mine['candidates'] if x['ea'] == slug]; b = [x for x in ref['candidates'] if x['ea'] == slug]
        assert a == b, ('Parity failure versus Faster Screen INPUTS', slug, len(a), len(b))
    assert mine['starts'] == ref['starts']
    print('parity PASS: nine EAs identical to the Faster Screen 2025-10-06..2026-10-06 inputs', flush=True)
    older = build(src, lookup, date(2021, 10, 7), date(2025, 10, 6))
    pool5 = build(src, lookup, date(2021, 10, 7), date(2026, 10, 6))
    for name, data in (('INPUTS-older.json', older), ('INPUTS-pool5y.json', pool5)):
        (R / name).write_text(json.dumps(data, separators=(',', ':')), encoding='utf-8')
    (R / 'SOURCES.json').write_text(json.dumps(dict(source_hashes=hashes, parity='PASS', older_candidates=len(older['candidates']), older_starts=len(older['starts']),
                                                     pool5y_candidates=len(pool5['candidates']),
                                                     per_ea={s: dict(older=sum(c['ea'] == s for c in older['candidates']), pool5y=sum(c['ea'] == s for c in pool5['candidates'])) for s in SLUGS}), indent=1), encoding='utf-8')
    print(f"older: {len(older['candidates'])} candidates, {len(older['starts'])} starts; pool5y: {len(pool5['candidates'])} candidates")


if __name__ == '__main__':
    main()
