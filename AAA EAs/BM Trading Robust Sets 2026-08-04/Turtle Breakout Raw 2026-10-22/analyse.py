"""Metrics, gate, per-asset / per-year, swap and equity graph for the Turtle breakout portfolio raw study.
Run from AAA EAs/EA store:  uv run --with matplotlib python "<study>/analyse.py"   -> RESULTS.md / RESULTS.json / equity.png"""
import gzip, html, importlib.util, json, math, re, statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent; PKG = ROOT.parent
CFG = json.loads((ROOT / 'run-config.json').read_text(encoding='utf-8')); DEP = float(CFG['deposit'])
LABEL = {k: v['label'] for g in ('variants', 'controls', 'sensitivity') for k, v in CFG[g].items()}
ASSETS = CFG['common_inputs']['InpSymbols'].split(',')
def load_mod(name, path):
    s = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
rob = load_mod('rob', PKG.parent / 'Calyx Research Pipeline' / 'robustness.py')


def load(v, period):
    d = ROOT / 'native' / f'nw-BTCUSD-{v}-{period}'
    if not (d / 'run.json').exists(): return None
    meta = json.loads((d / 'run.json').read_text()); j = gzip.decompress((d / 'journal.txt.gz').read_bytes()).decode('utf-8', 'ignore')
    legs = json.loads(gzip.decompress((d / 'trades.json.gz').read_bytes()))
    for t in legs: t['close'] = datetime.fromisoformat(t['close_time'])
    risk, last_ep = {}, {}
    pct = float({**CFG['common_inputs'], **next(g[v] for g in (CFG['variants'], CFG['controls'], CFG['sensitivity']) if v in g)['inputs']}['InpRiskPct'])
    for m in re.finditer(r'TURTLE_OPEN sym=(\S+) ep=(\d+) why=(\w+) price=([\d.]+) stop=([\d.]+) active=([\d.]+) lots=([\d.]+) hwm=([\d.]+)', j):
        k = (m[1], int(m[2])); last_ep[m[1]] = int(m[2])
        if k not in risk: risk[k] = pct / 100 * float(m[8])
    eps = defaultdict(lambda: dict(net=0.0, legs=0, close=0))
    # The journal holds the agent log twice: de-duplicate the close lines (one position per asset, so sym/ep/time is unique).
    for m in sorted(set(re.findall(r'TURTLE_CLOSE sym=(\S+) ep=(\d+) reason=(\w+) time=(\d+) net=(-?[\d.]+)', j))):
        e = eps[(m[0], int(m[1]))]; e['net'] += float(m[4]); e['legs'] += 1; e['close'] = max(e['close'], int(m[3]))
    # Positions still open at the end are closed by the tester ('end of test') and not logged by the EA: book them on the open episode.
    for t in legs:
        if 'end of test' in (t.get('exit_comment') or '').lower():
            e = eps[(t['symbol'], last_ep[t['symbol']])]; e['net'] += t['net_profit']; e['legs'] += 1
            e['close'] = max(e['close'], int(t['close'].replace(tzinfo=timezone.utc).timestamp())); e['end_of_test'] = True
    total = round(sum(e['net'] for e in eps.values()), 2)
    assert abs(total - meta['metrics']['net_profit']) < 1.0, ('episodes do not reconcile with native net', v, period, total, meta['metrics']['net_profit'])
    days = {}
    for m in re.finditer(r'TURTLE_DAY epoch=(\d+) equity=([\d.]+) balance=([\d.]+) hwm=([\d.]+)', j): days[int(m[1])] = float(m[2])
    summ = {}
    for m in re.findall(r'TURTLE_SUMMARY ([^\r\n]*)', j):
        dd = dict(kv.split('=') for kv in m.split()); summ[dd['sym']] = dd
    meta['metrics'].update(native_dd(d / f'{d.name}.htm.gz'))
    return dict(meta=meta, legs=legs, eps=dict(eps), risk=risk, days=dict(sorted(days.items())), summ=summ)


def native_dd(path):
    """Relative (largest %) equity and balance drawdowns from the native report. The 'maximal' figure MT5 also prints is the
    % at the largest $ drawdown, which understates the worst % once the account has compounded."""
    h = gzip.decompress(path.read_bytes()); s = h.decode('utf-16') if h[:2] in (b'\xff\xfe', b'\xfe\xff') else h.decode('utf-8', 'ignore')
    t = html.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', s))); out = {}
    for key, lab in (('equity_dd_rel_pct', 'Equity Drawdown Relative'), ('balance_dd_rel_pct', 'Balance Drawdown Relative')):
        m = re.search(lab + r':?\s*([\d.]+)%', t); out[key] = float(m[1]) if m else None
    return out


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


def metrics(r, sym=None, start=None, end=None):
    eps = [(k, e) for k, e in sorted(r['eps'].items(), key=lambda kv: kv[1]['close']) if (sym is None or k[0] == sym) and (start is None or e['close'] >= start) and (end is None or e['close'] < end)]
    p = [e['net'] for _, e in eps]; R = [e['net'] / r['risk'][k] for k, e in eps if r['risk'].get(k)]
    legs = [t for t in r['legs'] if (sym is None or t['symbol'] == sym) and (start is None or t['close'].replace(tzinfo=timezone.utc).timestamp() >= start) and (end is None or t['close'].replace(tzinfo=timezone.utc).timestamp() < end)]
    ks = [k for k in r['days'] if (start is None or k >= start) and (end is None or k < end)]
    out = dict(trades=len(p), positions=len(legs), net=round(sum(p), 2), swap=round(sum(t['swap'] for t in legs), 2),
               held_over_23h=sum((datetime.fromisoformat(t['close_time']) - datetime.fromisoformat(t['open_time'])).total_seconds() > 23 * 3600 for t in legs))
    gp, gl = sum(x for x in p if x > 0), -sum(x for x in p if x < 0); (aw, mw), (al, ml) = streaks(p)
    out.update(pf=round(gp / gl, 2) if gl else None, win=round(100 * sum(x > 0 for x in p) / len(p), 1) if p else None, mean_R=round(statistics.fmean(R), 3) if R else None,
               win_streak=f'{aw} ({mw})', loss_streak=f'{al} ({ml})')
    if sym is None and len(ks) > 3:
        eq = [r['days'][k] for k in ks]; rets = [eq[i] / eq[i - 1] - 1 for i in range(1, len(eq))]; sd = statistics.stdev(rets)
        peak, dd = eq[0], 0.
        for x in eq: peak = max(peak, x); dd = max(dd, (peak - x) / peak)
        yrs = (ks[-1] - ks[0]) / 86400 / 365.25; months = defaultdict(float)
        for i in range(1, len(ks)): months[datetime.fromtimestamp(ks[i], timezone.utc).strftime('%Y-%m')] += eq[i] - eq[i - 1]
        bal = peak2 = eq[0]; cdd = 0.
        for x in p: bal += x; peak2 = max(peak2, bal); cdd = max(cdd, (peak2 - bal) / peak2)
        whole = start is None and end is None   # full window: native final result; sub-windows: rollover equity samples
        g = 1 + r['meta']['metrics']['return_pct'] / 100 if whole else eq[-1] / eq[0]
        out.update(return_pct=round(100 * (g - 1), 2), cagr=round(100 * (g ** (1 / yrs) - 1), 2) if yrs > 0.3 else None,
                   sharpe=round(statistics.fmean(rets) / sd * math.sqrt(365), 2) if sd > 0 else None, daily_eq_dd=round(100 * dd, 2), closed_dd=round(100 * cdd, 2),
                   per_month=round(len(p) / ((ks[-1] - ks[0]) / 86400 / 30.4375), 2), per_day=round(len(p) / len(ks), 3),
                   consistency=round(100 * sum(v > 0 for v in months.values()) / len(months), 1) if months else None,
                   native_eq_dd=r['meta']['metrics'].get('equity_dd_rel_pct'), native_bal_dd=r['meta']['metrics'].get('balance_dd_rel_pct'),
                   return_ex_swap_pct=round(100 * (g - 1 - out['swap'] / (DEP if whole else eq[0])), 2))  # diagnostic: swap added back, no re-compounding
    return out


HDR = ('| Version | Window | Return | CAGR | Sharpe | Equity DD (native, max %) | Balance DD (native, max %) | Trades | / month | / day | PF | Win % | Mean R | Win streak avg (max) | Loss streak avg (max) | Consistency | Swap $ | Return before swap | Positions > 23 h |\n'
       '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---:|---:|---:|---:|')
f = lambda x, s='': '—' if x is None else f'{x}{s}'  # noqa: E731
def line(name, w, m):
    return (f"| {name} | {w} | {m['return_pct']:+.2f}% | {f(m['cagr'], '%')} | {f(m['sharpe'])} | {f(m['native_eq_dd'], '%')} | {f(m['native_bal_dd'], '%')} | {m['trades']} | {m['per_month']} | {m['per_day']} | "
            f"{f(m['pf'])} | {f(m['win'])} | {f(m['mean_R'])} | {m['win_streak']} | {m['loss_streak']} | {f(m['consistency'], '%')} | {m['swap']:+,.0f} | {m['return_ex_swap_pct']:+.2f}% | {m['held_over_23h']} |")


out = dict(main={}, assets={}, years={}, controls={}, sens={}, gate={}, dependence={})
md = ['# Turtle breakout portfolio (US500, USTEC, XAU, XAG, BTC) — raw results (generated)', '',
      'Native MT5 Model 4, 150 ms, $100k, 2% of high-water-mark risk per trade. A trade = one signal (day-trading re-entries belong to the same trade).',
      'Mean R = trade net / (2% × HWM at entry). Sharpe from the equity at each 17:00 NY rollover (√365). Consistency = profitable months.',
      'Drawdowns are MT5 "relative" (largest % from a peak). Per-year DD uses the rollover equity samples. / day = per calendar day (Bitcoin trades 7 days).',
      'Return before swap is a diagnostic: swap added back, without re-compounding.', '', '## Main versions — separate native windows', '', HDR]
for v in ('HOLD', 'DAY'):
    for per in ('6m', '1y', '3y', '5y'):
        r = load(v, per)
        if not r: continue
        m = metrics(r); out['main'][f'{v}|{per}'] = m; md.append(line(f'**{v}**', per, m))
        if per in ('3y', '5y'): out['dependence'][f'{v}|{per}'] = rob.dependence([dict(net_profit=t['net_profit'], close_time=t['close_time']) for t in r['legs']])
md += ['', '## Per asset — 5 years', '', '| Version | Asset | Trades | Positions | Net $ | PF | Win % | Mean R | Swap $ |', '|---|---|---:|---:|---:|---:|---:|---:|---:|']
for v in ('HOLD', 'DAY'):
    r = load(v, '5y')
    if not r: continue
    for a in ASSETS:
        m = metrics(r, sym=a); out['assets'][f'{v}|{a}'] = m
        md.append(f"| {v} | {a} | {m['trades']} | {m['positions']} | {m['net']:+,.0f} | {f(m['pf'])} | {f(m['win'])} | {f(m['mean_R'])} | {m['swap']:+,.0f} |")
md += ['', '## Per calendar year — 5-year runs', '', '| Version | ' + ' | '.join(str(y) for y in range(2021, 2027)) + ' |', '|---|' + '---|' * 6]
for v in ('HOLD', 'DAY'):
    r = load(v, '5y')
    if not r: continue
    cells = []
    for y in range(2021, 2027):
        a, b = datetime(y, 1, 1, tzinfo=timezone.utc).timestamp(), datetime(y + 1, 1, 1, tzinfo=timezone.utc).timestamp(); m = metrics(r, start=a, end=b)
        out['years'][f'{v}|{y}'] = m; cells.append('—' if 'return_pct' not in m else f"{m['return_pct']:+.1f}% (DD {m['daily_eq_dd']:.0f}%, PF {f(m['pf'])})")
    md.append(f'| {v} | ' + ' | '.join(cells) + ' |')
md += ['', '## Controls and sensitivities — 5 years, Model 4', '', HDR]
for v in [*CFG['controls'], *CFG['sensitivity']]:
    r = load(v, '5y')
    if not r: continue
    m = metrics(r); (out['controls'] if v in CFG['controls'] else out['sens'])[v] = m; md.append(line(f'{v}', '5y', m))
yn = lambda x: 'yes' if x else '**no**'  # noqa: E731
md += ['', '## Raw gate', '', '| Version | Positive 3y & 5y | PF ≥ 1.15 3y & 5y | ≥ 30 trades | Mean R > random mean | Best day / trade | Verdict |', '|---|---|---|---|---|---|---|']
for v in ('HOLD', 'DAY'):
    a, b = out['main'].get(f'{v}|3y'), out['main'].get(f'{v}|5y')
    rnd = [out['controls'][k] for k in (f'RND_{v}1', f'RND_{v}2', f'RND_{v}3') if k in out['controls']]
    if not (a and b): continue
    rR = statistics.fmean(x['mean_R'] or 0 for x in rnd) if rnd else None
    g = dict(pos=a['return_pct'] > 0 and b['return_pct'] > 0, pf=(a['pf'] or 0) >= 1.15 and (b['pf'] or 0) >= 1.15, n=b['trades'] >= 30,
             rnd=rR is not None and (b['mean_R'] or -9) > rR, dep=all(out['dependence'].get(f'{v}|{p}', {}).get('verdict') == 'PASS' for p in ('3y', '5y')))
    out['gate'][v] = dict(checks=g, passed=all(g.values()), random_mean_R=rR)
    md.append(f"| {v} | {yn(g['pos'])} | {yn(g['pf'])} | {yn(g['n'])} | {yn(g['rnd'])} ({f(b['mean_R'])} vs {f(rR and round(rR, 3))}) | {yn(g['dep'])} | **{'PASS' if all(g.values()) else 'FAIL'}** |")
md += ['', '## Best-day dependence (positions)', ''] + [f"- {k}: total ${d['total']:+,.0f}; without best day ${d.get('without_best_day', 0):+,.0f}; without best trade ${d.get('without_best_trade', 0):+,.0f}; without 5 best days ${d.get('without_top5_days', 0):+,.0f} → {d['verdict']}" for k, d in out['dependence'].items() if d.get('verdict') != 'NO_TRADES']
(ROOT / 'RESULTS.md').write_text('\n'.join(md) + '\n', encoding='utf-8'); (ROOT / 'RESULTS.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8'); print('\n'.join(md))

import matplotlib; matplotlib.use('Agg')  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
fig, (ax, ax2) = plt.subplots(2, 1, figsize=(12, 9.5), height_ratios=(3, 2), sharex=True)
for v, col, lw, ls in (('HOLD', '#d62728', 2.2, '-'), ('DAY', '#1f77b4', 2.2, '-'), ('RND_HOLD1', '#f4a3a3', .8, '-'), ('RND_HOLD2', '#f4a3a3', .8, '-'), ('RND_HOLD3', '#f4a3a3', .8, '-'),
                       ('RND_DAY1', '#9ec5e8', .8, '--'), ('RND_DAY2', '#9ec5e8', .8, '--'), ('RND_DAY3', '#9ec5e8', .8, '--')):
    r = load(v, '5y')
    if not r or not r['days']: continue
    ks = list(r['days']); ax.plot([datetime.fromtimestamp(k, timezone.utc) for k in ks], [100 * r['days'][k] / DEP for k in ks], color=col, lw=lw, ls=ls,
                                  label=f"{v}: {r['meta']['metrics']['return_pct']:+.1f}%" + ('' if v.startswith('RND') else f' — {LABEL[v]}'))
ax.axhline(100, color='k', lw=.6, ls='--'); ax.legend(fontsize=7, loc='upper left'); ax.set_ylabel('equity (start = 100)')
ax.set_title('Turtle breakout portfolio · US500, USTEC, XAU, XAG, BTC · native MT5 Model 4 · 5 years · equity at each 17:00 NY rollover\n'
             'thin lines: random-entry controls (same stops, sizing and schedule)', fontsize=10)
r = load('HOLD', '5y')
if r:
    for a, col in zip(ASSETS, ('#8c564b', '#e377c2', '#bcbd22', '#7f7f7f', '#ff7f0e')):
        e = sorted((x['close'], x['net']) for k, x in r['eps'].items() if k[0] == a); c, ys = 0, []
        for _, n in e: c += n; ys.append(c)
        ax2.step([datetime.fromtimestamp(t, timezone.utc) for t, _ in e], ys, where='post', color=col, lw=1.6, label=f'{a}: {c:+,.0f} $')
    ax2.axhline(0, color='k', lw=.6, ls='--'); ax2.legend(fontsize=7, loc='upper left'); ax2.set_ylabel('HOLD cumulative net per asset ($)')
fig.tight_layout(); fig.savefig(ROOT / 'equity.png', dpi=130)
