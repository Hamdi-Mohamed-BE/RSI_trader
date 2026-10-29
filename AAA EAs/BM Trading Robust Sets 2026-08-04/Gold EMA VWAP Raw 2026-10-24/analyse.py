"""Gold EMA + VWAP raw study: metrics, gate, windows, controls, sensitivities, dependence and balance graph.
Run from AAA EAs/EA store:  uv run --with matplotlib python "<study>/analyse.py"   -> RESULTS.md / RESULTS.json / balance.png"""
import gzip, importlib.util, json, math, re, statistics
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent; PKG = ROOT.parent
CFG = json.loads((ROOT / 'run-config.json').read_text(encoding='utf-8'))
END = datetime.strptime(CFG['end_date'], '%Y.%m.%d'); DEP, RISK = 10000.0, 0.01
MAIN, CONTROLS, SENS = list(CFG['variants']), list(CFG['controls']), list(CFG['sensitivity'])
LABEL = {k: v['label'] for g in ('variants', 'controls', 'sensitivity') for k, v in CFG[g].items()}
def load_mod(name, path):
    s = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
rob = load_mod('rob', PKG.parent / 'Calyx Research Pipeline' / 'robustness.py')
split = load_mod('ds', PKG.parent / 'Calyx Research Pipeline' / 'data_split.py').research_split('2021-10-24', '2026-10-24')
WINDOWS = {'Dev 2021-23': (split['development']['start'], split['development']['end_exclusive']), 'Val 2023-24': (split['validation']['start'], split['validation']['end_exclusive']),
           'OOS 2024-26': (split['oos']['start'], split['oos']['end_exclusive']), '5 years': ('2021-10-24', '2026-10-24')}


def load(v, period):
    d = ROOT / 'native' / f'nw-XAUUSD-{v}-{period}'
    if not (d / 'run.json').exists(): return None, [], None
    meta = json.loads((d / 'run.json').read_text()); trades = json.loads(gzip.decompress((d / 'trades.json.gz').read_bytes()))
    for t in trades: t['open'] = datetime.fromisoformat(t['open_time']); t['close'] = datetime.fromisoformat(t['close_time'])
    trades.sort(key=lambda t: t['close'])
    j = gzip.decompress((d / 'journal.txt.gz').read_bytes()).decode('utf-8', 'ignore'); m = re.findall(r'GEV_SUMMARY ([^\r\n]*)', j)
    return meta, trades, ({k: int(x) for k, x in (kv.split('=') for kv in m[-1].split())} if m else None)


def streaks(p):
    runs = {True: [], False: []}; cur, n = None, 0
    for x in p:
        s = x > 0
        if s == cur: n += 1
        else:
            if cur is not None: runs[cur].append(n)
            cur, n = s, 1
    if cur is not None: runs[cur].append(n)
    avg = lambda v: round(sum(v) / len(v), 2) if v else 0.0  # noqa: E731
    return avg(runs[True]), avg(runs[False]), max(runs[True], default=0), max(runs[False], default=0)


def stats(trades, start, end, meta=None):
    ts = [t for t in trades if start <= t['open'] < end]; p = [t['net_profit'] for t in ts]
    days = (end - start).days; weekdays = [start + timedelta(days=i) for i in range(days) if (start + timedelta(days=i)).weekday() < 5]
    gp, gl = sum(x for x in p if x > 0), -sum(x for x in p if x < 0)
    bal0 = DEP + sum(t['net_profit'] for t in trades if t['close'] < start); bal, peak, bdd, R = bal0, bal0, 0.0, []
    for t in ts: R.append(t['net_profit'] / (RISK * bal)); bal += t['net_profit']; peak = max(peak, bal); bdd = max(bdd, (peak - bal) / peak * 100)
    daily = defaultdict(float)
    for t in ts: daily[t['close'].date()] += t['net_profit']
    eq, rets = bal0, []
    for d in weekdays: r = daily.get(d.date(), 0.0) / eq; rets.append(r); eq += daily.get(d.date(), 0.0)
    mean = sum(rets) / len(rets) if rets else 0; sd = math.sqrt(sum((r - mean) ** 2 for r in rets) / len(rets)) if rets else 0
    months = defaultdict(float)
    for t in ts: months[(t['close'].year, t['close'].month)] += t['net_profit']
    allm = set(); d = start
    while d < end: allm.add((d.year, d.month)); d += timedelta(days=28)
    aw, al, mw, ml = streaks(p); m = (meta or {}).get('metrics', {})
    return dict(trades=len(p), per_month=round(len(p) / (days / 30.4375), 2), per_day=round(len(p) / max(1, len(weekdays)), 3),
                ret=round(sum(p) / bal0 * 100, 2), pf=round(gp / gl, 2) if gl else None, win=round(100 * sum(x > 0 for x in p) / len(p), 1) if p else None,
                consistency=round(100 * sum(months.get(k, 0) > 0 for k in allm) / len(allm), 1) if allm else None,
                avg_w=aw, avg_l=al, max_w=mw, max_l=ml, sharpe=round(mean / sd * math.sqrt(252), 2) if sd > 0 and len(p) >= 10 else None,
                bal_dd=round(bdd, 2), eq_dd=m.get('equity_dd_relative_pct') or m.get('max_drawdown_pct'), mean_R=round(sum(R) / len(R), 3) if R else None,
                net=round(sum(p), 2), costs=round(sum(t['total_costs'] for t in ts), 2))


def native_eqdd(v, period):
    d = ROOT / 'native' / f'nw-XAUUSD-{v}-{period}'; f = next(iter(d.glob('*.htm.gz')), None)
    if not f: return None
    txt = gzip.decompress(f.read_bytes()).decode('utf-16', errors='ignore')
    if 'Equity Drawdown' not in txt: txt = gzip.decompress(f.read_bytes()).decode('utf-8', errors='ignore')
    m = re.search(r'Equity Drawdown Relative:.*?<b>([\d.,]+)%', txt, re.S)
    return float(m[1].replace(',', '')) if m else None


fmt = lambda x, s='': '—' if x is None else f'{x}{s}'  # noqa: E731
HDR = ('| Version | Window | Trades | /month | /day | Return | PF | Win % | Consistency | Avg win / loss streak (max) | Sharpe | Bal DD | Eq DD (relative) | Mean R |\n'
       '|---|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|')
def line(name, w, r):
    return (f"| {name} | {w} | {r['trades']} | {r['per_month']} | {r['per_day']} | {r['ret']:+.2f}% | {fmt(r['pf'])} | {fmt(r['win'])} | {fmt(r['consistency'], '%')} | "
            f"{r['avg_w']} / {r['avg_l']} ({r['max_w']} / {r['max_l']}) | {fmt(r['sharpe'])} | {r['bal_dd']}% | {fmt(r['eq_dd'], '%')} | {fmt(r['mean_R'])} |")


out = dict(native={}, windows={}, counters={}, dependence={}, gate={})
md = ['# Gold EMA + VWAP — raw results (generated)', '',
      'Native MT5 Model 4, 150 ms, $10k, 1% risk rounded up, XAUUSD (A on M15, B on M5), end 2026-10-24 exclusive. Consistency = share of profitable months;',
      'Sharpe = annualised daily; Bal DD = closed balance; Eq DD = native "Equity Drawdown Relative". Mean R = net / (1% of balance).', '',
      '## Main versions — separate native runs per period', '', HDR]
for v in MAIN:
    for per, s in CFG['periods'].items():
        meta, trades, cnt = load(v, per)
        if meta is None: continue
        r = stats(trades, datetime.strptime(s, '%Y.%m.%d'), END, meta); r['eq_dd'] = native_eqdd(v, per); out['native'][f'{v}|{per}'] = r
        if per in ('3y', '5y'): out['dependence'][f'{v}|{per}'] = rob.dependence(trades)
        md.append(line(f'**{v}**', per, r))
md += ['', '## Windows inside the 5-year runs (by trade open date)', '', HDR]
for v in MAIN + CONTROLS + SENS:
    meta, trades, cnt = load(v, '5y')
    if meta is None: continue
    out['counters'][v] = cnt
    for w, (a, b) in WINDOWS.items():
        r = stats(trades, datetime.fromisoformat(a), datetime.fromisoformat(b), meta if w == '5 years' else None)
        if w == '5 years': r['eq_dd'] = native_eqdd(v, '5y')
        out['windows'].setdefault(v, {})[w] = r
        if w == '5 years' or v in MAIN: md.append(line(v, w, r))
md.append('')
for v in MAIN:
    r3, r5 = out['native'].get(f'{v}|3y'), out['native'].get(f'{v}|5y')
    if not (r3 and r5): continue
    rnd = [out['windows'][k]['5 years']['mean_R'] or 0 for k in (f'RND1_{v}', f'RND2_{v}', f'RND3_{v}') if k in out['windows']]
    me = out['windows'][v]['5 years']['mean_R'] or -9
    pure = out['windows'].get('A15_NOFILT', {}).get('5 years') if v == 'A15' else None
    dep = [out['dependence'].get(f'{v}|3y', {}), out['dependence'].get(f'{v}|5y', {})]
    g = dict(positive_3y_5y=r3['ret'] > 0 and r5['ret'] > 0, pf_3y_5y=(r3['pf'] or 0) >= 1.15 and (r5['pf'] or 0) >= 1.15, trades=r5['trades'] >= 30,
             beats_random=bool(rnd) and me > statistics.fmean(rnd), beats_pure_cross=(pure is None) or me > (pure['mean_R'] or -9),
             best_day_trade=all(d.get('verdict') == 'PASS' for d in dep))
    out['gate'][v] = dict(checks=g, passed=all(g.values()), random_mean_R=statistics.fmean(rnd) if rnd else None)
yn = lambda b: 'yes' if b else '**no**'  # noqa: E731
md += ['## Raw gate', '', '| Version | Positive 3y & 5y | PF ≥ 1.15 3y & 5y | ≥ 30 trades | Mean R > random direction | Mean R > pure cross (A) | Best day/trade | Verdict |', '|---|---|---|---|---|---|---|---|']
for v, g in out['gate'].items():
    c = g['checks']; md.append(f"| {v} | {yn(c['positive_3y_5y'])} | {yn(c['pf_3y_5y'])} | {yn(c['trades'])} | {yn(c['beats_random'])} | {yn(c['beats_pure_cross'])} | {yn(c['best_day_trade'])} | **{'PASS' if g['passed'] else 'FAIL'}** |")
md += ['', '## Best-day dependence (3y / 5y)', '']
for k, d in out['dependence'].items():
    if d.get('verdict') == 'NO_TRADES': continue
    md.append(f"- {k}: total ${d['total']:+,.0f}; without best day ${d.get('without_best_day', 0):+,.0f}; without best trade ${d.get('without_best_trade', 0):+,.0f}; "
              f"without 5 best days ${d.get('without_top5_days', 0):+,.0f}; without worst day ${d.get('without_worst_day', 0):+,.0f} → {d['verdict']}")
md += ['', '## Counters (5y)', '', '| Run | Bars | Signals | Entries | Busy (in position) | Stop floors | Session skips | Place fails |', '|---|---:|---:|---:|---:|---:|---:|---:|']
for k, c in out['counters'].items():
    if c: md.append(f"| {k} | {c['bars']} | {c['signals']} | {c['entries']} | {c['busy']} | {c['floors']} | {c['session_skips']} | {c['place_fails']} |")
(ROOT / 'RESULTS.md').write_text('\n'.join(md) + '\n', encoding='utf-8'); (ROOT / 'RESULTS.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8')
print('RESULTS.md written')

import matplotlib; matplotlib.use('Agg')  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
fig, axes = plt.subplots(2, 1, figsize=(12, 9), facecolor='#fcfcfb')
for ax, v in zip(axes, MAIN):
    ax.set_facecolor('#fcfcfb')
    for k, col, lw in ((v, '#2a78d6', 2.0), (f'RND1_{v}', '#eb6834', 1.0), (f'RND2_{v}', '#1baf7a', 1.0), (f'RND3_{v}', '#eda100', 1.0),
                       ('A15_NOFILT' if v == 'A15' else 'B5_NOSLOPE', '#6250d6', 1.2)):
        meta, trades, _ = load(k, '5y')
        if not trades: continue
        x, y, bal = [datetime(2021, 10, 24)], [DEP], DEP
        for t in trades: bal += t['net_profit']; x.append(t['close']); y.append(bal)
        ax.step(x, y, where='post', label=f'{k}: {LABEL[k]}', lw=lw, color=col)
    for a in (split['validation']['start'], split['oos']['start']): ax.axvline(datetime.fromisoformat(a), color='#52514e', lw=.6, ls=':')
    ax.axhline(DEP, color='#52514e', lw=.7, ls='--'); ax.legend(fontsize=7, frameon=False)
    for s in ('top', 'right'): ax.spines[s].set_visible(False)
    ax.set_title(f'XAUUSD {v} · native MT5 Model 4 · 5 years · 1% risk · closed balance (dotted: validation / OOS start)', fontsize=10, loc='left')
fig.tight_layout(); fig.savefig(ROOT / 'balance.png', dpi=130, facecolor='#fcfcfb')
