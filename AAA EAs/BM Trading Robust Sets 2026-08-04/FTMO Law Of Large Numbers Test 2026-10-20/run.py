"""Part B: LLN_PF095 / LLN_ALL / EDGE_PF110 x caps 25/50/100/150 on dev, validation and OOS starts. No MT5 / trading.

python run.py freeze | run
"""
import bisect, copy, hashlib, importlib.util, json, os, statistics, sys, time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

R = Path(__file__).resolve().parent; B = R.parent; Z = ZoneInfo('Europe/Prague')
SEARCH = B / 'FTMO Fastest Funded Search 2026-10-20'; DIAL = B / 'FTMO Dial Study 2026-10-20'; FASTER = B / 'FTMO Faster Portfolio Screen 2026-10-16'
PACKAGE = B / '_00 Live profiles/Packages/FTMO/PACKAGE.json'
PLAN = json.loads((R / 'PLAN.json').read_text(encoding='utf-8'))
CAPS = PLAN['risk_caps_usd']; COSTS = ['recorded_exness', 'fixed_cost_stress']; WINDOWS = ['dev', 'val', 'oos']


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(name, path):
    s = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


S = load('search', SEARCH / 'run.py')   # starts() and window boundaries only


def freeze():
    files = [R / 'PLAN.json', Path(__file__), R / 'prepare_universe.py', R / 'INPUTS-universe.json', R / 'UNIVERSE.json', SEARCH / 'run.py', DIAL / 'run.py', FASTER / 'core_engine.py']
    (R / 'FROZEN.json').write_text(json.dumps(dict(frozen_at=datetime.now(Z).isoformat(), files={str(f): sha(f) for f in files}), indent=1), encoding='utf-8')
    print('frozen', len(files))


G = {}


def init_worker():
    d = load('dial', DIAL / 'run.py'); e = d.e
    data = json.loads((R / 'INPUTS-universe.json').read_text(encoding='utf-8'))
    uni = json.loads((R / 'UNIVERSE.json').read_text(encoding='utf-8'))
    plan = copy.deepcopy(e.read(FASTER / 'PLAN.json'))
    plan['history'] = dict(plan['history'], start_prague=data['window'][0], end_exclusive_prague=data['window'][1])
    pkg = [x['slug'] for x in json.loads(PACKAGE.read_text(encoding='utf-8-sig'))['entries'] if x['slug'] in data['eligible']]
    plan['candidate_priority'] = pkg + sorted(s for s in data['eligible'] if s not in pkg)
    plan['baskets'] = uni['baskets']
    events = e.master_events(plan, data)
    G.update(d=d, plan=plan, events=events, epochs=[x[0] for x in events])


def one(task):
    basket, cap, cost, window = task
    d = G['d']; d.BASKET = basket; rows = []
    for s in S.starts(window):
        w = G['events'][bisect.bisect_left(G['epochs'], s['epoch']):bisect.bisect_left(G['epochs'], s['horizon_epoch'])]
        t = d.replay(G['plan'], s, cost, 'next_prague_midnight', w, [(-1e9, cap)])
        both = t['total_elapsed_to_both']['inclusive_prague_days'] if t['total_elapsed_to_both'] else None
        acc = t.get('access_5bd_illustration_epoch')
        fund = None if not acc else (datetime.fromtimestamp(acc, Z).date() - datetime.fromtimestamp(t['start_epoch'], Z).date()).days + 1
        rows.append(dict(both=both, funded=fund, breach=t['outcome'].startswith('failed'), trades=len(t['trades']), eqdd=t['max_sampled_equity_drawdown_cash'],
                         day=t['max_daily_sampled_equity_loss'], buffer=t['counts'].get('soft_total_buffer9200', 0) > 0,
                         blocked=sum(v for k, v in t['counts'].items() if k.startswith(('daily_', 'aggregate', 'same_', 'soft_', 'proxy', 'entry_reconc')))))
    n = len(rows); passed = [r for r in rows if r['both'] and not r['breach']]; active = [(r['both'] or 180) for r in rows]
    return dict(basket=basket, cap=cap, cost=cost, window=window, starts=n, pass_share=round(len(passed) / n, 4),
                funded_90=round(sum(1 for r in passed if r['funded'] <= 90) / n, 4), breaches=sum(r['breach'] for r in rows),
                median_days_funded=statistics.median([r['funded'] for r in passed]) if passed else None,
                buffer_share=round(sum(r['buffer'] for r in rows) / n, 4), eqdd_max=round(max(r['eqdd'] for r in rows), 1), day_max=round(max(r['day'] for r in rows), 1),
                median_trades=statistics.median(r['trades'] for r in rows),
                median_trades_per_month=round(statistics.median(r['trades'] / a * 30.4375 for r, a in zip(rows, active)), 2),
                median_trades_per_weekday=round(statistics.median(r['trades'] / max(1, a * 5 / 7) for r, a in zip(rows, active)), 3),
                median_blocked_entries=statistics.median(r['blocked'] for r in rows))


def run():
    for p, h in json.loads((R / 'FROZEN.json').read_text(encoding='utf-8'))['files'].items():
        assert sha(p) == h, f'changed after freeze: {p}'
    baskets = json.loads((R / 'UNIVERSE.json').read_text(encoding='utf-8'))['baskets']
    tasks = [(bk, cap, c, w) for bk in baskets for cap in CAPS for c in COSTS for w in WINDOWS]
    began = time.time()
    with ProcessPoolExecutor(max_workers=max(1, (os.cpu_count() or 2) - 1), initializer=init_worker) as ex:
        res = list(ex.map(one, tasks, chunksize=1))
    (R / 'RESULTS.json').write_text(json.dumps(dict(seconds=round(time.time() - began), baskets=baskets, results=res), indent=1), encoding='utf-8')
    print('done', round(time.time() - began), 's')


if __name__ == '__main__':
    {'freeze': freeze, 'run': run}[sys.argv[1]]()
