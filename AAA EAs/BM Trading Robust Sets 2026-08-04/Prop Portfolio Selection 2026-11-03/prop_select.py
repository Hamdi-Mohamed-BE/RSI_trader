"""Prop portfolio selection (PLAN.md, frozen before results). Reuses the frozen engine of Portfolio Prop Comparison 2026-10-22
(compare.py: FTMO 2-step at $100k, guarded / unguarded models, MC and funded income) unchanged; only new signal streams.
python prop_select.py prepare | challenge <cand> <risk> | funded <cand> <risk> | table
"""
import bisect, csv, hashlib, importlib.util, json, random, statistics, sys, time, traceback
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

R = Path(__file__).resolve().parent; B = R.parent


def load(name, path):
    s = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


C = load('prop_compare', B / 'Portfolio Prop Comparison 2026-10-22/compare.py')
PUB = load('long_publish', B / 'Portfolio Long History 2026-10-08/publish.py')
P, T, I, L, E, PR = C.P, C.T, C.I, C.L, C.E, C.PR
LONG = B / 'Portfolio Long History All ORB05 2026-10-14'
NAS = 'nasdaq-5m-candle-momentum'
SEG = {'dev': (date(2021, 10, 7), date(2023, 10, 6)), 'val': (date(2023, 10, 6), date(2024, 10, 6)), 'oos': (date(2024, 10, 6), date(2026, 10, 6)),
       'all': (date(2021, 10, 7), date(2026, 10, 6))}
C14 = ['xau-rsi-vwap', 'gold-overnight-value-area', 'xau-squeeze-momentum-standard', 'dmc-fresh-reaction-us100', 'ema3', 'xau-trend-progression',
       'xau-orb-london-ny-overlap-m30', 'nasdaq-overnight', 'us100-h1-orb-13utc', 'usdjpy-london-open-momentum', 'us100-month-end-flow',
       'dmc-current-xau', NAS, '3-way-gold', 'us100-orb-new-york-m30', 'us100-selective-orb-v3', 'xau-orb-new-york-m30']
ORBS = ['us100-h1-orb-13utc', 'us100-orb-new-york-m30', 'us100-selective-orb-v3', 'xau-orb-new-york-m30', 'xau-orb-london-ny-overlap-m30']
NINE = ['xau-rsi-vwap', 'usdjpy-london-open-momentum', 'us100-month-end-flow', NAS] + ORBS
# member -> (source, case); source: 'ftmo' / 'full-eas' long-history mapping, or 'new' = native.py label
A6_ON, A6_OFF, VPVC05 = ('new', 'Nasdaq 5M ATR6 DI ON'), ('new', 'Nasdaq 5M ATR6 DI OFF'), ('new', 'ORB VP Volume Confirmed 0.5R')
F = lambda s: ('ftmo', s)  # noqa: E731
X = lambda s: ('full-eas', s)  # noqa: E731
CANDIDATES = {
    'FTMO17': dict(label='FTMO guarded 17 (Current 14 + ORB)', guard=True, risks=('0.50', '1.00'), members={**{s: F(s) for s in C14}, NAS: A6_ON}),
    'CUR17': dict(label='Current 14 + ORB 17, no guard', guard=False, risks=('0.50', '0.75'), members={**{s: F(s) for s in C14}, NAS: A6_ON}),
    'PR9': dict(label='Prop ready 9 (DI ON)', guard=True, risks=('0.50', '1.00'), members={**{s: F(s) for s in NINE}, NAS: A6_ON}),
    'BP9': dict(label='Best Prop 9 (DI OFF)', guard=True, risks=('0.50', '1.00'), members={**{s: F(s) for s in NINE}, NAS: A6_OFF}),
    'BP15': dict(label='Best Prop 15 (DI OFF)', guard=True, risks=('0.50', '1.00'),
                 members={**{s: F(s) for s in NINE + ['ema3', '3-way-gold', 'gold-overnight-value-area', 'dmc-current-xau', 'dmc-fresh-reaction-us100']},
                          'dmc-fresh-reaction-xau': X('dmc-fresh-reaction-xau'), NAS: A6_OFF}),
    'C7': dict(label='Custom 7, guarded', guard=True, risks=('0.50', '1.00'),
               members={**{s: F(s) for s in ('ema3', 'dmc-current-xau', 'dmc-fresh-reaction-us100', 'gold-overnight-value-area', 'xau-rsi-vwap')},
                        'dmc-fresh-reaction-xau': X('dmc-fresh-reaction-xau'), NAS: A6_ON}),
    'C7U': dict(label='Custom 7, no guard', guard=False, risks=('0.50', '0.75'), members=None),   # same as C7
    'FV9': dict(label='funded_v1 roster, guarded', guard=True, risks=('0.50', '1.00'),
                members={NAS: A6_ON, 'ema3': F('ema3'), '3-way-gold': X('3-way-gold'), 'orb-volume-profile-volume-confirmed': VPVC05,
                         'xau-orb-london-ny-overlap-m30': F('xau-orb-london-ny-overlap-m30'), 'dmc-fresh-reaction-us100': F('dmc-fresh-reaction-us100'),
                         'dmc-current-xau': F('dmc-current-xau'), 'xau-rsi-vwap': F('xau-rsi-vwap'), 'gold-overnight-value-area': F('gold-overnight-value-area')}),
    'T5': dict(label='Turbo 5 roster, guarded', guard=True, risks=('0.50', '1.00'),
               members={'gold-overnight-value-area': F('gold-overnight-value-area'), 'ema3': F('ema3'), 'xau-rsi-vwap': F('xau-rsi-vwap'), NAS: A6_OFF,
                        '3-way-gold': X('3-way-gold')}),
    'FULL': dict(label='Full EA core (no news / hourly / crypto), no guard', guard=False, risks=('0.25', '0.50'), members='FULL'),
}
CANDIDATES['C7U']['members'] = CANDIDATES['C7']['members']
RISKS = {'0.25': 0.0025, '0.50': 0.005, '0.75': 0.0075, '1.00': 0.01}
DEPLOY_BEFORE = B / 'Nasdaq 5M ATR6 Stop Deployment 2026-11-02/before'


def verify_freeze():
    """The frozen engine's own check, except one documented change: the 2026-11-02 Nasdaq ATR6 deployment rewrote
    _00 Live profiles/Packages/FTMO/PACKAGE.json (Nasdaq SET hash + inputs). Accepted only if its pre-deployment backup equals
    the frozen hash; every engine file and every other source must still match exactly."""
    f = PR.read(E.R / 'FROZEN.json')
    assert all(sha(p) == v for p, v in f['files'].items()), 'frozen engine code changed'
    for p, v in f['source_files'].items():
        if sha(p) == v: continue
        backup = DEPLOY_BEFORE / Path(p).relative_to(B.parent)
        assert Path(p).name == 'PACKAGE.json' and backup.exists() and sha(backup) == v, ('frozen source changed', p)


E.verify_freeze = verify_freeze


def sources():
    plan = PR.read(LONG / 'PLAN.json'); state = PR.read(LONG / 'RUN_STATUS.json'); rows = PR.read(LONG / 'RISK_ROWS.json')
    new_plan = json.loads((R / 'NATIVE_PLAN.json').read_text(encoding='utf-8')); new_state = json.loads((R / 'RUN_STATUS.json').read_text(encoding='utf-8'))
    return plan, state, rows, new_plan, new_state


def member_candidates(slug, src_key, begin, end, cache, S):
    plan, state, rows, new_plan, new_state = S
    key = (slug, src_key)
    if key in cache: return cache[key]
    kind, name = src_key
    if kind == 'new':
        row = next(r for r in new_plan if r['label'] == name); receipt = new_state['complete'][row['case_id']]
        lookup = {(slug, x['position_id']): x for x in PUB.rows(PR.read(receipt['path']), row)}
    else:
        cid = plan['mappings'][kind][name]; row = next(x for x in plan['cases'] if x['case_id'] == cid); receipt = state['complete'][cid]
        lookup = {(x['key'], x['position_id']): x for x in rows[kind]} if kind in rows else {(slug, x['position_id']): x for x in PUB.rows(PR.read(receipt['path']), row)}
    for f, digest in row['production_hashes'].items():
        if kind != 'new' and sha(f) != digest and not f.endswith('.set'): raise AssertionError(('production source changed', f))
    path = Path(receipt['path']); assert sha(path) == receipt['sha256']
    src = dict(row=row, case=PR.read(path), folder=path.parent)
    cands = C.threeway_candidates(src, lookup, slug, begin, end)[0] if slug == '3-way-gold' else PR.candidates(src, lookup, slug, begin, end)
    cache[key] = (cands, dict(case=row['case_id'], sha256=receipt['sha256'], history_quality=src['case'].get('native', {}).get('history_quality')))
    return cache[key]


def prepare():
    S = sources(); begin, end = PR.midnight(P.DATA_START), PR.midnight(P.DATA_END); cache = {}; out = dict(streams={}, excluded={})
    plan = S[0]
    full = {s: X(s) for s in plan['mappings']['full-eas'] if not s.startswith('news-pulse') and s != 'gold-news-v9-direction' and not s.endswith('hourly-profiles')}
    full[NAS] = A6_ON
    # parity: the old-Nasdaq nine-EA stream built here must equal the retest INPUTS-DI_ON exactly
    nine_old = []
    for s in NINE: nine_old += member_candidates(s, F(s), begin, end, cache, S)[0]
    ref = json.loads((P.RT / 'INPUTS-DI_ON.json').read_text(encoding='utf-8'))['candidates']
    k = lambda c: c['id']  # noqa: E731
    out['parity_nine_old_vs_retest_DI_ON'] = sorted(nine_old, key=k) == sorted(ref, key=k)
    print('PARITY', out['parity_nine_old_vs_retest_DI_ON'], flush=True); assert out['parity_nine_old_vs_retest_DI_ON']
    for name, cfg in CANDIDATES.items():
        if name == 'C7U': continue
        members = full if cfg['members'] == 'FULL' else cfg['members']; cands = []; srcs = {}
        for slug, src_key in members.items():
            try:
                c, info = member_candidates(slug, src_key, begin, end, cache, S)
                bad = {x['symbol'] for x in c} - {'USTEC', 'XAUUSD', 'USDJPY'}
                if bad: raise ValueError(f'engine has no specs for {bad}')
                cands += c; srcs[slug] = dict(info, source=list(src_key), trades=len(c))
            except Exception as e:
                out['excluded'][f'{name}|{slug}'] = f'{type(e).__name__}: {str(e)[:200]}'; print('EXCLUDED', name, slug, out['excluded'][f'{name}|{slug}'], flush=True)
        data = dict(candidates=cands, year_begin_epoch=begin, year_end_exclusive_epoch=end, window=[P.DATA_START.isoformat(), P.DATA_END.isoformat()])
        (R / f'INPUTS-{name}.json').write_text(json.dumps(data, separators=(',', ':')), encoding='utf-8')
        out['streams'][name] = dict(members=srcs, per_ea=dict(Counter(c['ea'] for c in cands)), trades=len(cands))
        print(name, len(cands), len(srcs), 'members', flush=True)
    (R / 'SOURCES.json').write_text(json.dumps(out, indent=1), encoding='utf-8')


def setup(name):
    data = json.loads((R / f"INPUTS-{'C7' if name == 'C7U' else name}.json").read_text(encoding='utf-8'))
    plan = T.splan_for(data['window']); eas = sorted({c['ea'] for c in data['candidates']})
    plan['baskets'][name] = eas; plan['candidate_priority'] = plan['candidate_priority'] + [s for s in eas if s not in plan['candidate_priority']]
    events = E.master_events(plan, data)
    return data, plan, events, [x[0] for x in events]


def challenge(name, risk):
    cfg = CANDIDATES[name]; r = RISKS[risk]; began = time.time(); E.verify_freeze()
    data, plan, events, epochs = setup(name); pool, mondays, index, priority = C.mc_pool(data, plan); sd = date(2030, 1, 7)
    rows = []; d = P.DATA_START
    while d + timedelta(days=P.HORIZON) <= P.DATA_END:
        if d.weekday() < 5:
            x = C.challenge_one(plan, name, cfg['guard'], r, d, P.window(events, epochs, P.midnight(d), P.midnight(d + timedelta(days=P.HORIZON))))
            rows.append((d, x))
        d += timedelta(days=1)
    out = dict(candidate=name, label=cfg['label'], risk=r, guard=cfg['guard'], hist={s: T.summarize([x for d, x in rows if a <= d < b]) for s, (a, b) in SEG.items()})
    print(name, risk, {s: (v['pass_both_180'], v['breach']) for s, v in out['hist'].items()}, f'{time.time() - began:.0f}s', flush=True)
    rng = random.Random(T.SEED); mc = [C.challenge_one(plan, name, cfg['guard'], r, sd, T.bootstrap_events(pool, mondays, index, rng, sd, priority)) for _ in range(T.PATHS)]
    out['mc'] = T.summarize(mc); out['seconds'] = round(time.time() - began)
    (R / f'CH-{name}-{risk}.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8'); print('done', name, risk, out['seconds'], flush=True)


def funded(name, risk):
    cfg = CANDIDATES[name]; r = RISKS[risk]; began = time.time(); E.verify_freeze()
    data, plan, events, epochs = setup(name); pool, mondays, index, priority = C.mc_pool(data, plan); sd = date(2030, 1, 7)
    rows = []; d = P.DATA_START
    while d <= I.HIST_LAST_START:
        if d.weekday() < 5: rows.append(C.funded_one(plan, name, cfg['guard'], r, d, I.HIST_DAYS, P.window(events, epochs, P.midnight(d), P.midnight(d + timedelta(days=I.HIST_DAYS)))))
        d += timedelta(days=1)
    out = dict(candidate=name, risk=r, hist=L.summarize(rows, I.HIST_DAYS))
    days = T.BLOCK_DAYS * I.MC_BLOCKS; rng = random.Random(I.MC_SEED)
    mc = [C.funded_one(plan, name, cfg['guard'], r, sd, days, P.path_events(pool, mondays, index, rng, sd, priority, I.MC_BLOCKS)) for _ in range(P.PATHS)]
    out['mc'] = L.summarize(mc, days); out['seconds'] = round(time.time() - began)
    (R / f'FU-{name}-{risk}.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8'); print('done funded', name, risk, out['seconds'], flush=True)


if __name__ == '__main__':
    a = sys.argv[1:]
    {'prepare': lambda: prepare(), 'challenge': lambda: challenge(a[1], a[2]), 'funded': lambda: funded(a[1], a[2])}[a[0]]()
