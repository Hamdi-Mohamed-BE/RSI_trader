"""Best 1-Step with the Calyx Weekend Flat rule (owner 2026-11-11: "how does this affect the pass rate and pass days and return"). Rules exactly as the helper EA:
non-crypto symbols flat from Friday 16:30 New York (17:00 - 30 min lead) to Sunday 17:00 NY; US index / metal symbols flat 12:00 NY on early-halt holidays (back 18:30, Friday
after Thanksgiving back 23:00); before Good Friday (indices / metals) and Christmas / New Year (also FX): flat 12:00 NY on the previous weekday, back 00:00 NY next weekday.
Stream transform (INPUTS-B1.json -> INPUTS-B1W.json): a trade still open at its first flat time F closes at F with the floating P/L of the last 5-minute mark before F
(0 if none), swap scaled by the share of time held, same commission / entry cost, marks after F dropped; a trade opened inside a flat window is removed.
The engines and everything else are unchanged (ftmo_b1.py jobs, names B1W = guard, B1WU = no guard). In-sample replay, not a native run.
Run from AAA EAs/EA store: uv run --with pandas --with numpy python "<this>" stream | sims [workers] | table"""
import importlib.util, json, sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

H = Path(__file__).resolve().parent
UTC = timezone.utc


def nth_dow(y, m, dow, n):  # dow: Monday=0
    d = date(y, m, 1); d += timedelta(days=(dow - d.weekday()) % 7); return d + timedelta(days=7 * (n - 1))


def last_dow(y, m, dow):
    d = (date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1)); return d - timedelta(days=(d.weekday() - dow) % 7)


def observed(d): return d - timedelta(days=1) if d.weekday() == 5 else d + timedelta(days=1) if d.weekday() == 6 else d


def prev_wd(d):
    d -= timedelta(days=1)
    while d.weekday() >= 5: d -= timedelta(days=1)
    return d


def next_wd(d):
    d += timedelta(days=1)
    while d.weekday() >= 5: d += timedelta(days=1)
    return d


def easter(y):
    a, b, c = y % 19, y // 100, y % 100; d, e = b // 4, b % 4; f = (b + 8) // 25; g = (b - f + 1) // 3; h = (19 * a + b - d - g + 15) % 30; i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7; m = (a + 11 * h + 22 * l) // 451; return date(y, (h + l - 7 * m + 114) // 31, (h + l - 7 * m + 114) % 31 + 1)


def ny_dst(utc):
    on = datetime.combine(nth_dow(utc.year, 3, 6, 2), datetime.min.time(), UTC) + timedelta(hours=7); off = datetime.combine(nth_dow(utc.year, 11, 6, 1), datetime.min.time(), UTC) + timedelta(hours=6)
    return on <= utc < off


def ny_epoch(d, minutes):
    guess = datetime.combine(d, datetime.min.time(), UTC) + timedelta(minutes=minutes, hours=5)
    return int((datetime.combine(d, datetime.min.time(), UTC) + timedelta(minutes=minutes, hours=4 if ny_dst(guess) else 5)).timestamp())


def sym_class(sym):
    s = sym.upper()
    if any(k in s for k in ('BTC', 'ETH', 'XRP', 'SOL', 'LTC')): return 0
    if any(k in s for k in ('XAU', 'XAG', 'GOLD', 'OIL', 'US30', 'US100', 'USTEC', 'NAS', 'US500', 'SPX', 'DJ', 'US2000')): return 1
    return 2 if len(s) == 6 and s.isalpha() else 4


def windows(years):
    W = []
    for y in years:
        for d in (nth_dow(y, 1, 0, 3), nth_dow(y, 2, 0, 3), last_dow(y, 5, 0), observed(date(y, 6, 19)), observed(date(y, 7, 4)), nth_dow(y, 9, 0, 1), nth_dow(y, 11, 3, 4)):
            W.append((ny_epoch(d, 720), ny_epoch(d, 18 * 60 + 30), 1))
        tg = nth_dow(y, 11, 3, 4) + timedelta(days=1); W.append((ny_epoch(tg, 720), ny_epoch(tg, 23 * 60), 1))
        j3 = date(y, 7, 3)
        if j3.weekday() <= 3: W.append((ny_epoch(j3, 720), ny_epoch(j3, 18 * 60 + 30), 1))
        gf = easter(y) - timedelta(days=2); W.append((ny_epoch(prev_wd(gf), 720), ny_epoch(next_wd(gf), 0), 1 | 4))
        for d in (observed(date(y, 12, 25)), observed(date(y + 1, 1, 1))): W.append((ny_epoch(prev_wd(d), 720), ny_epoch(next_wd(d), 0), 1 | 2 | 4))
    return W


HOL = windows(range(2019, 2028))


def weekly(t, cls):
    if cls == 0: return None
    u = datetime.fromtimestamp(t, UTC); ny = u - timedelta(hours=4 if ny_dst(u) else 5); m = ny.hour * 60 + ny.minute; wd = ny.weekday()   # Monday 0 .. Sunday 6
    if (wd == 4 and m >= 16 * 60 + 30) or wd == 5 or (wd == 6 and m < 17 * 60): return True
    return False


def in_flat(t, cls): return weekly(t, cls) or any(a <= t < b and (c & cls) for a, b, c in HOL)


def first_flat(op, cl, cls):
    """First flat epoch strictly after op and before cl (or None). Fridays checked from the NY calendar; holidays from HOL."""
    cands = [a for a, b, c in HOL if (c & cls) and op < a < cl]
    if cls:
        u = datetime.fromtimestamp(op, UTC); d = (u - timedelta(hours=5)).date()
        for k in range(0, 15):
            day = d + timedelta(days=k)
            if day.weekday() == 4:
                f = ny_epoch(day, 16 * 60 + 30)
                if op < f < cl: cands.append(f); break
                if f >= cl: break
    return min(cands) if cands else None


def stream():
    d = json.loads((H / 'INPUTS-B1.json').read_text(encoding='utf-8')); end = d['year_end_exclusive_epoch']; out = []; st = Counter(); per = defaultdict(lambda: [0, 0.0, 0.0])
    for c in d['candidates']:
        cls = sym_class(c['symbol'])
        if in_flat(c['op'], cls): st['removed_opened_in_window'] += 1; per[c['ea']][0] += 1; continue
        cl = c['cl'] if c['cl'] is not None else end
        f = first_flat(c['op'], cl, cls)
        if f is None: out.append(c); st['unchanged'] += 1; continue
        x = dict(c); marks = [m for m in c['marks'] if m[0] < f]; g = marks[-1][1] if marks else 0.0
        per[c['ea']][1] += (c['unit_gross'] - g) / c['unit_risk']; frac = (f - c['op']) / max(1, cl - c['op'])
        per[c['ea']][2] += (c['unit_swap'] - c['unit_swap'] * frac) / c['unit_risk']
        x.update(cl=f, unit_gross=g, unit_swap=c['unit_swap'] * frac, marks=marks, end_censored=False, weekend_flat_cut=True, source_forced_close_epoch=f)
        out.append(x); st['cut_at_flat'] += 1
    (H / 'INPUTS-B1W.json').write_text(json.dumps(dict(d, candidates=out), separators=(',', ':')), encoding='utf-8')
    info = dict(counts=dict(st), total=len(d['candidates']), per_ea={k: dict(removed=v[0], gross_r_lost_by_cuts=round(v[1], 1), swap_r_saved=round(-v[2], 1)) for k, v in per.items()})
    (H / 'WEEKEND_STREAM.json').write_text(json.dumps(info, indent=1), encoding='utf-8'); print(json.dumps(info, indent=1))


JOBS = [(k, n, r) for r in ('0.50',) for k, n in (('f1g', 'B1W'), ('f1u', 'B1WU'), ('ch', 'B1W'), ('ch', 'B1WU'), ('fu', 'B1W'), ('fu', 'B1WU'))]


def run(job):
    spec = importlib.util.spec_from_file_location('ftmo_b1', H / 'ftmo_b1.py'); M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
    kind, name, risk = job; m = M.p7()
    orig = m.engines

    def eng():
        S, *rest = orig()
        for n in ('B1W', 'B1WU'): S.CANDIDATES[n] = dict(label=n, guard=not n.endswith('U'), risks=m.RISKS, members=None)
        return (S, *rest)
    m.engines = eng
    if kind == 'f1u': m.f1u(name, risk); return job
    S, F1, *_ = m.engines()
    {'ch': lambda: S.challenge(name, risk), 'f1g': lambda: F1.main(name, risk), 'fu': lambda: S.funded(name, risk)}[kind]()
    return job


def sims(workers):
    todo = [j for j in JOBS if not (H / f"{dict(f1g='F1P', f1u='F1U', ch='CH', fu='FU')[j[0]]}-{j[1]}-{j[2]}.json").exists()]
    with ProcessPoolExecutor(workers) as ex:
        for j in ex.map(run, todo): print('finished', *j, flush=True)
    print('ALL DONE', flush=True)


def ledger_stats(path):
    d = json.loads(path.read_text(encoding='utf-8')); rs = sorted(((c['cl'] or d['year_end_exclusive_epoch'], (c['unit_gross'] + c['unit_commission'] + c['unit_swap']) / c['unit_risk'], c['ea'])
                                                                 for c in d['candidates']))
    gw = sum(r for _, r, _ in rs if r > 0); gl = -sum(r for _, r, _ in rs if r < 0); eq = pk = dd = 0.0; per = defaultdict(float); yrs = defaultdict(float)
    for t, r, ea in rs:
        eq += r; pk = max(pk, eq); dd = max(dd, pk - eq); per[ea] += r; yrs[datetime.fromtimestamp(t, UTC).year] += r
    return dict(trades=len(rs), total_r=round(sum(r for _, r, _ in rs), 1), pf=round(gw / gl, 3), win=round(100 * sum(r > 0 for _, r, _ in rs) / len(rs), 1), closed_dd_r=round(dd, 1),
                per_ea={k: round(v, 1) for k, v in sorted(per.items())}, years={k: round(v, 1) for k, v in sorted(yrs.items())})


def table():
    out = dict(ledger=dict(base=ledger_stats(H / 'INPUTS-B1.json'), weekend_flat=ledger_stats(H / 'INPUTS-B1W.json')), sims={})
    for pre, a, b in (('F1P', 'B1', 'B1W'), ('F1U', 'B1U', 'B1WU'), ('CH', 'B1', 'B1W'), ('CH', 'B1U', 'B1WU'), ('FU', 'B1', 'B1W'), ('FU', 'B1U', 'B1WU')):
        for n in (a, b):
            f = H / f'{pre}-{n}-0.50.json'
            if f.exists(): x = json.loads(f.read_text(encoding='utf-8')); out['sims'][f'{pre}-{n}'] = dict(mc=x['mc'], hist=x.get('hist'))
    (H / 'WEEKEND_RESULTS.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8'); print(json.dumps(out['ledger'], indent=1))


if __name__ == '__main__':
    a = sys.argv[1:]
    {'stream': stream, 'table': table}.get(a[0], lambda: sims(int(a[1]) if len(a) > 1 else 6))()
