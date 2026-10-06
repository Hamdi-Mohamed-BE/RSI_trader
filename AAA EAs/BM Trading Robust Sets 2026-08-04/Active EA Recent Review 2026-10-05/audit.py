"""Read-only cached evidence review. Does not contact or configure MT5."""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
STORE = BASE.parent / 'EA store'
CACHE = STORE / 'data/evidence-cache/v1/products'
os.environ['EA_STORE_DISABLE_MT5'] = '1'
sys.path.insert(0, str(STORE))
from app.catalog import get_catalog, parse_installer_items
from app.news_evidence import load_news_summary

START = datetime(2026, 7, 5)
END = datetime(2026, 10, 5)


def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))


def dt(v):
    if isinstance(v, (int, float)):
        return datetime.fromtimestamp(v, timezone.utc).replace(tzinfo=None)
    value = str(v).replace('Z', '+00:00')
    value = value[:10].replace('.', '-') + value[10:]
    return datetime.fromisoformat(value).replace(tzinfo=None)


def norm(t):
    return dict(open=dt(t.get('open_time') or float(t['open_epoch'])),
                close=dt(t.get('close_time') or float(t['close_epoch'])),
                net=float(t.get('net_profit', t.get('net', 0))),
                position_id=t.get('position_id'),
                side=t.get('side'), open_price=t.get('open_price'),
                comment=t.get('entry_comment', t.get('module', '')))


def whole(legs):
    buckets = defaultdict(list)
    for x in legs:
        t = norm(x)
        key = ('id', t['position_id']) if t['position_id'] is not None else (
            'inferred', t['open'], t['side'], t['open_price'], t['comment'])
        buckets[key].append(t)
    positions = [dict(open=min(x['open'] for x in v), close=max(x['close'] for x in v),
                      net=sum(x['net'] for x in v), legs=len(v)) for v in buckets.values()]
    return sorted(positions, key=lambda x: (x['close'], x['open']))


def metrics(ts, initial=10000):
    wins = [x['net'] for x in ts if x['net'] > 0.005]
    losses = [x['net'] for x in ts if x['net'] < -0.005]
    cw = cl = mw = ml = 0
    for t in ts:
        if t['net'] > 0.005:
            cw += 1; cl = 0; mw = max(mw, cw)
        elif t['net'] < -0.005:
            cl += 1; cw = 0; ml = max(ml, cl)
        else:
            cw = cl = 0
    net = sum(x['net'] for x in ts)
    return dict(trades=len(ts), net=net, return_pct=net / initial * 100 if initial > 0 else None,
                pf=sum(wins) / -sum(losses) if losses else (None if not wins else 'no losses'),
                win_rate=100 * len(wins) / len(ts) if ts else None,
                wins=len(wins), losses=len(losses), flats=len(ts)-len(wins)-len(losses),
                win_streak=mw, loss_streak=ml,
                avg_win=sum(wins)/len(wins) if wins else None,
                avg_loss=sum(losses)/len(losses) if losses else None)


def add_evidence(row, legs, source, stats, start, end_exclusive, grouping='exact'):
    ts = whole(legs)
    initial = stats.get('initial_balance', 10000)
    row['year'] = metrics(ts, initial)
    row['year']['equity_dd_pct'] = stats.get('native_equity_drawdown_pct', stats.get('equity_dd_pct', stats.get('max_drawdown_pct')))
    row['year']['start'] = str(start)[:10].replace('.', '-')
    row['year']['end_exclusive'] = str(end_exclusive)[:10].replace('.', '-')
    limit = min(END, dt(end_exclusive))
    before = sum(x['net'] for x in ts if x['close'] < START)
    recent = [x for x in ts if START <= x['close'] < limit]
    row['recent'] = metrics(recent, initial + before)
    row['recent'].update(start=START.date().isoformat(), end_exclusive=limit.date().isoformat(),
                         return_method='closed-position slice / closed balance at July 5; not a fresh-account backtest')
    row['source'] = str(source)
    row['source_sha256'] = hashlib.sha256(Path(source).read_bytes()).hexdigest()
    row['grouping'] = grouping
    row['ledger_exit_legs'] = len(legs)
    row['partial_groups'] = sum(x['legs'] > 1 for x in ts)
    row['cash_reconciliation_difference'] = row['year']['net'] - stats.get('net_profit', row['year']['net'])


def build():
    products = get_catalog()
    assert len(products) == 37
    assert len(parse_installer_items()) == 37
    rows = []
    for p in products:
        mode = 'dynamic' if p.recommended_dynamic_mode else ('safe' if p.recommended_safe_mode else 'standard')
        r = dict(slug=p.slug, label=p.label, mode=mode, canonical=p.canonical,
                 set_source=p.dynamic_set_source if mode == 'dynamic' else (p.safe_set_source if mode == 'safe' else p.set_source),
                 limitations=p.limitations, risk_note=p.risk_note, status=None,
                 evidence_notes=[e.model_dump(mode='json') for e in [p.evidence, p.safe_evidence, p.dynamic_evidence, p.one_year_evidence] if e])
        if p.slug.startswith('news-pulse-'):
            r.update(year=None, recent=None, source=None, current_news_evidence_available=load_news_summary(p.slug, '1y') is not None,
                     provenance='Current Oct 3 placement release requires matching replay; old event-optimised caches intentionally excluded')
        else:
            folder = CACHE / p.slug / mode
            path = folder / '1y.json'
            lp = folder / '1y.trades.json'
            if path.exists() and lp.exists():
                payload = read(path)
                meta_path = STORE / 'data/evidence-cache/v1/source-runs' / p.slug / mode / '1y.meta.json'
                meta = read(meta_path) if meta_path.exists() else {}
                end_exclusive = meta.get('to') or (dt(payload['available_to']) + timedelta(days=1)).date().isoformat()
                start = meta.get('from', payload['available_from'])
                add_evidence(r, read(lp), lp, payload['stats'], start, end_exclusive, 'entry-key grouping; inferred where no position ID')
                r['history_quality'] = payload.get('history_quality')
                r['fingerprint'] = payload.get('source_fingerprint')
                r['cache_stats'] = payload['stats']
                r['date_provenance'] = 'native source-run From/To (To exclusive)' if meta else 'cache reported dates; assumed inclusive available_to'
                r['cache_payload_path'] = str(path)
                r['cache_payload_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
            else:
                r.update(year=None, recent=None, source=None)
        if p.slug == 'lta-volume-profile':
            path = BASE / 'LTA VWAP Developing POC Comparison 2026-10-05/native/SAFE_M15/results.json'
            q = read(path)
            add_evidence(r, q['trades'], path, q['native'], q['window'][0], q['window'][1])
            r['year']['equity_dd_pct'] = q['native']['equity_dd_pct']
            r['history_quality'] = q['native']['history_quality']
            r['provenance'] = 'Fresh Oct 5 native replay of current Safe M15 rules; not the experimental M5 flow'
        if p.slug == 'nasdaq-5m-candle-momentum':
            path = BASE / 'Nasdaq 5M Next Day Efficiency ML 2026-10-05/SUMMARY.json'
            q = next(x for x in read(path)['comparison'] if x['version'] == 'BASE' and x['window'] == '3M')
            r['recent'] = dict(trades=q['trades'], return_pct=q['return_pct'], net=q['net_profit'], pf=q['net_pf'],
                               win_rate=q['win_rate_pct'], win_streak=q['max_win_streak'], loss_streak=q['max_loss_streak'],
                               equity_dd_pct=q['equity_dd_pct'], start=q['start'].replace('.', '-'),
                               end_exclusive=q['end_exclusive'].replace('.', '-'), return_method='fresh native 3M backtest',
                               source=str(path), sharpe_daily_equity=q['daily_equity_sharpe'])
            r['provenance'] = 'Latest DI-on wide-stop ATR-trail BASE; no experimental ML gate'
        if p.slug == '3-way-gold':
            root = BASE / 'QuantLab Gold Trio Pipeline 2026-09-30/native/combo-best-3-ABC-recent'
            q = read(root / 'results.json')[0]
            with gzip.open(root / '0-trades.csv.gz', 'rt', encoding='utf-8') as f:
                legs = list(csv.DictReader(f))
            add_evidence(r, legs, root / '0-trades.csv.gz', dict(q['net'], initial_balance=10000), q['start'], q['end'])
            r['year']['equity_dd_pct'] = q['net']['equity_dd_pct']
            r['history_quality'] = 'Mixed real/generated ticks; real history begins January 2026'
            r['provenance'] = 'BEST trio exact whole positions; live installer variant/clock may differ. Older untouched holdout PF 0.74 / -20.3%, WATCH_ONLY'
        rows.append(r)
    return rows


if __name__ == '__main__':
    rows = build()
    (HERE / 'evidence.json').write_text(json.dumps(rows, indent=2, default=str), encoding='utf-8')
    for r in rows:
        a, q = r['year'], r['recent']
        def s(x):
            if not x: return 'UNVERIFIED'
            return f"n={x['trades']} PF={x['pf']} WR={x['win_rate']} return={x['return_pct']:+.2f}% W/L={x['win_streak']}/{x['loss_streak']}"
        print(r['slug'], r['mode'], '| YEAR', s(a), '| JUL5+', s(q), '| groups', r.get('partial_groups'), '| cashdiff', r.get('cash_reconciliation_difference'))
