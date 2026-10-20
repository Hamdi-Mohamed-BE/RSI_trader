"""FTMO fastest-funded search with a 70% average pass-rate requirement (PLAN.json). No MT5 / trading.

python run.py prepare   # build 5-year streams for every eligible FTMO-package EA (no outcomes)
python run.py freeze
python run.py dev       # stage 1: all 72 configurations on development starts -> finalists
python run.py val       # stage 2: finalists on validation starts -> choice
python run.py oos       # stage 3: choice + finalists once on the (previously inspected) OOS starts
"""
import bisect, copy, hashlib, importlib.util, json, math, os, statistics, sys, time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

R = Path(__file__).resolve().parent; B = R.parent; Z = ZoneInfo('Europe/Prague')
OLDER = B / 'FTMO Prop Ready Older History 2026-10-20'; DIAL = B / 'FTMO Dial Study 2026-10-20'; FASTER = B / 'FTMO Faster Portfolio Screen 2026-10-16'
PACKAGE = B / '_00 Live profiles/Packages/FTMO/PACKAGE.json'
PLAN = json.loads((R / 'PLAN.json').read_text(encoding='utf-8'))
CAPS = PLAN['menu']['risk_caps_usd']
COSTS = ['recorded_exness', 'fixed_cost_stress']
CORE = ['nasdaq-5m-candle-momentum', 'usdjpy-london-open-momentum', 'us100-month-end-flow', 'xau-rsi-vwap']
ORBS = ['us100-h1-orb-13utc', 'us100-orb-new-york-m30', 'us100-selective-orb-v3', 'xau-orb-new-york-m30', 'xau-orb-london-ny-overlap-m30']
PR9 = CORE + ORBS
WINDOWS = {'dev': (date(2021, 10, 7), date(2023, 10, 6)), 'val': (date(2023, 10, 6), date(2024, 10, 6)), 'oos': (date(2024, 10, 6), date(2026, 10, 6))}


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def midnight(x): return datetime.combine(x, datetime.min.time(), tzinfo=Z).timestamp()
def load(name, path):
    s = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


def baskets(eligible):
    fs = json.loads((FASTER / 'PLAN.json').read_text(encoding='utf-8-sig'))['baskets']
    out = {k: v for k, v in fs.items()}
    out['ALL12'] = CORE + ['gold-overnight-value-area', 'ema3', 'xau-trend-progression'] + ORBS
    out['FTMO_ALL'] = list(eligible)
    out['PR9_PLUS_GOLDVA'] = PR9 + ['gold-overnight-value-area']
    out['PR9_PLUS_DMC'] = PR9 + ['dmc-current-xau', 'dmc-fresh-reaction-us100']
    out['PR9_PLUS_NASDAQ_OVERNIGHT'] = PR9 + ['nasdaq-overnight']
    out['ORBS5'] = list(ORBS)
    return {k: v for k, v in out.items() if all(x in eligible for x in v)}, {k: v for k, v in out.items() if not all(x in eligible for x in v)}


def prepare():
    pr = load('older_prepare', OLDER / 'prepare.py')
    order = [e['slug'] for e in json.loads(PACKAGE.read_text(encoding='utf-8-sig'))['entries'] if e['slug'] != '3-way-gold']
    pr.SLUGS = order
    src, lookup, hashes = pr.load_sources()
    begin, end = midnight(date(2021, 10, 7)), midnight(date(2026, 10, 6))
    cands, eligible, excluded = [], [], {}
    for slug in order:
        try:
            c = pr.candidates(src[slug], lookup, slug, begin, end); cands += c; eligible.append(slug)
        except AssertionError as exc:
            excluded[slug] = f'model assertion failed: {exc}'
    excluded['3-way-gold'] = 'overlapping module lifecycles unsupported (Faster Screen rule)'
    data = dict(candidates=cands, year_begin_epoch=begin, year_end_exclusive_epoch=end, window=['2021-10-07', '2026-10-06'], eligible=eligible)
    (R / 'INPUTS-5y.json').write_text(json.dumps(data, separators=(',', ':')), encoding='utf-8')
    ok, dropped = baskets(eligible)
    (R / 'ELIGIBILITY.json').write_text(json.dumps(dict(eligible=eligible, excluded=excluded, baskets=ok, baskets_dropped_missing_ea=dropped,
                                                        per_ea={s: sum(c['ea'] == s for c in cands) for s in eligible}, source_hashes=hashes), indent=1), encoding='utf-8')
    print('eligible', len(eligible), eligible); print('excluded', excluded); print('baskets', len(ok), 'dropped', list(dropped))


def freeze():
    files = [R / 'PLAN.json', Path(__file__), R / 'INPUTS-5y.json', R / 'ELIGIBILITY.json', OLDER / 'prepare.py', DIAL / 'run.py', FASTER / 'core_engine.py', FASTER / 'PLAN.json']
    (R / 'FROZEN.json').write_text(json.dumps(dict(frozen_at=datetime.now(Z).isoformat(), files={str(f): sha(f) for f in files}), indent=1), encoding='utf-8')
    print('frozen', len(files))


def check_frozen():
    for p, h in json.loads((R / 'FROZEN.json').read_text(encoding='utf-8'))['files'].items():
        assert sha(p) == h, f'changed after freeze: {p}'


def starts(window):
    a, b = WINDOWS[window]; out = []; x = a
    while x < b:
        if x.weekday() < 5 and x + timedelta(days=180) <= b:
            out.append(dict(date=x.isoformat(), epoch=midnight(x), horizon_date=(x + timedelta(days=180)).isoformat(), horizon_epoch=midnight(x + timedelta(days=180))))
        x += timedelta(days=1)
    return out


G = {}


def init_worker():
    d = load('dial', DIAL / 'run.py'); e = d.e
    data = json.loads((R / 'INPUTS-5y.json').read_text(encoding='utf-8'))
    plan = copy.deepcopy(e.read(FASTER / 'PLAN.json'))
    plan['history'] = dict(plan['history'], start_prague=data['window'][0], end_exclusive_prague=data['window'][1])
    order = [x['slug'] for x in json.loads(PACKAGE.read_text(encoding='utf-8-sig'))['entries'] if x['slug'] in data['eligible']]
    plan['candidate_priority'] = order
    plan['baskets'] = json.loads((R / 'ELIGIBILITY.json').read_text(encoding='utf-8'))['baskets']
    events = e.master_events(plan, data)
    G.update(d=d, e=e, plan=plan, events=events, epochs=[x[0] for x in events])


def one(task):
    basket, cap, cost, window = task
    d, plan, events, epochs = G['d'], G['plan'], G['events'], G['epochs']
    d.BASKET = basket
    rows = []
    for s in starts(window):
        w = events[bisect.bisect_left(epochs, s['epoch']):bisect.bisect_left(epochs, s['horizon_epoch'])]
        t = d.replay(plan, s, cost, 'next_prague_midnight', w, [(-1e9, cap)])
        both = t['total_elapsed_to_both']['inclusive_prague_days'] if t['total_elapsed_to_both'] else None
        acc = t.get('access_5bd_illustration_epoch')
        fund = None if not acc else (datetime.fromtimestamp(acc, Z).date() - datetime.fromtimestamp(t['start_epoch'], Z).date()).days + 1
        rows.append(dict(both=both, funded=fund, breach=t['outcome'].startswith('failed'), trades=len(t['trades']), eqdd=t['max_sampled_equity_drawdown_cash'],
                         day=t['max_daily_sampled_equity_loss'], buffer=t['counts'].get('soft_total_buffer9200', 0) > 0,
                         pass_date=None if not t['both_pass_epoch'] else datetime.fromtimestamp(t['both_pass_epoch'], Z).date().isoformat()))
    n = len(rows); passed = [r for r in rows if r['both'] and not r['breach']]
    active = [(r['both'] or 180) for r in rows]
    return dict(basket=basket, cap=cap, cost=cost, window=window, starts=n, pass_share=round(len(passed) / n, 4) if n else None,
                breaches=sum(r['breach'] for r in rows), median_days_both=statistics.median([r['both'] for r in passed]) if passed else None,
                median_days_funded=statistics.median([r['funded'] for r in passed]) if passed else None,
                within={str(k): round(sum(1 for r in passed if r['both'] <= k) / n, 4) for k in (60, 90, 120)},
                buffer_share=round(sum(r['buffer'] for r in rows) / n, 4), eqdd_max=round(max(r['eqdd'] for r in rows), 1), day_max=round(max(r['day'] for r in rows), 1),
                median_trades=statistics.median(r['trades'] for r in rows),
                median_trades_per_month=round(statistics.median(r['trades'] / a * 30.4375 for r, a in zip(rows, active)), 2),
                median_trades_per_weekday=round(statistics.median(r['trades'] / max(1, a * 5 / 7) for r, a in zip(rows, active)), 3),
                distinct_pass_dates=len({r['pass_date'] for r in passed}))


def combine(results):
    by = {}
    for r in results:
        by.setdefault((r['basket'], r['cap'], r['window']), {})[r['cost']] = r
    out = []
    for (bk, cap, win), v in by.items():
        a, b = v['recorded_exness'], v['fixed_cost_stress']
        fund = [x['median_days_funded'] for x in (a, b) if x['median_days_funded'] is not None]
        out.append(dict(basket=bk, cap=cap, window=win, eas=len(G_BASKETS[bk]), avg_pass=round((a['pass_share'] + b['pass_share']) / 2, 4),
                        pass_recorded=a['pass_share'], pass_stress=b['pass_share'], breaches=a['breaches'] + b['breaches'],
                        avg_median_funded=round(sum(fund) / len(fund), 1) if len(fund) == 2 else None,
                        within_90_avg=round((a['within']['90'] + b['within']['90']) / 2, 4), within_120_avg=round((a['within']['120'] + b['within']['120']) / 2, 4),
                        buffer_share_avg=round((a['buffer_share'] + b['buffer_share']) / 2, 4), eqdd_max=max(a['eqdd_max'], b['eqdd_max']), day_max=max(a['day_max'], b['day_max']),
                        median_trades_per_month=a['median_trades_per_month'], median_trades_per_weekday=a['median_trades_per_weekday'],
                        distinct_pass_dates=min(a['distinct_pass_dates'], b['distinct_pass_dates']), starts=a['starts'], detail=v))
    return out


def run_stage(tasks):
    with ProcessPoolExecutor(max_workers=max(1, (os.cpu_count() or 2) - 1), initializer=init_worker) as ex:
        return list(ex.map(one, tasks, chunksize=1))


G_BASKETS = json.loads((R / 'ELIGIBILITY.json').read_text(encoding='utf-8'))['baskets'] if (R / 'ELIGIBILITY.json').exists() else {}


def key(r):
    return (r['avg_median_funded'] if r['avg_median_funded'] is not None else 1e9, -r['avg_pass'], r['eas'], r['cap'])


def dev():
    check_frozen(); began = time.time()
    tasks = [(bk, cap, c, 'dev') for bk in G_BASKETS for cap in CAPS for c in COSTS]
    res = combine(run_stage(tasks))
    eligible = sorted([r for r in res if r['breaches'] == 0 and r['avg_pass'] >= .70], key=key)
    if eligible:
        finalists, mode = eligible[:5], 'eligible'
    else:
        finalists, mode = sorted(res, key=lambda r: (-r['avg_pass'], key(r)))[:5], 'NO_CONFIGURATION_REACHED_70PCT'
    (R / 'DEV.json').write_text(json.dumps(dict(mode=mode, starts=len(starts('dev')), seconds=round(time.time() - began), finalists=[(f['basket'], f['cap']) for f in finalists],
                                                eligible_count=len(eligible), results=sorted(res, key=lambda r: (-r['avg_pass'], key(r)))), indent=1), encoding='utf-8')
    print(mode, 'eligible', len(eligible), 'seconds', round(time.time() - began))
    for r in sorted(res, key=lambda r: (-r['avg_pass'], key(r)))[:15]:
        print(f"{r['basket']:34} ${r['cap']:<4} pass {r['avg_pass']:.3f} (rec {r['pass_recorded']:.3f} / str {r['pass_stress']:.3f}) funded {r['avg_median_funded']} breaches {r['breaches']} buf {r['buffer_share_avg']:.2f} eqdd {r['eqdd_max']}")


def val():
    check_frozen(); devr = json.loads((R / 'DEV.json').read_text(encoding='utf-8'))
    tasks = [(bk, cap, c, 'val') for bk, cap in devr['finalists'] for c in COSTS]
    res = combine(run_stage(tasks))
    ok = sorted([r for r in res if r['breaches'] == 0 and r['avg_pass'] >= .70], key=key)
    choice = ok[0] if ok else max(res, key=lambda r: (r['avg_pass'], -key(r)[0]))
    (R / 'VAL.json').write_text(json.dumps(dict(choice=(choice['basket'], choice['cap']), choice_meets_70=bool(ok), results=res), indent=1), encoding='utf-8')
    for r in res:
        print(f"{r['basket']:34} ${r['cap']:<4} val pass {r['avg_pass']:.3f} funded {r['avg_median_funded']} breaches {r['breaches']}")
    print('CHOICE', choice['basket'], choice['cap'], 'meets 70%:', bool(ok))


def oos():
    check_frozen(); devr = json.loads((R / 'DEV.json').read_text(encoding='utf-8')); v = json.loads((R / 'VAL.json').read_text(encoding='utf-8'))
    tasks = [(bk, cap, c, 'oos') for bk, cap in devr['finalists'] for c in COSTS]
    res = combine(run_stage(tasks))
    (R / 'OOS.json').write_text(json.dumps(dict(choice=v['choice'], results=res), indent=1), encoding='utf-8')
    for r in res:
        tag = '  <= CHOICE' if [r['basket'], r['cap']] == list(v['choice']) else ''
        print(f"{r['basket']:34} ${r['cap']:<4} OOS pass {r['avg_pass']:.3f} funded {r['avg_median_funded']} breaches {r['breaches']}{tag}")


if __name__ == '__main__':
    {'prepare': prepare, 'freeze': freeze, 'dev': dev, 'val': val, 'oos': oos}[sys.argv[1]]()
