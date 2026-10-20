"""Part A: older-history replay (2021-10-07..2025-10-06 starts) and Part B: 4-week block bootstrap, FLAT50 vs FLAT100.

Engine = FTMO Dial Study 2026-10-20 DialTrial over the Faster Screen core engine (both hash-frozen). No MT5/trading.
python run.py freeze | older | bootstrap
"""
import bisect, copy, gzip, hashlib, importlib.util, json, math, random, statistics, sys, time
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

R = Path(__file__).resolve().parent; B = R.parent; Z = ZoneInfo('Europe/Prague')
DIAL = B / 'FTMO Dial Study 2026-10-20'; FASTER = B / 'FTMO Faster Portfolio Screen 2026-10-16'
spec = importlib.util.spec_from_file_location('dial', DIAL / 'run.py'); d = importlib.util.module_from_spec(spec); spec.loader.exec_module(d)
e = d.e
PLAN = json.loads((R / 'PLAN.json').read_text(encoding='utf-8'))
POLICIES = {'FLAT50': [(-1e9, 50)], 'FLAT100': [(-1e9, 100)]}
PATHS, SEED, BLOCK_DAYS, BLOCKS = PLAN['part_b_bootstrap']['paths'], PLAN['part_b_bootstrap']['seed'], 28, 7


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def midnight(x): return datetime.combine(x, datetime.min.time(), tzinfo=Z).timestamp()


def splan_for(window):
    p = copy.deepcopy(e.read(FASTER / 'PLAN.json'))
    p['history'] = dict(p['history'], start_prague=window[0], end_exclusive_prague=window[1])
    return p


def freeze():
    files = [R / 'PLAN.json', R / 'prepare.py', Path(__file__), R / 'INPUTS-older.json', R / 'INPUTS-pool5y.json', R / 'SOURCES.json',
             DIAL / 'run.py', DIAL / 'FROZEN.json', FASTER / 'core_engine.py', FASTER / 'PLAN.json']
    (R / 'FROZEN.json').write_text(json.dumps(dict(frozen_at=datetime.now(Z).isoformat(), files={str(f): sha(f) for f in files}), indent=1), encoding='utf-8')
    print('frozen', len(files))


def check_frozen():
    for p, h in json.loads((R / 'FROZEN.json').read_text(encoding='utf-8'))['files'].items():
        assert sha(p) == h, f'changed after freeze: {p}'


def per_trial(t, horizon_days=180):
    both = t['total_elapsed_to_both']['inclusive_prague_days'] if t['total_elapsed_to_both'] else None
    acc = t.get('access_5bd_illustration_epoch')
    fund = None if not acc else (datetime.fromtimestamp(acc, Z).date() - datetime.fromtimestamp(t['start_epoch'], Z).date()).days + 1
    active = both or horizon_days
    return dict(outcome=t['outcome'], both=both, funded=fund, breach=t['outcome'].startswith('failed'),
                unfinished=t['outcome'].startswith('pending') or t['outcome'] == 'phase2_not_started_wait',
                p1=t['phase1']['elapsed_to_terminal']['inclusive_prague_days'] if t['phase1']['status'] == 'passed' else None,
                eqdd=t['max_sampled_equity_drawdown_cash'], day=t['max_daily_sampled_equity_loss'], trades=len(t['trades']),
                per_month=len(t['trades']) / active * 30.4375, per_weekday=len(t['trades']) / max(1, active * 5 / 7),
                soft_buffer=t['counts'].get('soft_total_buffer9200', 0) > 0, reserve_blocks=t['counts'].get('soft_daily_reserve300', 0))


def q(arr, p):
    s = sorted(arr); return s[min(len(s) - 1, max(0, math.ceil(p * len(s)) - 1))] if s else None


def summarize(rows):
    n = len(rows); both = [r['both'] for r in rows if r['both']]
    share = lambda f: round(sum(f(r) for r in rows) / n, 4)  # noqa: E731
    return dict(n=n, breach_share=share(lambda r: r['breach']), unfinished_share=share(lambda r: r['unfinished']),
                both_within={str(k): share(lambda r, k=k: bool(r['both']) and r['both'] <= k) for k in (60, 90, 120, 180)},
                phase1_within_60=share(lambda r: bool(r['p1']) and r['p1'] <= 60),
                median_days_both=statistics.median(both) if both else None, median_days_funded=statistics.median([r['funded'] for r in rows if r['funded']]) if both else None,
                eqdd_p50=round(q([r['eqdd'] for r in rows], .5), 1), eqdd_p95=round(q([r['eqdd'] for r in rows], .95), 1), eqdd_p99=round(q([r['eqdd'] for r in rows], .99), 1),
                eqdd_max=round(max(r['eqdd'] for r in rows), 1), day_p95=round(q([r['day'] for r in rows], .95), 1), day_p99=round(q([r['day'] for r in rows], .99), 1),
                day_max=round(max(r['day'] for r in rows), 1), median_trades=statistics.median(r['trades'] for r in rows),
                median_trades_per_month=round(statistics.median(r['per_month'] for r in rows), 2), median_trades_per_weekday=round(statistics.median(r['per_weekday'] for r in rows), 3),
                soft_buffer_share=share(lambda r: r['soft_buffer']), median_reserve_blocks=statistics.median(r['reserve_blocks'] for r in rows),
                outcomes=dict(Counter(r['outcome'] for r in rows)))


def older():
    check_frozen()
    data = json.loads((R / 'INPUTS-older.json').read_text(encoding='utf-8'))
    plan = splan_for(data['window']); events = e.master_events(plan, data); epochs = [x[0] for x in events]
    out = {}; began = time.time()
    for name, bands in POLICIES.items():
        for sc in plan['scenarios']:
            rows = []
            for s in data['starts']:
                w = events[bisect.bisect_left(epochs, s['epoch']):bisect.bisect_left(epochs, s['horizon_epoch'])]
                t = d.replay(plan, s, sc['cost'], sc['handover'], w, bands)
                rows.append(dict(per_trial(t), start=s['date'], pass_date=None if not t['both_pass_epoch'] else datetime.fromtimestamp(t['both_pass_epoch'], Z).date().isoformat()))
            key = f"{name}|{sc['cost']}|{sc['handover']}"
            out[key] = dict(summary=summarize(rows), distinct_pass_dates=len({r['pass_date'] for r in rows if r['pass_date']}),
                            by_start_year={y: summarize([r for r in rows if r['start'][:4] == y]) for y in sorted({r['start'][:4] for r in rows})}, rows=rows)
            print(key, f"{time.time() - began:.0f}s", json.dumps({k: out[key]['summary'][k] for k in ('breach_share', 'both_within', 'median_days_both', 'eqdd_max', 'day_max')}), flush=True)
    surv = all(v['summary']['breach_share'] == 0 and v['summary']['both_within']['180'] >= .95 and v['summary']['eqdd_max'] < 900 and v['summary']['day_max'] < 450
               for k, v in out.items() if k.startswith('FLAT100'))
    (R / 'OLDER.json.gz').write_bytes(gzip.compress(json.dumps(out).encode(), 6, mtime=0))
    (R / 'OLDER-SUMMARY.json').write_text(json.dumps(dict(flat100_survives=surv, starts=len(data['starts']), window=data['window'],
                                                           results={k: {kk: vv for kk, vv in v.items() if kk != 'rows'} for k, v in out.items()}), indent=1), encoding='utf-8')
    print('FLAT100 survives older-history rule:', surv)


def path_events(pool, mondays, blocks_index, rng, start_day, priority):
    rows = []
    for k in range(BLOCKS):
        src = mondays[rng.randrange(len(mondays))]; tgt = start_day + timedelta(days=BLOCK_DAYS * k)
        shift = (tgt - src).days * 86400
        lo, hi = blocks_index[src]
        for c in pool[lo:hi]:
            rows.append(dict(c, id=f"{c['id']}#{k}", op=c['op'] + shift, cl=None if c['cl'] is None else c['cl'] + shift,
                             marks=[(m[0] + shift, m[1]) for m in c['marks']]))
    horizon = midnight(start_day + timedelta(days=180)); ev = []
    for r in rows:
        ev.append((r['op'], 3, priority[r['ea']], r['id'], r, None))
        if r['cl'] is not None and r['cl'] < horizon:
            ev.append((r['cl'], 4 if r['cl'] == r['op'] else 1, priority[r['ea']], r['id'], r, None))
        for m in r['marks']:
            ev.append((m[0], 2, priority[r['ea']], r['id'], r, m))
    x = start_day
    while x < start_day + timedelta(days=180):
        ev.append((midnight(x), 0, -1, '', None, None)); x += timedelta(days=1)
    ev.sort(key=lambda z: z[:4])
    return [z for z in ev if z[0] < horizon]


def bootstrap():
    check_frozen()
    data = json.loads((R / 'INPUTS-pool5y.json').read_text(encoding='utf-8'))
    plan = splan_for(data['window']); priority = {ea: i for i, ea in enumerate(plan['candidate_priority'])}
    start_day = date(2030, 1, 7)  # synthetic Monday; only weekday / Prague-day structure matters
    start = dict(date=start_day.isoformat(), epoch=midnight(start_day), horizon_date=(start_day + timedelta(days=180)).isoformat(), horizon_epoch=midnight(start_day + timedelta(days=180)))
    scenarios = [dict(cost=c, handover='next_prague_midnight') for c in ('recorded_exness', 'fixed_cost_stress')]
    excluded = [c for c in data['candidates'] if c['end_censored']]
    allc = sorted((c for c in data['candidates'] if not c['end_censored']), key=lambda c: c['op'])
    ops = [c['op'] for c in allc]
    pools = {'5y': (date(2021, 10, 11), date(2026, 10, 6)), 'older4y': (date(2021, 10, 11), date(2025, 10, 6))}  # first Monday after 2021-10-07
    out = {}; began = time.time()
    for pname, (first, end) in pools.items():
        mondays = []; m = first
        while m + timedelta(days=BLOCK_DAYS) <= end:
            mondays.append(m); m += timedelta(days=7)
        index = {m: (bisect.bisect_left(ops, midnight(m)), bisect.bisect_left(ops, midnight(m + timedelta(days=BLOCK_DAYS)))) for m in mondays}
        rng = random.Random(SEED); rows = {f'{p}|{s["cost"]}': [] for p in POLICIES for s in scenarios}
        for i in range(PATHS):
            ev = path_events(allc, mondays, index, rng, start_day, priority)
            for pol, bands in POLICIES.items():
                for sc in scenarios:
                    t = d.replay(plan, start, sc['cost'], sc['handover'], ev, bands)
                    rows[f'{pol}|{sc["cost"]}'].append(per_trial(t))
            if i % 250 == 0:
                print(pname, 'path', i, f'{time.time() - began:.0f}s', flush=True)
        for k, v in rows.items():
            out[f'{pname}|{k}'] = summarize(v)
            print(pname, k, json.dumps({kk: out[f'{pname}|{k}'][kk] for kk in ('breach_share', 'both_within', 'median_days_both', 'eqdd_p95', 'day_p95', 'unfinished_share')}), flush=True)
    accept = all(v['breach_share'] <= .05 for k, v in out.items() if '|FLAT100|' in k)
    strict = all(v['breach_share'] <= .01 for k, v in out.items() if '|FLAT100|' in k)
    (R / 'BOOTSTRAP-SUMMARY.json').write_text(json.dumps(dict(paths=PATHS, seed=SEED, block_days=BLOCK_DAYS, blocks=BLOCKS, excluded_end_censored=len(excluded),
                                                               flat100_breach_le_5pct_all=accept, flat100_breach_le_1pct_all=strict, results=out), indent=1), encoding='utf-8')
    print('FLAT100 breach <=5% everywhere:', accept, '| <=1%:', strict)


if __name__ == '__main__':
    {'freeze': freeze, 'older': older, 'bootstrap': bootstrap}[sys.argv[1]]()
