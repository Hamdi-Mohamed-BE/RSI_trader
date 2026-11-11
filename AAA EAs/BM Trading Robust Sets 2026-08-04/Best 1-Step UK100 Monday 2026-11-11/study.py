"""Best 1-Step + UK100 Monday dip (owner 2026-11-11: "start with point 3" = add the UK100 Monday dip to the Best 1-Step portfolio simulation).
Base = what would be installed now: Best 1-Step without Sell Nasdaq (10 EAs), weekend / holiday flat ON (Best 1-Step Search 2026-11-11/INPUTS-B1W.json minus sell-nasdaq).
New member = FTSE Three Setup Raw 2026-10-27 S2 Monday dip (unchanged raw EA and inputs: Monday, close < SMA20, RSI < 40, long, 2.5 ATR stop, 2R, 24 h max hold), UK100 H1,
native long-history run with intratrade marks via Portfolio P7 2026-11-10/p7.py machinery; the same weekend / holiday transform is applied (no-op for Monday trades except holidays).
Engines unchanged (frozen FTMO 1-Step / 2-step / funded); the engines' spec table gets UK100 (contract 1, min 0.05, step 0.01, leverage 15 like the other index; margin in GBP
treated as USD - approximation). Names: B1X = base guard, B1XU = base no guard, B1XM / B1XMU = with the Monday dip.
Run from AAA EAs/EA store: uv run --with pandas --with numpy python "<this>" streams | inputs | sims [workers] | table"""
import importlib.util, json, sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

H = Path(__file__).resolve().parent; B = H.parent; S1 = B / 'Best 1-Step Search 2026-11-11'
FTSE = B / 'FTSE Three Setup Raw 2026-10-27'
UK_SPEC = dict(contract=1, leverage=15, minimum=0.05, step=0.01, maximum=500)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def p7():
    m = load('p7', B / 'Portfolio P7 2026-11-10/p7.py'); m.H = H
    cfg = json.loads((FTSE / 'run-config.json').read_text(encoding='utf-8')); inputs = dict(cfg['common_inputs'], InpSetup1='false', InpSetup2='true', InpSetup3='false', InpRiskPercent='1.0')
    m.NEW = {'UK100MON': ('uk100-monday-dip', 'ema3-824231b1376b', 'UK100', 'H1', FTSE / 'EA/FTSE Three Setup Research EA.mq5', inputs)}
    orig = m.engines

    def eng():
        S, *rest = orig(); base = S.T.splan_for
        if not getattr(base, '_uk', False):
            def splan_for(window):
                plan = base(window); plan['risk']['specs'].setdefault('UK100', dict(UK_SPEC)); return plan
            splan_for._uk = True; S.T.splan_for = splan_for
        for n in ('B1X', 'B1XU', 'B1XM', 'B1XMU'): S.CANDIDATES[n] = dict(label=n, guard=not n.endswith('U'), risks=m.RISKS, members=None)
        return (S, *rest)
    m.engines = eng; return m


def streams():
    p7().streams()


def inputs():
    m = p7(); S, *_ = m.engines(); P, PR = S.P, S.PR; begin, end = PR.midnight(P.DATA_START), PR.midnight(P.DATA_END)
    S.PUB.CONTRACTS.setdefault('UK100', 1.30)   # UK100 = 1 GBP per point; GBPUSD ~1.30 (2021-26 average) converts the stop risk to USD (+-10% approximation, disclosed)
    import inspect
    old = "{'USTEC': 1., 'XAUUSD': 100., 'USDJPY': 100000.}"; src = inspect.getsource(S.PR.candidates); assert src.count(old) == 1
    exec(src.replace(old, "{'USTEC': 1., 'XAUUSD': 100., 'USDJPY': 100000., 'UK100': 1.30}"), S.PR.__dict__)   # same function, UK100 added (marks are USD equity already)
    uk, info = S.member_candidates('uk100-monday-dip', ('new', 'UK100MON'), begin, end, {}, S.sources()); print('UK100 Monday candidates', len(uk), info, flush=True)
    W = load('weekend_flat', S1 / 'weekend_flat.py'); ukw = []; st = Counter()
    for c in uk:
        cls = W.sym_class(c['symbol']); cl = c['cl'] if c['cl'] is not None else end
        if W.in_flat(c['op'], cls): st['removed'] += 1; continue
        f = W.first_flat(c['op'], cl, cls)
        if f is None: ukw.append(c); st['unchanged'] += 1; continue
        x = dict(c); marks = [mk for mk in c['marks'] if mk[0] < f]; g = marks[-1][1] if marks else 0.0; frac = (f - c['op']) / max(1, cl - c['op'])
        x.update(cl=f, unit_gross=g, unit_swap=c['unit_swap'] * frac, marks=marks, weekend_flat_cut=True); ukw.append(x); st['cut'] += 1
    print('weekend transform on UK100', dict(st), flush=True)
    base = json.loads((S1 / 'INPUTS-B1W.json').read_text(encoding='utf-8')); assert base['window'] == [P.DATA_START.isoformat(), P.DATA_END.isoformat()]
    b10 = [c for c in base['candidates'] if c['ea'] != 'sell-nasdaq-15min']
    meta = {k: v for k, v in base.items() if k != 'candidates'}
    (H / 'INPUTS-B1X.json').write_text(json.dumps(dict(meta, candidates=b10), separators=(',', ':')), encoding='utf-8')
    (H / 'INPUTS-B1XM.json').write_text(json.dumps(dict(meta, candidates=b10 + ukw), separators=(',', ':')), encoding='utf-8')
    (H / 'STREAMS.json').write_text(json.dumps(dict(base_10=len(b10), uk100_monday=len(ukw), uk_transform=dict(st), uk_source=info), indent=1, default=str), encoding='utf-8')
    print('B1X', len(b10), 'B1XM', len(b10) + len(ukw), flush=True)


JOBS = [(k, n, '0.50') for n0 in ('B1X', 'B1XM') for k, n in (('f1g', n0), ('f1u', n0 + 'U'), ('ch', n0), ('fu', n0), ('fu', n0 + 'U'))]


def run(job):
    kind, name, risk = job; m = p7()
    if kind == 'f1u': m.f1u(name, risk); return job
    S, F1, *_ = m.engines()
    {'ch': lambda: S.challenge(name, risk), 'f1g': lambda: F1.main(name, risk), 'fu': lambda: S.funded(name, risk)}[kind]()
    return job


def sims(workers):
    todo = [j for j in JOBS if not (H / f"{dict(f1g='F1P', f1u='F1U', ch='CH', fu='FU')[j[0]]}-{j[1]}-{j[2]}.json").exists()]
    with ProcessPoolExecutor(workers) as ex:
        for j in ex.map(run, todo): print('finished', *j, flush=True)
    print('ALL DONE', flush=True)


def ledger(path):
    d = json.loads(path.read_text(encoding='utf-8')); end = d['year_end_exclusive_epoch']
    rs = sorted(((c['cl'] or end), (c['unit_gross'] + c['unit_commission'] + c['unit_swap']) / c['unit_risk'], c['ea']) for c in d['candidates'])
    gw = sum(r for _, r, _ in rs if r > 0); gl = -sum(r for _, r, _ in rs if r < 0); eq = pk = dd = 0.0; per = defaultdict(float); days = defaultdict(float)
    for t, r, ea in rs:
        eq += r; pk = max(pk, eq); dd = max(dd, pk - eq); per[ea] += r; days[datetime.fromtimestamp(t, timezone.utc).date()] += r
    months = (end - d['year_begin_epoch']) / 86400 / 30.4375
    return dict(trades=len(rs), per_month=round(len(rs) / months, 1), per_day=round(len(rs) / months / 21, 2), total_r=round(sum(r for _, r, _ in rs), 1), pf=round(gw / gl, 3),
                closed_dd_r=round(dd, 1), worst_day_r=round(min(days.values()), 2), per_ea={k: round(v, 1) for k, v in sorted(per.items())})


def table():
    out = dict(ledger={n: ledger(H / f'INPUTS-{n}.json') for n in ('B1X', 'B1XM')}, sims={})
    for f in sorted(H.glob('*-B1X*-0.50.json')): x = json.loads(f.read_text(encoding='utf-8')); out['sims'][f.stem] = dict(mc=x['mc'], hist=x.get('hist'))
    (H / 'RESULTS.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8'); print(json.dumps(out['ledger'], indent=1))


if __name__ == '__main__':
    a = sys.argv[1:]
    {'streams': streams, 'inputs': inputs, 'table': table}.get(a[0], lambda: sims(int(a[1]) if len(a) > 1 else 6))()
