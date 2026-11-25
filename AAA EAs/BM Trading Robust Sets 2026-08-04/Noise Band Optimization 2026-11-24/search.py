"""Stage 5 staged search (PLAN.md). uv run --with numba python search.py search | finalize
search  : stages 1-10 on DEVELOPMENT only (combined USTEC + US500, shared setting), top 3 carried, every config -> SEARCH_RESULTS.json
finalize: plateau check, walk-forward (pre-OOS), validation pick, then OOS once -> FINAL.json"""
import json, math, sys, time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
H = Path(__file__).resolve().parent; sys.path.insert(0, str(H)); sys.path.insert(0, str(H.parent.parent / 'Calyx Research Pipeline'))
import engine as E  # noqa: E402
import robustness  # noqa: E402
COMM = {'USTEC': 0.625 + 0.44, 'US500': 0.25 + 0.13}
SYMS = ('USTEC', 'US500')
DEV = ('2019-07-16', '2023-11-21'); VAL = ('2023-11-21', '2024-11-21'); OOS = ('2024-11-21', '2026-11-21'); ALL = ('2019-07-16', '2026-11-21')
BASE = dict(tf=30, band=0, k=1.4, first_min=30, last_off=330, confirm=1, stop_mode=0, stop_mult=2.0, be=0.0, trail=2.0, trail_start=1.0, target=0.0, time_h=0.0, flat=0,
            direction='both', trend=False, vol='any', dow='none', max_trades=1)
ORDERED = dict(tf=[15, 30, 60], k=[0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.4], stop_mult=[0.75, 1.0, 1.5, 2.0, 2.5, 3.0], trail=[0.0, 1.0, 1.5, 2.0, 3.0],
               trail_start=[0.5, 1.0, 1.5, 2.0], be=[0.0, 0.5, 1.0], target=[0.0, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0], time_h=[0.0, 2.0, 4.0],
               first_min=[30, 60], last_off=[90, 150, 210, 330], flat=[1, 0])
SIGMA_K = [0.8, 1.0, 1.2, 1.5]
_DATA = {}


def data(sym, tf):
    if (sym, tf) not in _DATA: _DATA[(sym, tf)] = E.Data(sym, tf, COMM[sym])
    return _DATA[(sym, tf)]


def key(c): return json.dumps({k: c[k] for k in sorted(c)}, sort_keys=True)


_LEDGER = {}


def ledger(c):
    """combined ledger: list of (date, epoch, sym, r)."""
    k = key(c)
    if k not in _LEDGER:
        rows = []
        for s in SYMS:
            D = data(s, c['tf']); tr = E.run(D, {x: v for x, v in c.items() if x != 'tf'})
            for r in tr: rows.append((D.DATE[int(r[0])], int(D.t[int(r[4])]), s, float(r[3])))
        rows.sort(key=lambda x: x[1]); _LEDGER[k] = rows
    return _LEDGER[k]


def stats(rows, w, sym=None):
    x = [r[3] for r in rows if w[0] <= r[0] < w[1] and (sym is None or r[2] == sym)]
    if not x: return dict(n=0, R=0.0, PF=None, DD=None, RDD=None, win=None)
    g = sum(v for v in x if v > 0); l = -sum(v for v in x if v < 0); eq = pk = dd = 0.0
    for v in x: eq += v; pk = max(pk, eq); dd = max(dd, pk - eq)
    m = (datetime.fromisoformat(w[1]) - datetime.fromisoformat(w[0])).days / 30.4375
    return dict(n=len(x), per_month=round(len(x) / m, 1), R=round(sum(x), 2), PF=round(g / l, 3) if l else None, DD=round(dd, 2), RDD=round(sum(x) / max(dd, 1.0), 3),
                win=round(100 * sum(v > 0 for v in x) / len(x), 1), avgR=round(sum(x) / len(x), 4))


def dev_eval(c):
    rows = ledger(c); a = stats(rows, DEV); a['USTEC_n'] = stats(rows, DEV, 'USTEC')['n']; a['US500_n'] = stats(rows, DEV, 'US500')['n']
    a['eligible'] = a['n'] >= 300 and a['USTEC_n'] >= 100 and a['US500_n'] >= 100
    return a


TRIED = {}


def evaluate(cands, stage):
    out = []
    for c in cands:
        k = key(c)
        if k not in TRIED: TRIED[k] = dict(cfg=c, stage=stage, dev=dev_eval(c))
        out.append(TRIED[k])
    return out


def top3(results):
    el = [r for r in results if r['dev']['eligible'] and r['dev']['PF'] is not None]
    if not el: return []
    pf = sorted(el, key=lambda r: -r['dev']['PF']); rd = sorted(el, key=lambda r: -r['dev']['RDD'])
    rank = {key(r['cfg']): (pf.index(r) + rd.index(r)) / 2 for r in el}
    uniq = []; seen = set()
    for r in sorted(el, key=lambda r: (rank[key(r['cfg'])], -r['dev']['PF'])):
        if key(r['cfg']) in seen: continue
        seen.add(key(r['cfg'])); uniq.append(r)
    return uniq[:3]


def vary(cs, **opts):
    out = []
    for c in cs:
        for combo in opts['grid'](c): out.append(dict(c, **combo))
    return out


def search():
    t0 = time.time(); log = {}
    stages = [
        ('1 timeframe', lambda c: [dict(tf=v) for v in ORDERED['tf']]),
        ('2 band', lambda c: [dict(band=0, k=v) for v in ORDERED['k']] + [dict(band=1, k=v) for v in SIGMA_K]),
        ('3 confirmation', lambda c: [dict(confirm=v) for v in (1, 2)]),
        ('4 initial stop', lambda c: [dict(stop_mode=0, stop_mult=v) for v in ORDERED['stop_mult']] + [dict(stop_mode=1, stop_mult=c['stop_mult'])]),
        ('5 stop management', lambda c: [dict(trail=0.0, be=0.0)] + [dict(trail=0.0, be=v) for v in (0.5, 1.0)] +
                                        [dict(trail=t, trail_start=s, be=0.0) for t in (1.0, 1.5, 2.0, 3.0) for s in ORDERED['trail_start']]),
        ('6 target / exit', lambda c: [dict(target=v, time_h=0.0) for v in ORDERED['target']] + [dict(target=0.0, time_h=v) for v in (2.0, 4.0)]),
        ('7 session', lambda c: [dict(first_min=f, last_off=l, flat=fl) for f in (30, 60) for l in (90, 150, 210, 330) for fl in (0, 1) if not (fl == 1 and l > 300)]),
        ('8 direction', lambda c: [dict(direction=v) for v in ('both', 'long', 'short')]),
        ('9 filters', lambda c: [dict(trend=t, vol=v, dow=d) for t in (False, True) for v in ('any', 'high', 'low') for d in ('none', 'mon', 'fri')]),
        ('10 management', lambda c: [dict(max_trades=v) for v in (1, 2)]),
    ]
    carry = [dict(BASE)]; evaluate(carry, '0 raw WIDE')
    for name, grid in stages:
        res = evaluate(vary(carry, grid=grid), name); best = top3(res)
        if not best: print('NO ELIGIBLE at', name); break
        carry = [b['cfg'] for b in best]
        log[name] = [dict(cfg=b['cfg'], dev=b['dev']) for b in best]
        print(f"{name:20s} tried {len(res):3d} | " + ' | '.join(f"PF {b['dev']['PF']} R {b['dev']['R']} DD {b['dev']['DD']} n {b['dev']['n']}" for b in best), f"({time.time() - t0:.0f}s)", flush=True)
    json.dump(dict(configs_tried=len(TRIED), stages=log, all=list(TRIED.values())), open(H / 'SEARCH_RESULTS.json', 'w'), indent=1)
    print('CONFIGS TRIED', len(TRIED))


def neighbours(c):
    out = []
    for dim, vals in ORDERED.items():
        if dim not in c or c[dim] not in vals: continue
        i = vals.index(c[dim])
        for j in (i - 1, i + 1):
            if 0 <= j < len(vals): out.append(dict(c, **{dim: vals[j]}))
    if c['band'] == 1:
        out = [n for n in out if 'k' not in n or n['k'] in SIGMA_K or n['k'] == c['k']]
        i = SIGMA_K.index(c['k']); out += [dict(c, k=SIGMA_K[j]) for j in (i - 1, i + 1) if 0 <= j < len(SIGMA_K)]
    for dim in ('confirm', 'max_trades'):
        out.append(dict(c, **{dim: {1: 2, 2: 1}[c[dim]]}))
    out.append(dict(c, trend=not c['trend']))
    return [n for n in out if key(n) != key(c)]


def finalize():
    S = json.load(open(H / 'SEARCH_RESULTS.json')); last = list(S['stages'])[-1]; fin = [x['cfg'] for x in S['stages'][last]]
    for r in S['all']: TRIED[key(r['cfg'])] = r
    out = dict(configs_tried_search=S['configs_tried'], finalists=[])
    # plateau
    for c in fin:
        nb = neighbours(c); ev = evaluate(nb, 'plateau'); prof = [e for e in ev if e['dev']['R'] > 0]
        pfs = sorted(e['dev']['PF'] or 0 for e in ev); med = pfs[len(pfs) // 2] if pfs else 0
        ok = len(prof) / max(1, len(ev)) >= 0.70 and med >= 1.05
        out['finalists'].append(dict(cfg=c, dev=dev_eval(c), plateau=dict(neighbours=len(ev), profitable_pct=round(100 * len(prof) / max(1, len(ev)), 1), median_pf=med, PASS=ok,
                                                                           worst=[dict(changed={k: e['cfg'][k] for k in e['cfg'] if e['cfg'][k] != c[k]}, R=e['dev']['R'], PF=e['dev']['PF']) for e in sorted(ev, key=lambda e: e['dev']['R'])[:4]])))
    # walk-forward inside pre-OOS (dev + val), all tried configs, ledgers per config
    t0 = int(datetime(2019, 7, 16, tzinfo=timezone.utc).timestamp()); t1 = int(datetime(2024, 11, 21, tzinfo=timezone.utc).timestamp())
    led = {key(r['cfg']): [(e, rr) for d, e, s, rr in ledger(r['cfg']) if t0 <= e < t1] for r in TRIED.values()}
    nbm = {key(r['cfg']): [key(n) for n in neighbours(r['cfg']) if key(n) in led] for r in TRIED.values()}
    wf = robustness.walk_forward(led, nbm, robustness.rolling_folds(t0, t1), min_trades=30, blind_runs=2000)
    for f in wf['folds']: f['choice'] = json.loads(f['choice']) if f['choice'] else None
    out['walk_forward'] = wf
    # validation pick
    for f in out['finalists']: f['val'] = stats(ledger(f['cfg']), VAL)
    ok = [f for f in out['finalists'] if f['plateau']['PASS'] and f['val']['R'] > 0 and (f['val']['PF'] or 0) >= 1.10]
    out['configs_tried_total'] = len(TRIED)
    if not ok:
        out['verdict'] = 'REJECTED_AT_VALIDATION'; out['pick'] = None
    else:
        pick = max(ok, key=lambda f: f['val']['RDD']); out['pick'] = pick['cfg']
        rows = ledger(pick['cfg']); o = stats(rows, OOS)
        out['oos'] = o; out['verdict'] = 'OOS_PASS' if o['R'] > 0 and (o['PF'] or 0) >= 1.10 else 'REJECTED_AT_OOS'
    raw = ledger(BASE)
    out['raw_WIDE'] = {w: stats(raw, v) for w, v in dict(dev=DEV, val=VAL, oos=OOS, all=ALL).items()}
    json.dump(out, open(H / 'FINAL.json', 'w'), indent=1, default=str)
    print(json.dumps({k: v for k, v in out.items() if k != 'walk_forward'}, indent=1, default=str)[:6000]); print('WF', json.dumps(wf['chained']), json.dumps(wf['blind']), wf['verdict'])


if __name__ == '__main__':
    {'search': search, 'finalize': finalize}[sys.argv[1]]()
