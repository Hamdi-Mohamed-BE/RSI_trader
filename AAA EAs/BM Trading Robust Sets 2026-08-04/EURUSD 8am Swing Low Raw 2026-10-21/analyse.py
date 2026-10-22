"""Metrics, gate, windows, controls, drift profile and balance graph for the EURUSD 8am swing-low raw study.
Run from AAA EAs/EA store:  uv run --with matplotlib python "<study>/analyse.py"   -> RESULTS.md / RESULTS.json / balance.png"""
import gzip, importlib.util, json, math, re, statistics
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent; PKG = ROOT.parent
CFG = json.loads((ROOT / 'run-config.json').read_text(encoding='utf-8'))
END = datetime.strptime(CFG['end_date'], '%Y.%m.%d')
DEP, RISK = 10000.0, float(CFG['common_inputs']['InpRiskPercent']) / 100
MAIN, CONTROLS, SENS = list(CFG['variants']), list(CFG['controls']), list(CFG['sensitivity'])
LABEL = {k: v['label'] for grp in ('variants', 'controls', 'sensitivity') for k, v in CFG[grp].items()}
def load_mod(name, path):
    s = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
rob = load_mod('rob', PKG.parent / 'Calyx Research Pipeline' / 'robustness.py')
split = load_mod('ds', PKG.parent / 'Calyx Research Pipeline' / 'data_split.py').research_split('2021-10-17', '2026-10-17')
WINDOWS = {'Dev 2021-23': (split['development']['start'], split['development']['end_exclusive']),
           'Val 2023-24': (split['validation']['start'], split['validation']['end_exclusive']),
           'OOS 2024-26': (split['oos']['start'], split['oos']['end_exclusive']), '5 years': ('2021-10-17', '2026-10-17')}


def load(v, period):
    d = ROOT / 'native' / f'nw-EURUSD-{v}-{period}'
    if not (d / 'run.json').exists(): return None, [], None, None
    meta = json.loads((d / 'run.json').read_text())
    trades = json.loads(gzip.decompress((d / 'trades.json.gz').read_bytes()))
    for t in trades: t['open'] = datetime.fromisoformat(t['open_time']); t['close'] = datetime.fromisoformat(t['close_time'])
    trades.sort(key=lambda t: t['close'])
    j = gzip.decompress((d / 'journal.txt.gz').read_bytes()).decode('utf-8', 'ignore')
    m = re.findall(r'EUR8_SUMMARY ([^\r\n]*)', j)
    cnt = {k: int(x) for k, x in (kv.split('=') for kv in m[-1].split())} if m else None
    return meta, trades, cnt, j


def streaks(p):
    runs = {True: [], False: []}; cur, n = None, 0
    for x in p:
        if x == 0:
            if cur is not None: runs[cur].append(n)
            cur, n = None, 0; continue
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
    aw, al, mw, ml = streaks(p); ex = defaultdict(int)
    for t in ts: ex['SL' if (t.get('exit_comment') or '').lower().startswith('sl') else 'time'] += 1
    m = (meta or {}).get('metrics', {})
    return dict(trades=len(p), per_month=round(len(p) / (days / 30.4375), 2), per_week=round(len(p) / (days / 7), 2), per_day=round(len(p) / len(weekdays), 3),
                ret=round(sum(p) / bal0 * 100, 2), pf=round(gp / gl, 2) if gl else None, win=round(100 * sum(x > 0 for x in p) / len(p), 1) if p else None,
                consistency=round(100 * sum(months.get(k, 0) > 0 for k in allm) / len(allm), 1) if allm else None,
                avg_w=aw, avg_l=al, max_w=mw, max_l=ml, sharpe=round(mean / sd * math.sqrt(252), 2) if sd > 0 and len(p) >= 10 else None,
                bal_dd=round(bdd, 2), eq_dd=m.get('max_drawdown_pct'), mean_R=round(sum(R) / len(R), 3) if R else None, exits=dict(ex), net=round(sum(p), 2),
                costs=round(sum(t['total_costs'] for t in ts), 2))


f = lambda x, s='': '—' if x is None else f'{x}{s}'  # noqa: E731
HDR = ('| Version | Window | Trades | /month | /week | /day | Return | PF | Win % | Consistency | Avg win / loss streak (max) | Sharpe | Bal DD | Eq DD | Mean R | Exits SL / time |\n'
       '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---|')
def line(name, w, r):
    e = r['exits']
    return (f"| {name} | {w} | {r['trades']} | {r['per_month']} | {r['per_week']} | {r['per_day']} | {r['ret']:+.2f}% | {f(r['pf'])} | {f(r['win'])} | {f(r['consistency'], '%')} | "
            f"{r['avg_w']} / {r['avg_l']} ({r['max_w']} / {r['max_l']}) | {f(r['sharpe'])} | {r['bal_dd']}% | {f(r['eq_dd'], '%')} | {f(r['mean_R'])} | {e.get('SL', 0)} / {e.get('time', 0)} |")


out = dict(native={}, windows={}, counters={}, dependence={}, gate={}, drift={})
md = ['# EURUSD 8am fresh swing low — raw results (generated)', '',
      'Native MT5 Model 4, 150 ms, $10k, 1% risk, H1, study end 2026-10-17 exclusive. Consistency = share of profitable months; Sharpe = annualised daily;',
      'Bal DD = closed-balance drawdown; Eq DD = native floating-equity drawdown (native runs only). Mean R = net / (1% of balance).', '']
md += ['## Main versions — separate native runs per period', '', HDR]
for v in MAIN:
    for per, s in CFG['periods'].items():
        meta, trades, cnt, _ = load(v, per)
        if meta is None: continue
        r = stats(trades, datetime.strptime(s, '%Y.%m.%d'), END, meta); out['native'][f'{v}|{per}'] = r
        if per in ('3y', '5y'): out['dependence'][f'{v}|{per}'] = rob.dependence(trades)
        md.append(line(f'**{v}**', per, r))
md.append('')
md += ['## Windows inside the 5-year runs (by trade open date)', '', HDR]
for v in MAIN + CONTROLS + SENS:
    meta, trades, cnt, _ = load(v, '5y')
    if meta is None or v.startswith('LOG_'): continue
    out['counters'][v] = cnt
    for w, (a, b) in WINDOWS.items():
        r = stats(trades, datetime.fromisoformat(a), datetime.fromisoformat(b), meta if w == '5 years' else None); out['windows'].setdefault(v, {})[w] = r
        if w == '5 years' or v in MAIN: md.append(line(f'{v}', w, r))
md.append('')

# gate
for v in MAIN:
    r3, r5 = out['native'].get(f'{v}|3y'), out['native'].get(f'{v}|5y')
    if not (r3 and r5): continue
    rng = [out['windows'][k]['5 years'] for k in (f'RNG1_{v}', f'RNG2_{v}', f'RNG3_{v}') if k in out['windows']]
    allr = out['windows'].get(f'ALL_{v}', {}).get('5 years'); rngR = statistics.fmean(x['mean_R'] or 0 for x in rng) if rng else None
    me = out['windows'][v]['5 years']['mean_R']
    dep = [out['dependence'].get(f'{v}|3y', {}), out['dependence'].get(f'{v}|5y', {})]
    g = dict(positive_3y_5y=r3['ret'] > 0 and r5['ret'] > 0, pf_3y_5y=(r3['pf'] or 0) >= 1.15 and (r5['pf'] or 0) >= 1.15, trades=r5['trades'] >= 30,
             beats_all=allr is not None and me is not None and me > (allr['mean_R'] or -9), beats_random=rngR is not None and me is not None and me > rngR,
             best_day_trade=all(d.get('verdict') == 'PASS' for d in dep))
    out['gate'][v] = dict(checks=g, passed=all(g.values()), random_mean_R=rngR, all_mean_R=allr and allr['mean_R'])
yn = lambda b: 'yes' if b else '**no**'  # noqa: E731
md += ['## Raw gate', '', '| Version | Positive 3y & 5y | PF ≥ 1.15 3y & 5y | ≥ 30 trades | Mean R > every-day control | Mean R > random control | Best day/trade | Verdict |', '|---|---|---|---|---|---|---|---|']
for v, g in out['gate'].items():
    c = g['checks']; md.append(f"| {v} | {yn(c['positive_3y_5y'])} | {yn(c['pf_3y_5y'])} | {yn(c['trades'])} | {yn(c['beats_all'])} | {yn(c['beats_random'])} | {yn(c['best_day_trade'])} | **{'PASS' if g['passed'] else 'FAIL'}** |")
md += ['', '## Best-day dependence (3y / 5y)', '']
for k, d in out['dependence'].items():
    if d.get('verdict') == 'NO_TRADES': continue
    md.append(f"- {k}: total ${d['total']:+,.0f}; without best day ${d.get('without_best_day', 0):+,.0f}; without best trade ${d.get('without_best_trade', 0):+,.0f}; "
              f"without 5 best days ${d.get('without_top5_days', 0):+,.0f}; without worst day ${d.get('without_worst_day', 0):+,.0f} → {d['verdict']}")

# drift profile from the loggers (no stop, no costs): forward bid change in ATR units and pips
md += ['', '## No-stop drift profile from the loggers (bid change after the 08:00 check; ATR = ATR(14,H1) at the check)', '']
for v in ('LOG_L8', 'LOG_NY8'):
    meta, trades, cnt, j = load(v, '5y')
    if j is None: continue
    base = {}
    for m in re.finditer(r'EUR8_DRIFT base=(\d+) h=(\d+) bid=([\d.]+)(?: atr=([\d.]+) low2=(\d) high2=(\d) low3=(\d) low2w4=(\d) low2ll=(\d) dow=(\d))?', j):
        b, h = int(m[1]), int(m[2])
        if h == 0: base[b] = dict(bid=float(m[3]), atr=float(m[4]), low2=m[5] == '1', high2=m[6] == '1', low3=m[7] == '1', low2w4=m[8] == '1', low2ll=m[9] == '1', fwd={})
        elif b in base: base[b]['fwd'][h] = float(m[3])
    rows = []
    for grp in ('all', 'low2', 'high2', 'low3', 'low2w4', 'low2ll'):
        for w, (a, bnd) in WINDOWS.items():
            lo, hi = datetime.fromisoformat(a).replace(tzinfo=timezone.utc).timestamp(), datetime.fromisoformat(bnd).replace(tzinfo=timezone.utc).timestamp()
            sel = [x for k, x in base.items() if lo <= k < hi and (grp == 'all' or x[grp])]
            cells = []
            for h in (1, 2, 4, 6, 8):
                vals = [(x['fwd'][h] - x['bid']) / x['atr'] for x in sel if h in x['fwd'] and x['atr'] > 0]
                if len(vals) < 5: cells.append('—'); continue
                mu = statistics.fmean(vals); se = statistics.stdev(vals) / math.sqrt(len(vals))
                pips = statistics.fmean((x['fwd'][h] - x['bid']) * 1e4 for x in sel if h in x['fwd'])
                cells.append(f'{mu:+.3f} ATR ({pips:+.1f} pips, t {mu / se:+.1f}, up {100 * sum(z > 0 for z in vals) / len(vals):.0f}%)')
                out['drift'].setdefault(v, {}).setdefault(grp, {}).setdefault(w, {})[h] = dict(n=len(vals), mean_atr=round(mu, 4), t=round(mu / se, 2), pips=round(pips, 2))
            rows.append(f"| {grp} | {w} | {len(sel)} ({len(sel) / max(1, ((datetime.fromisoformat(bnd) - datetime.fromisoformat(a)).days / 7)):.2f}/week) | " + ' | '.join(cells) + ' |')
    md += [f'### {v}', '', '| Days | Window | n (per week) | +1 h | +2 h | +4 h | +6 h | +8 h |', '|---|---|---|---|---|---|---|---|', *rows, '']
md += ['## Counters (5y)', '', '| Run | Weekday checks | Fresh swing low | Fresh swing high | Entries | No pivot | Skipped stops / margin | Place / close fails |', '|---|---:|---:|---:|---:|---:|---|---|']
for k, c in out['counters'].items():
    if c: md.append(f"| {k} | {c['days']} | {c['fresh_low']} | {c['fresh_high']} | {c['entries']} | {c['no_pivot']} | {c['skipped_stops']} / {c['skipped_margin']} | {c['place_fails']} / {c['close_fails']} |")
(ROOT / 'RESULTS.md').write_text('\n'.join(md) + '\n', encoding='utf-8'); (ROOT / 'RESULTS.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8')
print('\n'.join(md))

import matplotlib; matplotlib.use('Agg')  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
fig, axes = plt.subplots(2, 1, figsize=(12, 9))
for ax, tz in zip(axes, ('L8', 'NY8')):
    for v, col, lw in ((tz, '#1f77b4', 2.0), (f'SHORT_{tz}', '#d62728', 1.2), (f'ALL_{tz}', '#7f7f7f', 1.2), (f'RNG1_{tz}', '#bcbd22', .9), (f'RNG2_{tz}', '#17becf', .9), (f'RNG3_{tz}', '#9467bd', .9)):
        meta, trades, _, _ = load(v, '5y')
        if not trades: continue
        x, y, bal = [datetime.fromisoformat('2021-10-17')], [DEP], DEP
        for t in trades: bal += t['net_profit']; x.append(t['close']); y.append(bal)
        ax.step(x, y, where='post', label=f'{v}: {LABEL[v]}', lw=lw, color=col)
    for a in (split['validation']['start'], split['oos']['start']): ax.axvline(datetime.fromisoformat(a), color='k', lw=.6, ls=':')
    ax.axhline(DEP, color='grey', lw=.7, ls='--'); ax.legend(fontsize=7)
    ax.set_title(f'EURUSD H1 · 08:00 {"London" if tz == "L8" else "New York"} · native MT5 Model 4 · 5 years · 1% risk · closed balance (dotted: validation / OOS start)', fontsize=10)
fig.tight_layout(); fig.savefig(ROOT / 'balance.png', dpi=130)
