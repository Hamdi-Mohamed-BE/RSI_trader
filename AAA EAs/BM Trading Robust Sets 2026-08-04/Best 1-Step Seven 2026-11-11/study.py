"""Owner 2026-11-11: "what if we keep only these" = Nasdaq 5M, Overnight Bias ORB, EMA3, Gold Band Wave, ORB VP Volume Confirmed, XAU RSI VWAP, UK100 Monday dip
(the 7 best of the last two months: HINDSIGHT SELECTION, disclosed). "Show their results, pass rate and expected return for last year only."
Streams = Best 1-Step UK100 Monday 2026-11-11/INPUTS-B1XM.json (weekend / holiday flat, 2021-10-07 -> 2026-10-06): S7 = the seven, B11 = all eleven.
Last year = 2025-10-06 -> 2026-10-06. FTMO 1-Step (frozen engines, $100k, 0.5%): historical starts in the last year (full 180-day follow-up only possible to 2026-04-09),
Monte Carlo from the last year's weeks only (names *LY) and from all years. Run from AAA EAs/EA store: uv run --with pandas --with numpy python "<this>" inputs | sims | table"""
import importlib.util, json, sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from datetime import date, datetime, timezone
from pathlib import Path

H = Path(__file__).resolve().parent; B = H.parent; UKD = B / 'Best 1-Step UK100 Monday 2026-11-11'
SEVEN = ['nasdaq-5m-candle-momentum', 'overnight-bias-orb', 'ema3', 'gold-band-wave', 'orb-volume-profile-volume-confirmed', 'xau-rsi-vwap', 'uk100-monday-dip']
LY = (date(2025, 10, 6), date(2026, 10, 6))
NAMES = ('S7', 'S7U', 'S7LY', 'S7LYU', 'B11', 'B11U', 'B11LY', 'B11LYU')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def p7():
    U = load('uk_study', UKD / 'study.py'); m = U.p7(); m.H = H; base = m.engines

    def eng():
        S, F1, O, N, C = base()
        for n in NAMES: S.CANDIDATES[n] = dict(label=n, guard=not n.endswith('U'), risks=m.RISKS, members=None)
        S.SEG['last_year'] = LY
        if not getattr(C.mc_pool, '_ly', False):
            orig = C.mc_pool

            def mc_pool(data, plan):
                pool, mondays, index, priority = orig(data, plan)
                if data.get('mc_from'):
                    keep = [d for d in mondays if d >= date.fromisoformat(data['mc_from'])]; mondays = keep; index = {d: index[d] for d in keep}
                return pool, mondays, index, priority
            mc_pool._ly = True; C.mc_pool = mc_pool
            for mod in (S, F1, O, N):
                if hasattr(mod, 'C'): mod.C.mc_pool = mc_pool
        return S, F1, O, N, C
    m.engines = eng; return m


def inputs():
    d = json.loads((UKD / 'INPUTS-B1XM.json').read_text(encoding='utf-8')); meta = {k: v for k, v in d.items() if k != 'candidates'}
    s7 = [c for c in d['candidates'] if c['ea'] in SEVEN]; assert {c['ea'] for c in s7} == set(SEVEN)
    for name, cands, ly in (('S7', s7, False), ('S7LY', s7, True), ('B11', d['candidates'], False), ('B11LY', d['candidates'], True)):
        (H / f'INPUTS-{name}.json').write_text(json.dumps(dict(meta, candidates=cands, **({'mc_from': LY[0].isoformat()} if ly else {})), separators=(',', ':')), encoding='utf-8')
    print('S7', len(s7), 'B11', len(d['candidates']), flush=True)


JOBS = [('f1g', 'S7', '0.50'), ('f1u', 'S7U', '0.50'), ('ch', 'S7', '0.50'), ('fu', 'S7', '0.50'), ('fu', 'S7U', '0.50')]   # owner 2026-11-11: stats for the approved 7


def run(job):
    kind, name, risk = job; m = p7()
    if kind == 'f1u': m.f1u(name, risk); return job
    S, F1, *_ = m.engines()
    {'ch': lambda: S.challenge(name, risk), 'f1g': lambda: F1.main(name, risk), 'fu': lambda: S.funded(name, risk)}[kind](); return job


def sims(workers=8):
    todo = [j for j in JOBS if not (H / f"{dict(f1g='F1P', f1u='F1U', ch='CH', fu='FU')[j[0]]}-{j[1]}-{j[2]}.json").exists()]
    with ProcessPoolExecutor(workers) as ex:
        for j in ex.map(run, todo): print('finished', *j, flush=True)
    print('ALL DONE', flush=True)


def ledger(name, a, b):
    d = json.loads((H / f'INPUTS-{name}.json').read_text(encoding='utf-8')); end = d['year_end_exclusive_epoch']
    ae, be = datetime(a.year, a.month, a.day, tzinfo=timezone.utc).timestamp(), datetime(b.year, b.month, b.day, tzinfo=timezone.utc).timestamp()
    rs = sorted(((c['cl'] or end), (c['unit_gross'] + c['unit_commission'] + c['unit_swap']) / c['unit_risk'], c['ea']) for c in d['candidates'] if ae <= c['op'] < be)
    gw = sum(r for _, r, _ in rs if r > 0); gl = -sum(r for _, r, _ in rs if r < 0); eq = pk = dd = 0.0; per = defaultdict(lambda: [0, 0.0, 0]); days = defaultdict(float); mon = defaultdict(float)
    for t, r, ea in rs:
        eq += r; pk = max(pk, eq); dd = max(dd, pk - eq); per[ea][0] += 1; per[ea][1] += r; per[ea][2] += r > 0
        dt = datetime.fromtimestamp(t, timezone.utc); days[dt.date()] += r; mon[dt.strftime('%Y-%m')] += r
    months = (b - a).days / 30.4375
    return dict(trades=len(rs), per_month=round(len(rs) / months, 1), per_day=round(len(rs) / months / 21, 2), total_r=round(sum(r for _, r, _ in rs), 1), pf=round(gw / gl, 3) if gl else None,
                win=round(100 * sum(r > 0 for _, r, _ in rs) / max(1, len(rs)), 1), closed_dd_r=round(dd, 1), worst_day_r=round(min(days.values()), 2) if days else None,
                losing_months=sum(1 for v in mon.values() if v < 0), months=dict(sorted((k, round(v, 1)) for k, v in mon.items())),
                per_ea={k: dict(trades=v[0], total_r=round(v[1], 1), win=round(100 * v[2] / max(1, v[0]), 1)) for k, v in sorted(per.items())})


def table():
    W = {'last_year': LY, 'all': (date(2021, 10, 7), date(2026, 10, 6)), '2021-23': (date(2021, 10, 7), date(2023, 10, 6))}
    out = dict(ledger={n: {w: ledger(n, *v) for w, v in W.items()} for n in ('S7', 'B11')}, sims={})
    for f in sorted(list(H.glob('F1*-*-0.50.json')) + list(H.glob('CH-*-0.50.json')) + list(H.glob('FU-*-0.50.json'))): x = json.loads(f.read_text(encoding='utf-8')); out['sims'][f.stem] = dict(mc=x['mc'], last_year=(x['hist'].get('last_year') if isinstance(x.get('hist'), dict) else None), all=(x['hist'].get('all') if isinstance(x.get('hist'), dict) else None))
    (H / 'RESULTS.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8'); print('written')


if __name__ == '__main__':
    a = sys.argv[1:]
    {'inputs': inputs, 'table': table}.get(a[0], lambda: sims(int(a[1]) if len(a) > 1 else 8))()
