"""Metrics, gate, controls and equity graph for the pairs-trading raw study.
Run from AAA EAs/EA store:  uv run --with matplotlib python "<study>/analyse.py"   -> RESULTS.md / RESULTS.json / equity.png"""
import gzip, importlib.util, json, math, re, statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent; PKG = ROOT.parent
CFG = json.loads((ROOT / 'run-config.json').read_text(encoding='utf-8')); PAIRS = CFG['pairs']; SYM = CFG['symbol_of']
LABEL = {k: v['label'] for g in ('variants', 'controls', 'sensitivity') for k, v in CFG[g].items()}
def load_mod(name, path):
    s = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
rob = load_mod('rob', PKG.parent / 'Calyx Research Pipeline' / 'robustness.py')


def load(key, period):
    d = ROOT / 'native' / f'nw-{SYM[key]}-{key}-{period}'
    if not (d / 'run.json').exists(): return None
    meta = json.loads((d / 'run.json').read_text()); j = gzip.decompress((d / 'journal.txt.gz').read_bytes()).decode('utf-8', 'ignore')
    pt = {}
    for m in re.finditer(r'PAIR_TRADE open=(\d+) close=(\d+) pos=(-?\d) side=(-?\d) entry_z=(-?[\d.]+) exit_z=(-?[\d.]+) reason=(\w+) net=(-?[\d.]+)', j):
        pt[(int(m[1]), int(m[2]))] = dict(open=int(m[1]), close=int(m[2]), reason=m[7], net=float(m[8]))
    days = {}
    for m in re.finditer(r'PAIR_DAY epoch=(\d+) equity=([\d.]+) z=(-?[\d.]+) beta=(-?[\d.]+) sd=([\d.]+) pos=(-?\d)', j): days[int(m[1])] = float(m[2])
    s = re.findall(r'PAIR_SUMMARY ([^\r\n]*)', j); cnt = {k: int(x) for k, x in (kv.split('=') for kv in s[-1].split())} if s else None
    legs = json.loads(gzip.decompress((d / 'trades.json.gz').read_bytes()))
    # A pair still open at the end of the test is closed by the tester ('end of test') and not logged by the EA:
    # book it as a final marked-to-market pair trade so pair-level totals reconcile with native cash.
    eot = [t for t in legs if 'end of test' in (t.get('exit_comment') or '').lower()]
    if eot:
        ts = lambda s: datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp()  # noqa: E731
        o, c = int(min(ts(t['open_time']) for t in eot)), int(max(ts(t['close_time']) for t in eot))
        pt[(o, c)] = dict(open=o, close=c, reason='end_of_test', net=round(sum(t['net_profit'] for t in eot), 2))
    total = round(sum(t['net'] for t in pt.values()), 2)
    assert abs(total - meta['metrics']['net_profit']) < 1.0, ('pair trades do not reconcile with native net', key, period, total, meta['metrics']['net_profit'])
    return dict(meta=meta, trades=sorted(pt.values(), key=lambda t: t['close']), days=dict(sorted(days.items())), counters=cnt, legs=legs)


def streaks(p):
    runs = {True: [], False: []}; cur, n = None, 0
    for x in p:
        s = x > 0
        if s == cur: n += 1
        else:
            if cur is not None: runs[cur].append(n)
            cur, n = s, 1
    if cur is not None: runs[cur].append(n)
    a = lambda v: (round(sum(v) / len(v), 2), max(v)) if v else (0, 0)  # noqa: E731
    return a(runs[True]), a(runs[False])


def metrics(r):
    t = r['trades']; p = [x['net'] for x in t]; ks = list(r['days']); eq = [r['days'][k] for k in ks]
    if len(eq) < 3: return None
    rets = [eq[i] / eq[i - 1] - 1 for i in range(1, len(eq))]; sd = statistics.stdev(rets) if len(rets) > 2 else 0
    per_year = len(ks) / max((ks[-1] - ks[0]) / 86400 / 365.25, 0.1)
    bal = peak = 100000.; cdd = 0.
    for x in p: bal += x; peak = max(peak, bal); cdd = max(cdd, (peak - bal) / peak)
    gp, gl = sum(x for x in p if x > 0), -sum(x for x in p if x < 0); (aw, mw), (al, ml) = streaks(p)
    months = defaultdict(float)
    for x in t: months[datetime.fromtimestamp(x['close'], timezone.utc).strftime('%Y-%m')] += x['net']
    span_m = (ks[-1] - ks[0]) / 86400 / 30.4375
    return dict(trades=len(p), per_month=round(len(p) / max(span_m, 0.1), 2), per_day=round(len(p) / len(ks), 3), return_pct=r['meta']['metrics']['return_pct'],
                pf=round(gp / gl, 2) if gl else None, win=round(100 * sum(x > 0 for x in p) / len(p), 1) if p else None,
                sharpe=round(statistics.fmean(rets) / sd * math.sqrt(per_year), 2) if sd > 0 else None, eq_dd=r['meta']['metrics'].get('max_drawdown_pct'),
                closed_dd=round(100 * cdd, 2), win_streak=f'{aw} ({mw})', loss_streak=f'{al} ({ml})', stops=sum(x['reason'] == 'stop' for x in t),
                avg_hold_d=round(statistics.fmean((x['close'] - x['open']) / 86400 for x in t), 1) if t else None,
                mean_R=round(statistics.fmean(x / 1000 for x in p), 3) if p else None,
                consistency=round(100 * sum(v > 0 for v in months.values()) / len(months), 1) if months else None,
                swap=round(sum(x.get('swap', 0) for x in r['legs']), 2))


HDR = ('| Pair | Window | Trades | / month | / day | Return | PF | Win % | Sharpe | Equity DD | Closed DD | Win streak avg (max) | Loss streak avg (max) | Stops | Avg hold d | Consistency | Swap $ |\n'
       '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---:|---:|---:|---:|')
f = lambda x, s='': '—' if x is None else f'{x}{s}'  # noqa: E731
def line(name, w, m):
    return (f"| {name} | {w} | {m['trades']} | {m['per_month']} | {m['per_day']} | {m['return_pct']:+.2f}% | {f(m['pf'])} | {f(m['win'])} | {f(m['sharpe'])} | {f(m['eq_dd'], '%')} | "
            f"{m['closed_dd']}% | {m['win_streak']} | {m['loss_streak']} | {m['stops']} | {f(m['avg_hold_d'])} | {f(m['consistency'], '%')} | {m['swap']:+,.0f} |")


out = dict(fade={}, five={}, gate={}, dependence={}, m4={})
md = ['# Pairs trading (z-score fade) — raw results (generated)', '', 'Native MT5 Model 1 screen (Model 4 confirmation for gate passers). $100k, 1% risk to the 3.5σ stop. '
      'PF / win / streaks per pair trade (both legs). Mean R = net / $1,000.', '', '## FADE (the clip\'s rule) — separate windows', '', HDR]
for pid, (a, b) in PAIRS.items():
    for per in ('6m', '1y', '3y', '5y'):
        r = load(f'{pid}_FADE', per)
        if not r or not r['trades'] and not r['days']: continue
        m = metrics(r)
        if not m: continue
        out['fade'][f'{pid}|{per}'] = m; md.append(line(f'{pid} {a}/{b}', per, m))
        if per in ('3y', '5y'): out['dependence'][f'{pid}|{per}'] = rob.dependence([dict(net_profit=x['net'], close_time=datetime.fromtimestamp(x['close'], timezone.utc).isoformat()) for x in r['trades']])
md += ['', '## Controls and sensitivities — 5 years, Model 1 (like for like)', '',
       '| Pair | FADE PF / return | MOM PF / return | Random mean PF / return | 20d | 120d | entry 2.5σ | stop 4σ | no stop | OLS β |', '|---|---|---|---|---|---|---|---|---|---|']
for pid, (a, b) in PAIRS.items():
    row = {}
    for v in ('FADE', 'MOM', 'RND1', 'RND2', 'RND3', 'S_N20', 'S_N120', 'S_E25', 'S_ST4', 'S_NOSTOP', 'S_BETA'):
        r = load(f'{pid}_{v}', '5y'); m = metrics(r) if r else None
        if m: row[v] = m
    out['five'][pid] = row
    rnd = [row[k] for k in ('RND1', 'RND2', 'RND3') if k in row]
    rpf = statistics.fmean(x['pf'] or 0 for x in rnd) if rnd else None; rret = statistics.fmean(x['return_pct'] for x in rnd) if rnd else None
    cell = lambda k: '—' if k not in row else f"{f(row[k]['pf'])} / {row[k]['return_pct']:+.1f}%"  # noqa: E731
    md.append(f"| {pid} {a}/{b} | {cell('FADE')} | {cell('MOM')} | {f(rpf and round(rpf, 2))} / {f(rret and round(rret, 1), '%')} | {cell('S_N20')} | {cell('S_N120')} | {cell('S_E25')} | {cell('S_ST4')} | {cell('S_NOSTOP')} | {cell('S_BETA')} |")
    fa3, fa5 = out['fade'].get(f'{pid}|3y'), out['fade'].get(f'{pid}|5y')
    if fa3 and fa5 and 'MOM' in row and rnd:
        g = dict(pos=fa3['return_pct'] > 0 and fa5['return_pct'] > 0, pf=(fa3['pf'] or 0) >= 1.15 and (fa5['pf'] or 0) >= 1.15, n=fa5['trades'] >= 30,
                 mom=(fa5['pf'] or 0) > (row['MOM']['pf'] or 0), rnd=(fa5['pf'] or 0) > rpf,
                 dep=all(out['dependence'].get(f'{pid}|{p}', {}).get('verdict') == 'PASS' for p in ('3y', '5y')))
        out['gate'][pid] = dict(checks=g, passed=all(g.values()))
yn = lambda x: 'yes' if x else '**no**'  # noqa: E731
md += ['', '## Raw gate (Model 1)', '', '| Pair | Positive 3y & 5y | PF ≥ 1.15 3y & 5y | ≥ 30 trades | PF > momentum | PF > random mean | Best day / trade | Verdict |', '|---|---|---|---|---|---|---|---|']
for pid, g in out['gate'].items():
    c = g['checks']; md.append(f"| {pid} {'/'.join(PAIRS[pid])} | {yn(c['pos'])} | {yn(c['pf'])} | {yn(c['n'])} | {yn(c['mom'])} | {yn(c['rnd'])} | {yn(c['dep'])} | **{'PASS' if g['passed'] else 'FAIL'}** |")
for pid in PAIRS:
    for per in ('3y_m4', '5y_m4'):
        r = load(f'{pid}_FADE', per)
        if r: out['m4'][f'{pid}|{per}'] = metrics(r)
if out['m4']:
    md += ['', '## Model 4 confirmation', '', HDR] + [line(k.split('|')[0], k.split('|')[1], m) for k, m in out['m4'].items()]
md += ['', '## Best-day dependence (FADE, pair trades)', ''] + [f"- {k}: total ${d['total']:+,.0f}; without best day ${d.get('without_best_day', 0):+,.0f}; without best trade ${d.get('without_best_trade', 0):+,.0f}; without 5 best days ${d.get('without_top5_days', 0):+,.0f} → {d['verdict']}" for k, d in out['dependence'].items() if d.get('verdict') != 'NO_TRADES']
(ROOT / 'RESULTS.md').write_text('\n'.join(md) + '\n', encoding='utf-8'); (ROOT / 'RESULTS.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8'); print('\n'.join(md))

import matplotlib; matplotlib.use('Agg')  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
fig, ax = plt.subplots(figsize=(12, 6.5))
for pid, (a, b) in PAIRS.items():
    r = load(f'{pid}_FADE', '5y')
    if not r or not r['days']: continue
    ks = list(r['days']); ax.plot([datetime.fromtimestamp(k, timezone.utc) for k in ks], [100 * r['days'][k] / 100000 for k in ks], label=f'{pid} {a}/{b}', lw=1.6 if out['gate'].get(pid, {}).get('passed') else 1.0)
ax.axhline(100, color='k', lw=.6, ls='--'); ax.legend(fontsize=8, ncol=3); ax.set_ylabel('equity (start = 100)')
ax.set_title('Pairs trading z-score fade (2σ entry, exit at 0, 3.5σ stop) · native MT5 Model 1 · 5 years · daily equity per pair', fontsize=10)
fig.tight_layout(); fig.savefig(ROOT / 'equity.png', dpi=130)
