"""Metrics, gate, yearly split, costs, sensitivity and balance graph for the FTSE 100 Monday-dip raw study.
Run from AAA EAs/EA store:  uv run --with matplotlib python "<study>/analyse.py"
Fills REPORT.template.md -> REPORT.md when the template exists."""
import gzip, json, math, re
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CFG = json.loads((ROOT / 'run-config.json').read_text(encoding='utf-8'))
PER = '2020_2023'
START, END = datetime.strptime(CFG['periods'][PER], '%Y.%m.%d'), datetime.strptime(CFG['end_date'], '%Y.%m.%d')
DEP, RISK = 10000.0, float(CFG['common_inputs']['InpRiskPercent']) / 100
MAIN, CONTROLS, SENS = list(CFG['variants']), list(CFG['controls']), list(CFG['sensitivity'])
LABEL = {k: v['label'] for grp in ('variants', 'controls', 'sensitivity') for k, v in CFG[grp].items()}
YEARS = list(range(START.year, END.year))


def load(v):
    d = ROOT / 'native' / f'nw-UK100-{v}-{PER}'
    if not (d / 'run.json').exists():
        return None, [], None
    meta = json.loads((d / 'run.json').read_text())
    trades = json.loads(gzip.decompress((d / 'trades.json.gz').read_bytes()))
    for t in trades:
        t['open'] = datetime.fromisoformat(t['open_time']); t['close'] = datetime.fromisoformat(t['close_time'])
    trades.sort(key=lambda t: t['close'])
    j = gzip.decompress((d / 'journal.txt.gz').read_bytes()).decode('utf-8', 'ignore')
    m = re.findall(r'FTSE_SUMMARY ([^\r\n]*)', j)
    counters = {k: int(x) for k, x in (kv.split('=') for kv in m[-1].split())} if m else None
    return meta, trades, counters


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


def stats(trades, meta=None):
    p = [t['net_profit'] for t in trades]
    days = (END - START).days
    weekdays = [START + timedelta(days=i) for i in range(days) if (START + timedelta(days=i)).weekday() < 5]
    gp, gl = sum(x for x in p if x > 0), -sum(x for x in p if x < 0)
    bal, peak, bdd, R = DEP, DEP, 0.0, []
    for t in trades:
        R.append(t['net_profit'] / (RISK * bal)); bal += t['net_profit']; peak = max(peak, bal); bdd = max(bdd, (peak - bal) / peak * 100)
    daily = defaultdict(float)
    for t in trades: daily[t['close'].date()] += t['net_profit']
    eq, rets = DEP, []
    for d in weekdays:
        r = daily.get(d.date(), 0.0) / eq; rets.append(r); eq += daily.get(d.date(), 0.0)
    for d, v in daily.items():                       # weekend closes (time exits at reopen) are rare; book them anyway
        if datetime.combine(d, datetime.min.time()).weekday() >= 5: rets.append(v / DEP)
    mean = sum(rets) / len(rets); sd = math.sqrt(sum((r - mean) ** 2 for r in rets) / len(rets))
    months = defaultdict(float)
    for t in trades: months[(t['close'].year, t['close'].month)] += t['net_profit']
    allm = {(y, m) for y in YEARS for m in range(1, 13)}
    aw, al, mw, ml = streaks(p)
    ex = defaultdict(int)
    for t in trades:
        c = (t.get('exit_comment') or '').lower()
        ex['TP' if c.startswith('tp') else 'SL' if c.startswith('sl') else 'time'] += 1
    m = (meta or {}).get('metrics', {})
    return dict(trades=len(p), per_month=round(len(p) / (days / 30.4375), 2), per_day=round(len(p) / len(weekdays), 3),
                ret=round(sum(p) / DEP * 100, 2), pf=round(gp / gl, 2) if gl else None, win=round(100 * sum(x > 0 for x in p) / len(p), 1) if p else None,
                consistency=round(100 * sum(months.get(k, 0) > 0 for k in allm) / len(allm), 1),
                avg_w=aw, avg_l=al, max_w=mw, max_l=ml, sharpe=round(mean / sd * math.sqrt(252), 2) if sd > 0 and len(p) >= 10 else None,
                bal_dd=round(bdd, 2), eq_dd=m.get('max_drawdown_pct'), mean_R=round(sum(R) / len(R), 3) if R else None,
                exits=dict(ex), net=round(sum(p), 2), costs=round(sum(t['total_costs'] for t in trades), 2))


def yearly(trades):
    out, bal = {}, DEP
    for y in YEARS:
        ts = [t for t in trades if t['close'].year == y]; p = [t['net_profit'] for t in ts]
        gp, gl = sum(x for x in p if x > 0), -sum(x for x in p if x < 0)
        out[y] = dict(n=len(p), ret=round(sum(p) / bal * 100, 2), pf=round(gp / gl, 2) if gl else None, net=round(sum(p), 2))
        bal += sum(p)
    return out


rows, years, counters = {}, {}, {}
for v in MAIN + CONTROLS + SENS:
    meta, trades, cnt = load(v)
    if meta is None: continue
    rows[v] = dict(variant=v, **stats(trades, meta), flags=meta.get('journal_flags'), ok=meta.get('ok'), real_ticks=meta.get('real_tick_lines'))
    years[v] = yearly(trades); counters[v] = cnt

f = lambda x, s='': '—' if x is None else f'{x}{s}'  # noqa: E731
HDR = ('| Version | Trades | /month | /day | Return | PF | Win % | Consistency | Avg win / loss streak (max) | Sharpe | Bal DD | Eq DD | Mean R | Exits TP / SL / 24h |\n'
       '|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---|')


def line(name, r):
    e = r['exits']
    return (f"| {name} | {r['trades']} | {r['per_month']} | {r['per_day']} | {r['ret']:+.2f}% | {f(r['pf'])} | {f(r['win'])} | {f(r['consistency'], '%')} | "
            f"{r['avg_w']} / {r['avg_l']} ({r['max_w']} / {r['max_l']}) | {f(r['sharpe'])} | {r['bal_dd']}% | {f(r['eq_dd'], '%')} | {f(r['mean_R'])} | "
            f"{e.get('TP', 0)} / {e.get('SL', 0)} / {e.get('time', 0)} |")


def table(keys):
    return HDR + '\n' + '\n'.join(line(f"**{k}** — {LABEL[k]}", rows[k]) for k in keys if k in rows)


def year_table(keys):
    out = ['| Version | ' + ' | '.join(str(y) for y in YEARS) + ' | Positive years |', '|---|' + '---|' * len(YEARS) + '---:|']
    for k in keys:
        if k not in years: continue
        cells = [f"{years[k][y]['ret']:+.2f}% (PF {f(years[k][y]['pf'])}, n{years[k][y]['n']})" for y in YEARS]
        out.append(f"| {k} | " + ' | '.join(cells) + f" | {sum(years[k][y]['net'] > 0 for y in YEARS)}/{len(YEARS)} |")
    return '\n'.join(out)


def cost_table():
    """Per-rule attribution inside BOTH is NOT reliable (FIFO entry/exit pairing when R1 and R2 longs overlap),
    so rule-level evidence comes from the standalone R1/R2 runs. This table splits gross P&L from commission+swap."""
    out = ['| Run | Gross P&L $ (incl. spread at fills) | Commission + swap $ | Net $ | Mean hold h | Weekend-gap time exits |', '|---|---:|---:|---:|---:|---:|']
    for v in MAIN + CONTROLS:
        if v not in rows: continue
        _, trades, _ = load(v)
        hold = sum((t['close'] - t['open']).total_seconds() for t in trades) / 3600 / max(len(trades), 1)
        gap = sum(1 for t in trades if not (t.get('exit_comment') or '').lower().startswith(('tp', 'sl')) and (t['close'] - t['open']).total_seconds() > 26 * 3600)
        r = rows[v]
        out.append(f"| {v} | {r['net'] - r['costs']:+,.0f} | {r['costs']:+,.0f} | {r['net']:+,.0f} | {hold:.1f} | {gap} |")
    return '\n'.join(out)


rng = [rows[k] for k in ('RNG1', 'RNG2', 'RNG3') if k in rows]
rng_pf = sum(r['pf'] or 0 for r in rng) / len(rng) if rng else None
rng_R = sum(r['mean_R'] or 0 for r in rng) / len(rng) if rng else None
gate = {}
for v in MAIN:
    if v not in rows: continue
    r = rows[v]; c = counters.get(v) or {}
    if v == 'R1':
        ctl = rows.get('C1TF'); beats = bool(ctl) and (r['pf'] or 0) > (ctl['pf'] or 0) and (r['mean_R'] or -9) > (ctl['mean_R'] or -9)
    else:
        beats = rng_pf is not None and (r['pf'] or 0) > rng_pf and (r['mean_R'] or -9) > rng_R
    g = dict(positive=r['ret'] > 0, pf=(r['pf'] or 0) >= 1.15, trades=r['trades'] >= 30,
             years=sum(years[v][y]['net'] > 0 for y in YEARS) >= 3, beats_control=beats,
             clean=not any((r['flags'] or {}).get(k) for k in ('init_failed', 'critical', 'rejected')) and not c.get('place_fails') and not c.get('close_fails'))
    gate[v] = dict(checks=g, passed=all(g.values()))
yn = lambda b: 'yes' if b else '**no**'  # noqa: E731
gate_md = ('| Version | Positive | PF ≥ 1.15 | ≥ 30 trades | ≥ 3/4 years positive | Beats control | Clean | Verdict |\n|---|---|---|---|---|---|---|---|\n' +
           '\n'.join(f"| {v} | {yn(g['checks']['positive'])} | {yn(g['checks']['pf'])} | {yn(g['checks']['trades'])} | {yn(g['checks']['years'])} | "
                     f"{yn(g['checks']['beats_control'])} | {yn(g['checks']['clean'])} | **{'PASS' if g['passed'] else 'FAIL'}** |" for v, g in gate.items()))
ctl_md = (f"Random-entry control mean (RNG1–3): PF {rng_pf:.2f}, mean R {rng_R:+.3f}, "
          f"return {sum(r['ret'] for r in rng) / len(rng):+.2f}%." if rng else 'Random controls not run.')
cnt_md = ('| Run | H1 bars | R1 signals / entries | R2 signals / entries | R2 flat bars | Random entries | Skipped (stops / margin) | Place / close fails |\n|---|---:|---|---|---:|---:|---|---|\n' +
          '\n'.join(f"| {k} | {c['bars']} | {c['r1_signals']} / {c['r1_entries']} | {c['r2_signals']} / {c['r2_entries']} | {c['r2_flat_bars']} | {c['rng_entries']} | "
                    f"{c['skipped_stops']} / {c['skipped_margin']} | {c['place_fails']} / {c['close_fails']} |" for k, c in counters.items() if c))

print(table(MAIN + CONTROLS + SENS)); print(); print(year_table(MAIN + CONTROLS + SENS)); print(); print(cost_table()); print(); print(gate_md); print(ctl_md); print(); print(cnt_md)
(ROOT / 'RESULTS.json').write_text(json.dumps(dict(rows=rows, years=years, counters=counters, gate=gate,
                                                   rng_mean=dict(pf=rng_pf, mean_R=rng_R)), indent=2, default=str), encoding='utf-8')

tpl = ROOT / 'REPORT.template.md'
if tpl.exists():
    s = tpl.read_text(encoding='utf-8')
    for k, v in {'{{MAIN}}': table(MAIN), '{{CONTROLS}}': table(CONTROLS), '{{SENS}}': table(SENS), '{{YEARS}}': year_table(MAIN + CONTROLS),
                 '{{YEARS_SENS}}': year_table(SENS), '{{COSTS}}': cost_table(), '{{GATE}}': gate_md, '{{CTL}}': ctl_md, '{{COUNTERS}}': cnt_md}.items():
        s = s.replace(k, v)
    (ROOT / 'REPORT.md').write_text(s, encoding='utf-8')

import matplotlib; matplotlib.use('Agg')  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
fig, axes = plt.subplots(2, 1, figsize=(12, 8.5))
style = {'BOTH': ('#1f77b4', 2.0), 'R1': ('#2ca02c', 1.3), 'R2': ('#ff7f0e', 1.3), 'C1TF': ('#9467bd', 1.1)}
for ax, keys, title in ((axes[0], MAIN + ['C1TF', 'RNG1', 'RNG2', 'RNG3'], 'main versions and controls'), (axes[1], ['BOTH'] + SENS, 'BOTH vs declared sensitivities')):
    for v in keys:
        meta, trades, _ = load(v)
        if not trades: continue
        x, y, bal = [START], [DEP], DEP
        for t in trades: bal += t['net_profit']; x.append(t['close']); y.append(bal)
        col, lw = style.get(v, ('#999999', 0.9))
        if ax is axes[1] and v != 'BOTH': col, lw = None, 1.0
        ax.step(x, y, where='post', label=f'{v}: {LABEL[v]}', lw=lw, color=col)
    ax.axhline(DEP, color='grey', lw=.7, ls='--'); ax.set_title(f'UK100 (FTSE 100 CFD) H1 · native MT5 Model 4 · 2020–2023 · 0.75% risk · closed balance · {title}', fontsize=10)
    ax.legend(fontsize=7, ncol=2)
fig.tight_layout(); fig.savefig(ROOT / 'balance.png', dpi=130)
