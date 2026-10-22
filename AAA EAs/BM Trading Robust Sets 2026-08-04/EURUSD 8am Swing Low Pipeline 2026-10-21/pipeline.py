"""EURUSD 8am swing-low pipeline orchestration (PLAN.md). Isolated tester only.

python pipeline.py freeze | parity | search <london|newyork> | plateau <track> | confirm <track> | oos <track>
"""
import gzip, hashlib, json, statistics, sys
from datetime import datetime
from pathlib import Path
import engine as en, runner as rn

R = Path(__file__).resolve().parent; B = R.parent; RAW = B / 'EURUSD 8am Swing Low Raw 2026-10-21'
DEV, VAL, OOS, RAW5 = ('2016-10-17', '2023-10-17'), ('2023-10-17', '2024-10-17'), ('2024-10-17', '2026-10-17'), ('2021-10-17', '2026-10-17')
TRACKS = {'london': 0, 'newyork': 1}
RR = (0.5, 0.75, 1, 1.25, 1.5, 2, 2.5, 3, 4, 5, 6); HOLDS = (1, 2, 3, 4, 6, 8); WINDOWS_W = (1, 2, 4, 6)
ANCHORS = ((7, 0), (7, 30), (8, 0), (8, 30), (9, 0), (9, 30))


def base(track): return dict(en.BASE, clock=TRACKS[track])
def stage_swing(c): return [dict(c, tf=tf, n=n, w=w, ll=ll) for tf in (15, 30, 60) for n in (1, 2, 3) for w in WINDOWS_W for ll in (0, 1)]
def stage_entry(c): return [dict(c, entry=0, entry_k=0), dict(c, entry=1, entry_k=0.25, entry_exp_h=2), dict(c, entry=1, entry_k=0.5, entry_exp_h=2), dict(c, entry=2, entry_k=0, entry_exp_h=2)]
def stage_stop(c): return [dict(c, stop_type=0, stop_val=v, min_stop=0.5) for v in (0, 0.1, 0.25, 0.5)] + [dict(c, stop_type=1, stop_val=v, min_stop=0) for v in (0.5, 1, 1.5, 2, 3)]
def stage_mgmt(c): return ([dict(c, be_r=0, trail_atr=0, trail_start_r=0)] + [dict(c, be_r=b, trail_atr=0, trail_start_r=0) for b in (0.5, 1, 1.5)]
                           + [dict(c, be_r=0, trail_atr=a, trail_start_r=s) for a in (1, 2) for s in (0.5, 1)])
def stage_exit(c): return ([dict(c, tp_r=0, hold_h=hh, exit_mode=0) for hh in HOLDS] + [dict(c, tp_r=0, hold_h=0, exit_mode=1)]
                           + [dict(c, tp_r=r, hold_h=8, exit_mode=0) for r in RR] + [dict(c, tp_r=r, hold_h=0, exit_mode=1) for r in RR])
def stage_anchor(c): return [dict(c, hour=hh, minute=mm) for hh, mm in ANCHORS]
def stage_dir(c): return [dict(c, dir=d) for d in (0, 1, 2)]
def stage_filter(c): return ([dict(c, trend=0, adx_min=0, atr_regime=0, dow=0)] + [dict(c, trend=t) for t in (1, 2, 3)] + [dict(c, adx_min=a) for a in (20, 25)]
                             + [dict(c, atr_regime=g) for g in (1, 2)] + [dict(c, dow=d) for d in (1, 2, 3)])
STAGES = [('swing', stage_swing), ('entry', stage_entry), ('stop', stage_stop), ('mgmt', stage_mgmt), ('exit', stage_exit),
          ('anchor', stage_anchor), ('direction', stage_dir), ('filters', stage_filter)]


def dedupe(cases): return list({rn.digest(c): c for c in cases}.values())
def slim(r): return {k: v for k, v in r.items() if k != 'trades'}
def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))


def rank(records):
    ok = lambda r: r['metrics']['trades'] >= 60  # noqa: E731
    elig = [r for r in records if ok(r) and r['metrics']['net'] > 0 and (r['metrics']['pf'] or 0) >= 1.05]
    top = sorted(elig, key=lambda r: (r['metrics']['ret_dd'], r['metrics']['pf'] or 0), reverse=True)[:3]
    for r in top: r['carry'] = 'eligible'
    if len(top) < 3:
        rest = sorted([r for r in records if ok(r) and r not in top], key=lambda r: r['metrics']['pf'] or 0, reverse=True)[:3 - len(top)]
        for r in rest: r['carry'] = 'not profitable (best PF with >= 60 trades)'
        top += rest
    return top


def record_search(track, stage, recs):
    p = R / 'SEARCH RESULTS.json'; allr = read(p) if p.exists() else []
    keys = {(x['track'], x['stage'], rn.digest(x['parameters']), x['window'][0]) for x in allr}
    for r in recs:
        k = (track, stage, rn.digest(r['parameters']), r['start'])
        if k not in keys: allr.append(dict(track=track, stage=stage, window=[r['start'], r['end']], model=r['model'], parameters=r['parameters'], metrics=r['metrics'], clean=r['clean'], native={k2: r['native'][k2] for k2 in ('fresh_low', 'fresh_high', 'placed', 'filtered', 'expired_orders', 'skipped_stops', 'modify_fails')}))
    rn.save(p, allr)


def freeze():
    files = [R / 'PLAN.md', R / 'engine.py', R / 'runner.py', R / 'pipeline.py']
    rn.save(R / 'FROZEN.json', dict(frozen_at=datetime.now().isoformat(), split=dict(development=DEV, validation=VAL, oos=OOS), files={str(f): rn.sha(f) for f in files}))


def verify():
    for p, h_ in read(R / 'FROZEN.json')['files'].items(): assert rn.sha(Path(p)) == h_, f'changed after freeze: {p}'


def parity():
    verify(); cases = [base('london'), base('newyork'), dict(base('newyork'), dir=1)]
    raws = ['L8', 'NY8', 'SHORT_NY8']; recs = rn.batch('parity-raw5y-m4', cases, *RAW5, model=4); out = {}
    for rec, raw in zip(recs, raws):
        ref = json.loads(gzip.decompress((RAW / 'native' / f'nw-EURUSD-{raw}-5y' / 'trades.json.gz').read_bytes()))
        a = [(t['open_time'][:19], t['close_time'][:19], round(t['volume'], 2), round(t['net_profit'], 2)) for t in rec['trades']]
        b = [(datetime.fromisoformat(t['open_time']).isoformat()[:19], datetime.fromisoformat(t['close_time']).isoformat()[:19], round(t['volume'], 2), round(t['net_profit'], 2)) for t in ref]
        diff = sum(x != y for x, y in zip(a, b)) + abs(len(a) - len(b))
        out[raw] = dict(engine_trades=len(a), raw_trades=len(b), mismatches=diff, engine_net=round(sum(x[3] for x in a), 2), raw_net=round(sum(x[3] for x in b), 2), first_mismatch=next(([x, y] for x, y in zip(a, b) if x != y), None))
        print('PARITY', raw, json.dumps(out[raw]), flush=True)
    rn.save(R / 'PARITY.json', out); assert all(v['mismatches'] == 0 for v in out.values()), 'engine parity failed'


def search(track):
    verify(); assert all(v['mismatches'] == 0 for v in read(R / 'PARITY.json').values()), 'run parity first'
    carry = [base(track)]; trail = []
    for stage, gen in STAGES:
        cases = dedupe([v for c in carry for v in gen(c)])
        recs = rn.batch(f'{track}-{stage}-dev-m1', cases, *DEV, model=1); record_search(track, stage, recs)
        top = rank(recs); carry = [t['parameters'] for t in top]
        trail.append(dict(stage=stage, tested=len(cases), top=[dict(parameters=t['parameters'], metrics=t['metrics'], carry=t['carry']) for t in top]))
        print('STAGE', track, stage, len(cases), [(round(t['metrics']['pf'] or 0, 2), t['metrics']['trades'], round(t['metrics']['return_pct'], 1), t['carry'][:8]) for t in top], flush=True)
    rn.save(R / f'SEARCH-{track}.json', trail)


def neighbours(c):
    def around(seq, v):
        i = min(range(len(seq)), key=lambda j: abs(seq[j] - v)); return [seq[j] for j in (i - 1, i, i + 1) if 0 <= j < len(seq)]
    ws = around(WINDOWS_W, c['w']); ai = ANCHORS.index((c['hour'], c['minute'])); anchors = [ANCHORS[j] for j in (ai - 1, ai, ai + 1) if 0 <= j < len(ANCHORS)]
    if c['tp_r'] > 0: exits = [dict(tp_r=r) for r in around(RR, c['tp_r'])]
    elif c['exit_mode'] == 1: exits = [dict(hold_h=0, exit_mode=1), dict(hold_h=8, exit_mode=0)]
    else: exits = [dict(hold_h=hh) for hh in around(HOLDS, c['hold_h'])]
    return dedupe([dict(c, w=w, hour=a[0], minute=a[1], **e) for w in ws for a in anchors for e in exits])


def plateau(track):
    verify(); finals = read(R / f'SEARCH-{track}.json')[-1]['top']; out = []
    for k, f in enumerate(finals):
        cases = neighbours(f['parameters']); recs = rn.batch(f'{track}-plateau{k}-dev-m1', cases, *DEV, model=1); record_search(track, f'plateau{k}', recs)
        nets = [r['metrics']['net'] for r in recs]; pfs = [r['metrics']['pf'] or 0 for r in recs]
        res = dict(final=k, parameters=f['parameters'], dev=f['metrics'], neighbours=len(recs), positive_share=round(sum(n > 0 for n in nets) / len(nets), 3), median_pf=round(statistics.median(pfs), 3))
        res['passed'] = res['positive_share'] >= 0.70 and res['median_pf'] >= 1.05; out.append(res); print('PLATEAU', track, json.dumps({k2: v for k2, v in res.items() if k2 != 'parameters'}), flush=True)
    rn.save(R / f'PLATEAU-{track}.json', out)


def confirm(track):
    verify(); finals = [p for p in read(R / f'PLATEAU-{track}.json') if p['passed']]; out = dict(track=track, finalists=len(finals))
    if not finals: out['verdict'] = 'REJECTED_AT_PLATEAU'; rn.save(R / f'CONFIRM-{track}.json', out); print('CONFIRM', track, out, flush=True); return
    cases = [f['parameters'] for f in finals]
    dev = rn.batch(f'{track}-confirm-dev-m4', cases, *DEV, model=4); val = rn.batch(f'{track}-confirm-val-m4', cases, *VAL, model=4)
    record_search(track, 'confirm-dev-m4', dev); record_search(track, 'confirm-val-m4', val)
    rows = [dict(parameters=c, dev=slim(d)['metrics'], val=slim(v)['metrics']) for c, d, v in zip(cases, dev, val)]
    ok = [r for r in rows if r['val']['trades'] >= 15 and r['val']['net'] > 0]
    out.update(rows=rows)
    if not ok: out['verdict'] = 'REJECTED_AT_VALIDATION'
    else:
        pick = max(ok, key=lambda r: r['val']['pf'] or 0); out.update(verdict='SELECTED', selected=pick['parameters'])
    rn.save(R / f'CONFIRM-{track}.json', out); print('CONFIRM', track, out.get('verdict'), json.dumps([(r['dev']['pf'], r['val']['pf'], r['val']['trades']) for r in rows]), flush=True)


def oos(track):
    verify(); c = read(R / f'CONFIRM-{track}.json'); assert c.get('verdict') == 'SELECTED', 'no selected finalist'
    assert not (R / 'native' / f'{track}-oos-m4' / 'results.json').exists() or True
    rec = rn.batch(f'{track}-oos-m4', [c['selected']], *OOS, model=4, optimize=False)[0]; record_search(track, 'oos-m4', [rec])
    import importlib.util
    s = importlib.util.spec_from_file_location('rob', B.parent / 'Calyx Research Pipeline' / 'robustness.py'); rob = importlib.util.module_from_spec(s); s.loader.exec_module(rob)
    tr = rec['trades']; half = tr[len(tr) // 2:]; gp = sum(t['net_profit'] for t in half if t['net_profit'] > 0); gl = -sum(t['net_profit'] for t in half if t['net_profit'] < 0)
    dep = rob.dependence(tr); m = rec['metrics']
    g = dict(net_positive=m['net'] > 0, pf=(m['pf'] or 0) >= 1.15, trades=m['trades'] >= 30, recent_half_pf=(gp / gl if gl else 9) > 1, best_day_trade=dep.get('verdict') == 'PASS')
    out = dict(track=track, parameters=c['selected'], metrics=m, recent_half_pf=round(gp / gl, 3) if gl else None, dependence=dep, gate=g, passed=all(g.values()),
               label='retrospective OOS, previously inspected in the raw study')
    rn.save(R / f'OOS-{track}.json', out); print('OOS', track, 'PASS' if out['passed'] else 'FAIL', json.dumps(m), json.dumps(g), flush=True)


if __name__ == '__main__':
    cmd = sys.argv[1]
    with rn.lease():
        if cmd == 'freeze': freeze()
        elif cmd == 'parity': parity()
        else: {'search': search, 'plateau': plateau, 'confirm': confirm, 'oos': oos}[cmd](sys.argv[2])
