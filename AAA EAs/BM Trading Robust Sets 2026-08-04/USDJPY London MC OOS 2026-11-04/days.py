"""Weekday breakdown: production (Wed-Fri) vs ALL5 (Mon-Fri) native runs, split by the entry weekday. R = net / (1% of the closed
balance before the trade). Parity: ALL5's Wed-Fri entries must be the production entries (same open times / sides). -> DAYS.json"""
import gzip, json, statistics, sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

H = Path(__file__).resolve().parent
sys.path.insert(0, str(H.parents[1] / 'Calyx Research Pipeline')); import robustness as rb  # noqa: E402
WIN = json.loads((H / 'PLAN.json').read_text(encoding='utf-8'))['windows']


def ledger(tag, p):
    T = sorted(json.loads(gzip.open(H / f'native/nw-USDJPY-{tag}-{p}/trades.json.gz').read()), key=lambda t: t['close_time']); bal = 1e4
    for t in T: t['r'] = t['net_profit'] / (0.01 * bal); bal += t['net_profit']; t['day'] = datetime.fromisoformat(t['open_time']).strftime('%a')
    return T


def st(T, p):
    months = (date.fromisoformat(WIN[p][1]) - date.fromisoformat(WIN[p][0])).days / 30.4375
    if not T: return dict(trades=0)
    R = [t['r'] for t in T]; gl = -sum(v for v in R if v < 0)
    stops = sum((t.get('exit_comment') or '').lower().startswith('sl') and t['r'] < -0.05 for t in T)
    return dict(trades=len(T), per_month=round(len(T) / months, 2), sum_r=round(sum(R), 2), mean_r=round(statistics.fmean(R), 4),
                pf=round(sum(v for v in R if v > 0) / gl, 3) if gl else None, win_pct=round(100 * sum(v > 0 for v in R) / len(R), 1),
                dd_r=round(rb.max_drawdown(R), 2), stop_loss_pct=round(100 * stops / len(T), 1))


out = dict(windows={}, parity={}, by_year={}, native={})
for p in ('dev', 'val', 'oos', 'all'):
    prod, all5 = ledger('PROD', p), ledger('ALL5', p)
    key = lambda t: (t['open_time'][:16], t['side'])  # noqa: E731
    wf = [t for t in all5 if t['day'] in ('Wed', 'Thu', 'Fri')]
    out['parity'][p] = dict(prod=len(prod), all5_wed_fri=len(wf), same_entries=sorted(map(key, prod)) == sorted(map(key, wf)))
    net = lambda T: round(100 * sum(t['net_profit'] for t in T) / 1e4, 2)  # noqa: E731
    out['windows'][p] = dict(PROD=dict(st(prod, p), net_pct=net(prod)), ALL5=dict(st(all5, p), net_pct=net(all5)),
                             MON=st([t for t in all5 if t['day'] == 'Mon'], p), TUE=st([t for t in all5 if t['day'] == 'Tue'], p),
                             MON_TUE=st([t for t in all5 if t['day'] in ('Mon', 'Tue')], p),
                             **{d.upper(): st([t for t in all5 if t['day'] == d], p) for d in ('Wed', 'Thu', 'Fri')})
    out['native'][p] = json.loads((H / f'native/nw-USDJPY-ALL5-{p}/run.json').read_text(encoding='utf-8'))['metrics']
A = ledger('ALL5', 'all')
for d in ('Mon', 'Tue', 'Wed', 'Thu', 'Fri'):
    g = defaultdict(float)
    for t in A:
        if t['day'] == d: g[t['close_time'][:4]] += t['r']
    out['by_year'][d] = {y: round(v, 2) for y, v in sorted(g.items())}
P = ledger('PROD', 'all'); per_year = round(len(A) / 7.83)
out['three_mc'] = {name: dict(full=rb.three_monte_carlo([t['r'] for t in T]),
                              one_year=rb.three_monte_carlo([t['r'] for t in T], horizon=round(len(T) / 7.83)))
                   for name, T in (('PROD', P), ('ALL5', A))}
(H / 'DAYS.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
print(json.dumps(out['parity']))
for p, w in out['windows'].items():
    print(p); [print('  ', k, v) for k, v in w.items()]
print(json.dumps(out['by_year']))
for n, v in out['three_mc'].items():
    f, y = v['full'], v['one_year']
    print(n, 'realDD', f['real']['max_drawdown'], 'shufp95', f['reshuffle']['max_drawdown']['p95'], 'resample red', f['resample']['red_pct'], y['resample']['red_pct'],
          'rand red', f['randomize']['both']['red_pct'], y['randomize']['both']['red_pct'], '1y total p05/p50', y['resample']['total']['p05'], y['resample']['total']['p50'])
