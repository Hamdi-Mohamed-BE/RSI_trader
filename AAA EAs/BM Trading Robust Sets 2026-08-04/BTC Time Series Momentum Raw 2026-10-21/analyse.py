"""Metrics, gate, per-year, controls and equity graph for the BTC time-series momentum raw study.
Run from AAA EAs/EA store:  uv run --with matplotlib python "<study>/analyse.py"   -> RESULTS.md / RESULTS.json / equity.png"""
import bisect, gzip, importlib.util, json, math, re, statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent; PKG = ROOT.parent
CFG = json.loads((ROOT / 'run-config.json').read_text(encoding='utf-8'))
DEP = float(CFG['deposit']); LABEL = {k: v['label'] for g in ('variants', 'controls', 'sensitivity') for k, v in CFG[g].items()}
def load_mod(name, path):
    s = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
rob = load_mod('rob', PKG.parent / 'Calyx Research Pipeline' / 'robustness.py')


def load(v, period):
    d = ROOT / 'native' / f'nw-BTCUSD-{v}-{period}'
    if not (d / 'run.json').exists(): return None
    meta = json.loads((d / 'run.json').read_text())
    trades = json.loads(gzip.decompress((d / 'trades.json.gz').read_bytes()))
    for t in trades: t['open'] = datetime.fromisoformat(t['open_time']); t['close'] = datetime.fromisoformat(t['close_time'])
    trades.sort(key=lambda t: t['close'])
    j = gzip.decompress((d / 'journal.txt.gz').read_bytes()).decode('utf-8', 'ignore')
    days = {}
    for m in re.finditer(r'TSM_DAY epoch=(\d+) equity=([\d.]+) balance=([\d.]+) ret=(-?[\d.]+) vol=([\d.]+) want=(-?\d) dir=(-?\d) frac=([\d.]+) lots=(-?[\d.]+)', j):
        days[int(m[1])] = dict(equity=float(m[2]), dir=int(m[7]), frac=float(m[8]))
    flips = sorted({int(m[1]) for m in re.finditer(r'TSM_FLIP epoch=(\d+)', j)})
    s = re.findall(r'TSM_SUMMARY ([^\r\n]*)', j); cnt = {k: int(x) for k, x in (kv.split('=') for kv in s[-1].split())} if s else None
    return dict(meta=meta, trades=trades, days=dict(sorted(days.items())), flips=flips, counters=cnt)


def metrics(run, start=None, end=None):
    days = run['days']; keys = [k for k in days if (start is None or k >= start) and (end is None or k < end)]
    if len(keys) < 3: return None
    eq = [days[k]['equity'] for k in keys]
    # first equity of the window is the value at its first daily check; returns are day-to-day equity changes
    rets = [eq[i] / eq[i - 1] - 1 for i in range(1, len(eq))]
    mu = statistics.fmean(rets); sd = statistics.stdev(rets)
    peak, dd = eq[0], 0.0
    for x in eq: peak = max(peak, x); dd = max(dd, (peak - x) / peak)
    yrs = (keys[-1] - keys[0]) / 86400 / 365.25
    ts = [t for t in run['trades'] if (start is None or t['open'].replace(tzinfo=timezone.utc).timestamp() >= start) and (end is None or t['open'].replace(tzinfo=timezone.utc).timestamp() < end)]
    p = [t['net_profit'] for t in ts]; gp, gl = sum(x for x in p if x > 0), -sum(x for x in p if x < 0)
    ep = defaultdict(float)
    for t in ts: ep[bisect.bisect_right(run['flips'], t['open'].replace(tzinfo=timezone.utc).timestamp())] += t['net_profit']
    e = list(ep.values()); egp, egl = sum(x for x in e if x > 0), -sum(x for x in e if x < 0)
    months = defaultdict(float)
    for i in range(1, len(keys)):
        dt = datetime.fromtimestamp(keys[i], timezone.utc); months[(dt.year, dt.month)] += eq[i] - eq[i - 1]
    nd = len(keys); inm = [days[k] for k in keys if days[k]['dir'] != 0]
    return dict(days=nd, return_pct=round(100 * (eq[-1] / eq[0] - 1), 2), cagr_pct=round(100 * ((eq[-1] / eq[0]) ** (1 / yrs) - 1), 2) if yrs > 0.2 else None,
                sharpe=round(mu / sd * math.sqrt(365), 2) if sd > 0 else None, max_dd_pct=round(100 * dd, 2), exposure_pct=round(100 * len(inm) / nd, 1),
                avg_frac=round(statistics.fmean(x['frac'] for x in inm), 3) if inm else 0, positions=len(p), per_month=round(len(p) / (nd / 30.4375), 2),
                per_day=round(len(p) / nd, 3), pos_pf=round(gp / gl, 2) if gl else None, pos_win=round(100 * sum(x > 0 for x in p) / len(p), 1) if p else None,
                episodes=len(e), ep_pf=round(egp / egl, 2) if egl else None, ep_win=round(100 * sum(x > 0 for x in e) / len(e), 1) if e else None,
                consistency=round(100 * sum(v > 0 for v in months.values()) / len(months), 1) if months else None,
                costs=round(sum(t['total_costs'] for t in ts), 2), net=round(sum(p), 2))


HDR = ('| Version | Window | Return | CAGR | Sharpe | Max DD | Exposure | Avg size | Positions | / month | / day | Position PF / win | Episodes | Episode PF / win | Consistency | Costs $ |\n'
       '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---|---:|---:|')
f = lambda x, s='': '—' if x is None else f'{x}{s}'  # noqa: E731
def line(name, w, m):
    return (f"| {name} | {w} | {m['return_pct']:+.2f}% | {f(m['cagr_pct'], '%')} | {f(m['sharpe'])} | {m['max_dd_pct']}% | {m['exposure_pct']}% | {m['avg_frac']} | {m['positions']} | "
            f"{m['per_month']} | {m['per_day']} | {f(m['pos_pf'])} / {f(m['pos_win'], '%')} | {m['episodes']} | {f(m['ep_pf'])} / {f(m['ep_win'], '%')} | {f(m['consistency'], '%')} | {m['costs']:+,.0f} |")


out = dict(native={}, screen={}, years={}, gate={}, dependence={})
md = ['# BTC time-series momentum + volatility targeting — raw results (generated)', '',
      'Equity-based metrics from the daily EA equity log (00:00 UTC). Sharpe = daily, √365. Exposure = share of days in a position; Avg size = notional ÷ equity when in.',
      'Positions = closed positions incl. rebalance legs; Episode = one signal period, flip to flip. Consistency = profitable months.', '',
      '## Gate runs — native MT5 Model 4, separate windows', '', HDR]
for v in ('LF', 'LS'):
    for per in ('6m', '1y', '3y', '5y'):
        r = load(v, per)
        if not r: continue
        m = metrics(r); m['native_equity_dd'] = r['meta']['metrics'].get('max_drawdown_pct'); out['native'][f'{v}|{per}'] = m
        if per in ('3y', '5y'): out['dependence'][f'{v}|{per}'] = rob.dependence(r['trades'])
        md.append(line(f'**{v}**', per, m) + f" native eq DD {m['native_equity_dd']}%")
md += ['', '## Comparison screen — native MT5 Model 1, 5 years (like for like)', '', HDR]
screen = {}
for v in ['LF', 'LS', 'BH', 'VTL', *CFG['controls'], *CFG['sensitivity']]:
    r = load(v, '5y_m1')
    if not r: continue
    screen[v] = r; m = metrics(r); out['screen'][v] = m; md.append(line(f'{v} — {LABEL[v]}', '5y', m))
rnd = [out['screen'][k] for k in ('RND1', 'RND2', 'RND3') if k in out['screen']]
rnd_sharpe = statistics.fmean(x['sharpe'] or 0 for x in rnd) if rnd else None
md += ['', f"Random-signal control mean (RND1–3, Model 1): Sharpe {rnd_sharpe:.2f}, return {statistics.fmean(x['return_pct'] for x in rnd):+.1f}%, max DD {statistics.fmean(x['max_dd_pct'] for x in rnd):.1f}%." if rnd else '']
# per calendar year (Model 1 screen, like for like)
yrs = list(range(2021, 2027))
md += ['', '## Per calendar year (Model 1 screen; 2021 from 2021-10-20, 2026 to 2026-10-20)', '', '| Version | ' + ' | '.join(str(y) for y in yrs) + ' |', '|---|' + '---|' * len(yrs)]
for v in ('LF', 'LS', 'BH', 'VTL', 'FIX'):
    if v not in screen: continue
    cells = []
    for y in yrs:
        a, b = datetime(y, 1, 1, tzinfo=timezone.utc).timestamp(), datetime(y + 1, 1, 1, tzinfo=timezone.utc).timestamp()
        m = metrics(screen[v], a, b); out['years'].setdefault(v, {})[y] = m
        cells.append('—' if not m else f"{m['return_pct']:+.1f}% (DD {m['max_dd_pct']:.0f}%)")
    md.append(f'| {v} | ' + ' | '.join(cells) + ' |')
# gate
yn = lambda b: 'yes' if b else '**no**'  # noqa: E731
md += ['', '## Raw gate', '', '| Version | Positive 3y & 5y | Episode PF ≥ 1.15 3y & 5y | ≥ 30 positions | Sharpe > always-long VT (5y, M1) | Sharpe > random mean | Best day / trade | Verdict |', '|---|---|---|---|---|---|---|---|']
for v in ('LF', 'LS'):
    a, b = out['native'].get(f'{v}|3y'), out['native'].get(f'{v}|5y'); s5 = out['screen'].get(v); vt = out['screen'].get('VTL')
    if not (a and b and s5 and vt): continue
    g = dict(pos=a['return_pct'] > 0 and b['return_pct'] > 0, pf=(a['ep_pf'] or 0) >= 1.15 and (b['ep_pf'] or 0) >= 1.15, n=b['positions'] >= 30,
             vt=(s5['sharpe'] or -9) > (vt['sharpe'] or -9), rnd=rnd_sharpe is not None and (s5['sharpe'] or -9) > rnd_sharpe,
             dep=all(out['dependence'].get(f'{v}|{p}', {}).get('verdict') == 'PASS' for p in ('3y', '5y')))
    out['gate'][v] = dict(checks=g, passed=all(g.values()))
    md.append(f"| {v} | {yn(g['pos'])} | {yn(g['pf'])} | {yn(g['n'])} | {yn(g['vt'])} | {yn(g['rnd'])} | {yn(g['dep'])} | **{'PASS' if all(g.values()) else 'FAIL'}** |")
md += ['', '## Best-day dependence (Model 4, closed positions)', '']
for k, d in out['dependence'].items():
    if d.get('verdict') in ('NO_TRADES',): continue
    md.append(f"- {k}: total ${d['total']:+,.0f}; without best day ${d.get('without_best_day', 0):+,.0f}; without best trade ${d.get('without_best_trade', 0):+,.0f}; "
              f"without 5 best days ${d.get('without_top5_days', 0):+,.0f}; without worst day ${d.get('without_worst_day', 0):+,.0f} → {d['verdict']}")
(ROOT / 'RESULTS.md').write_text('\n'.join(md) + '\n', encoding='utf-8'); (ROOT / 'RESULTS.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8')
print('\n'.join(md))

import matplotlib; matplotlib.use('Agg')  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
fig, axes = plt.subplots(2, 1, figsize=(12, 9), gridspec_kw=dict(height_ratios=[3, 1]))
for v, col, lw in (('BH', '#7f7f7f', 1.3), ('VTL', '#9467bd', 1.2), ('LF', '#1f77b4', 2.0), ('LS', '#d62728', 1.6), ('FIX', '#2ca02c', 1.1), ('RND1', '#bcbd22', .8), ('RND2', '#17becf', .8), ('RND3', '#e377c2', .8)):
    if v not in screen: continue
    ks = list(screen[v]['days']); axes[0].plot([datetime.fromtimestamp(k, timezone.utc) for k in ks], [100 * screen[v]['days'][k]['equity'] / DEP for k in ks], label=f'{v}: {LABEL[v]}', color=col, lw=lw)
axes[0].set_yscale('log'); axes[0].axhline(100, color='k', lw=.6, ls='--'); axes[0].legend(fontsize=7); axes[0].set_ylabel('equity (start = 100, log)')
axes[0].set_title('BTCUSD · time-series momentum (30-day return) + 20% vol target · native MT5 Model 1 · 5 years · daily equity', fontsize=10)
if 'LF' in screen:
    ks = list(screen['LF']['days']); axes[1].fill_between([datetime.fromtimestamp(k, timezone.utc) for k in ks], [screen['LF']['days'][k]['frac'] * (screen['LF']['days'][k]['dir'] != 0) for k in ks], step='post', color='#1f77b4', alpha=.5)
    axes[1].set_ylabel('LF size (× equity)'); axes[1].set_ylim(0, 1.05)
fig.tight_layout(); fig.savefig(ROOT / 'equity.png', dpi=130)
