"""Metrics, gate, exit-reason split and balance graph for the BTC weekend value-area raw study."""
import gzip, json, math
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CFG = json.loads((ROOT / 'run-config.json').read_text())
END = datetime.strptime(CFG['end_date'], '%Y.%m.%d')
DEP = 10000.0
VARIANTS = {**{k: v['label'] for k, v in CFG['variants'].items()}, **{k: v['label'] for k, v in CFG['controls'].items()}}


def load(variant, period):
    d = ROOT / 'native' / f'nw-BTCUSD-{variant}-{period}'
    if not (d / 'run.json').exists():
        return None, []
    meta = json.loads((d / 'run.json').read_text())
    trades = json.loads(gzip.decompress((d / 'trades.json.gz').read_bytes()))
    for t in trades:
        t['open'] = datetime.fromisoformat(t['open_time']); t['close'] = datetime.fromisoformat(t['close_time'])
    trades.sort(key=lambda t: t['close'])
    return meta, trades


def streaks(p):
    runs = {True: [], False: []}; cur, n = None, 0
    for x in p:
        s = x > 0
        if x == 0:
            if cur is not None: runs[cur].append(n)
            cur, n = None, 0; continue
        if s == cur: n += 1
        else:
            if cur is not None: runs[cur].append(n)
            cur, n = s, 1
    if cur is not None: runs[cur].append(n)
    avg = lambda v: round(sum(v) / len(v), 2) if v else 0.0  # noqa: E731
    return avg(runs[True]), avg(runs[False]), max(runs[True], default=0), max(runs[False], default=0)


def stats(trades, start, end, meta=None):
    p = [t['net_profit'] for t in trades]
    days = (end - start).days
    weekdays = sum(1 for i in range(days) if (start + timedelta(days=i)).weekday() < 5)
    gp, gl = sum(x for x in p if x > 0), -sum(x for x in p if x < 0)
    bal, peak, bdd, R = DEP, DEP, 0.0, []
    for t in trades:
        R.append(t['net_profit'] / (0.01 * bal)); bal += t['net_profit']; peak = max(peak, bal); bdd = max(bdd, (peak - bal) / peak * 100)
    daily = defaultdict(float)
    for t in trades: daily[t['close'].date()] += t['net_profit']
    eq, rets = DEP, []
    for i in range(days):
        d = (start + timedelta(days=i)).date(); r = daily.get(d, 0.0) / eq; rets.append(r); eq += daily.get(d, 0.0)
    mean = sum(rets) / len(rets) if rets else 0; sd = math.sqrt(sum((r - mean) ** 2 for r in rets) / len(rets)) if rets else 0
    months = defaultdict(float)
    for t in trades: months[(t['close'].year, t['close'].month)] += t['net_profit']
    allm = set(); x = start
    while x < end: allm.add((x.year, x.month)); x += timedelta(days=28)
    allm |= set(months)
    aw, al, mw, ml = streaks(p)
    exits = defaultdict(int)
    for t in trades:
        c = (t.get('exit_comment') or '').lower()
        exits['TP' if c.startswith('tp') else 'SL' if c.startswith('sl') else 'time/other'] += 1
    m = (meta or {}).get('metrics', {})
    return dict(trades=len(p), per_month=round(len(p) / (days / 30.4375), 2), per_day=round(len(p) / max(weekdays, 1), 3),
                ret=round(sum(p) / DEP * 100, 2), pf=round(gp / gl, 2) if gl else None, win=round(100 * sum(x > 0 for x in p) / len(p), 1) if p else None,
                consistency=round(100 * sum(months.get(k, 0) > 0 for k in allm) / len(allm), 1) if allm else None,
                avg_w=aw, avg_l=al, max_w=mw, max_l=ml, sharpe=round(mean / sd * math.sqrt(365), 2) if sd > 0 and len(p) >= 10 else None,
                bal_dd=round(bdd, 2), eq_dd=m.get('max_drawdown_pct'), mean_R=round(sum(R) / len(R), 3) if R else None,
                long_n=sum(t['side'] == 'Long' for t in trades), long_net=round(sum(t['net_profit'] for t in trades if t['side'] == 'Long'), 2),
                short_n=sum(t['side'] == 'Short' for t in trades), short_net=round(sum(t['net_profit'] for t in trades if t['side'] == 'Short'), 2),
                exits=dict(exits))


rows = []
for v in VARIANTS:
    for per, s in CFG['periods'].items():
        meta, trades = load(v, per)
        if meta is None: continue
        start = datetime.strptime(s, '%Y.%m.%d')
        rows.append(dict(variant=v, period=per, **stats(trades, start, END, meta), flags=meta.get('journal_flags'), ok=meta.get('ok')))
fmt = lambda x: '—' if x is None else x  # noqa: E731
print('| Variant | Window | Trades | /month | /day | Return | PF | Win | Consist. | Streaks W/L avg (max) | Sharpe | Bal DD | Eq DD | ≈R/trade | Long n/$ | Short n/$ | Exits TP/SL/time |')
print('|---|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---|---|---|')
for r in rows:
    e = r['exits']
    print(f"| {r['variant']} | {r['period']} | {r['trades']} | {r['per_month']} | {r['per_day']} | {r['ret']:+.2f}% | {fmt(r['pf'])} | {fmt(r['win'])}% | {fmt(r['consistency'])}% | "
          f"{r['avg_w']}/{r['avg_l']} ({r['max_w']}/{r['max_l']}) | {fmt(r['sharpe'])} | {r['bal_dd']}% | {fmt(r['eq_dd'])}% | {fmt(r['mean_R'])} | "
          f"{r['long_n']} / {r['long_net']:+.0f} | {r['short_n']} / {r['short_net']:+.0f} | {e.get('TP', 0)}/{e.get('SL', 0)}/{e.get('time/other', 0)} |")

gate = {}
for v in CFG['variants']:
    g = {}
    for per in ('3y', '5y'):
        r = next((x for x in rows if x['variant'] == v and x['period'] == per), None)
        c = next((x for x in rows if x['variant'] == 'CRNG' and x['period'] == per), None)
        if not r: continue
        g[per] = dict(positive=r['ret'] > 0, pf=(r['pf'] or 0) >= 1.15, trades=r['trades'] >= 30,
                      beats_control=bool(c) and (r['pf'] or 0) > (c['pf'] or 0) and (r['mean_R'] or -9) > (c['mean_R'] or -9),
                      clean=not any((r['flags'] or {}).get(k) for k in ('init_failed', 'critical')))
    gate[v] = dict(windows=g, passed=bool(g) and all(all(x.values()) for x in g.values()))
print('\nGATE', json.dumps(gate, indent=1))
(ROOT / 'RESULTS.json').write_text(json.dumps(dict(rows=rows, gate=gate), indent=2, default=str))

import matplotlib; matplotlib.use('Agg')  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
fig, axes = plt.subplots(2, 1, figsize=(12, 8))
for ax, per in zip(axes, ('5y', '1y')):
    for v in VARIANTS:
        meta, trades = load(v, per)
        if not trades: continue
        x, y, bal = [], [], DEP
        for t in trades: bal += t['net_profit']; x.append(t['close']); y.append(bal)
        ax.step(x, y, where='post', label=f'{v}: {VARIANTS[v]}', lw=1.3)
    ax.axhline(DEP, color='grey', lw=.7, ls='--'); ax.set_title(f'BTCUSD weekend value-area limits · native MT5 Model 4 · {per} · closed balance'); ax.legend(fontsize=8)
fig.tight_layout(); fig.savefig(ROOT / 'balance.png', dpi=130)
