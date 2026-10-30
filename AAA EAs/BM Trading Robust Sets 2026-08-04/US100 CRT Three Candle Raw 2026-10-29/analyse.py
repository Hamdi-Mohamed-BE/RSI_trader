"""Results for the US100 CRT three-candle raw study: in-sample (development, validation) and out-of-sample splits of each 5y ledger,
native windows of the Model 4 confirmation, raw gate, random-direction controls, best-day falsifier and a balance chart.
Run from AAA EAs/EA store:  uv run --with matplotlib python "<study>/analyse.py"   -> RESULTS.md, RESULTS.json, balance.png"""
import gzip, json, math, re, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1] / 'EA store')); sys.path.insert(0, str(ROOT.parents[1] / 'Calyx Research Pipeline'))
from app.mt5_evidence_jobs import _metric, _read_report  # noqa: E402
from robustness import dependence  # noqa: E402

CFG = json.loads((ROOT / 'run-config.json').read_text(encoding='utf-8'))
END = datetime.strptime(CFG['end_date'], '%Y.%m.%d'); DEP, RISK = 10000.0, 0.01
LABEL = {k: v['label'] for grp in ('variants', 'controls') for k, v in CFG[grp].items()}
SEGS = {'Development 2021-23': CFG['split']['development'], 'Validation 2023-24': CFG['split']['validation'], 'OOS 2024-26': CFG['split']['oos'],
        'Last 12 months': ['2025-10-27', '2026-10-27'], 'Last 3 years': ['2023-10-27', '2026-10-27'], 'All 5 years': ['2021-10-27', '2026-10-27']}
GRID = list(CFG['variants']); CTRL1 = ['RND1', 'RND2', 'RND3']; SENS = ['S_MON', 'S_ASIA', 'S_TWO', 'S_R13']
CTRL = ['RND1_M4', 'RND2_M4', 'RND3_M4']; TFV = ['M15_R_B_M4', 'M30_R_B_M4', 'H1_R_B_M4']   # Addendum 1: Model 4 is the only decision evidence


def load(v, per):
    d = ROOT / 'native' / f'nw-USTEC-{v}-{per}'
    if not (d / 'run.json').exists(): return None
    meta = json.loads((d / 'run.json').read_text())
    trades = json.loads(gzip.decompress((d / 'trades.json.gz').read_bytes()))
    for t in trades:
        t['open'] = datetime.fromisoformat(t['open_time']); t['close'] = datetime.fromisoformat(t['close_time'])
    trades.sort(key=lambda t: t['close'])
    bal = DEP
    for t in trades:                                           # R relative to the 1% risk budget at the time (closed-balance proxy)
        t['R'] = t['net_profit'] / (RISK * bal); t['bal_before'] = bal; bal += t['net_profit']; t['bal_after'] = bal
    j = gzip.decompress((d / 'journal.txt.gz').read_bytes()).decode('utf-8', 'ignore')
    m = re.findall(r'CRT_SUMMARY ([^\r\n]*)', j)
    cnt = {k: int(x) for k, x in (kv.split('=') for kv in m[-1].split())} if m else None
    rel = None; rep = next(iter(sorted(d.glob('*.htm.gz'))), None)
    if rep:
        tmp = d / '_report.htm'; tmp.write_bytes(gzip.decompress(rep.read_bytes()))
        try: rel = float(re.search(r'([\d.]+)\s*%', _metric(_read_report(tmp), 'Equity Drawdown Relative')).group(1))
        except Exception: rel = None
        tmp.unlink()
    return dict(meta=meta, trades=trades, counters=cnt, eq_dd_rel=rel)


def seg_stats(trades, a, b):
    A, Bd = datetime.fromisoformat(a), datetime.fromisoformat(b)
    ts = [t for t in trades if A <= t['open'] < Bd]
    days = (Bd - A).days; weekdays = sum(1 for i in range(days) if (A + timedelta(days=i)).weekday() < 5)
    p = [t['net_profit'] for t in ts]; R = [t['R'] for t in ts]
    gp, gl = sum(x for x in p if x > 0), -sum(x for x in p if x < 0)
    start = ts[0]['bal_before'] if ts else None; end = ts[-1]['bal_after'] if ts else None
    peak, dd, bal = (start or DEP), 0.0, (start or DEP)
    for t in ts: bal += t['net_profit']; peak = max(peak, bal); dd = max(dd, (peak - bal) / peak * 100)
    ex = defaultdict(int)
    for t in ts:
        c = (t.get('exit_comment') or '').lower(); ex['TP' if c.startswith('tp') else 'SL' if c.startswith('sl') else 'other'] += 1
    run, best_l = 0, 0
    for x in p:
        run = run + 1 if x < 0 else 0; best_l = max(best_l, run)
    return dict(trades=len(ts), per_month=round(len(ts) / (days / 30.4375), 2), per_day=round(len(ts) / weekdays, 3) if weekdays else None,
                win=round(100 * sum(x > 0 for x in p) / len(p), 1) if p else None, pf=round(gp / gl, 2) if gl else None,
                net_R=round(sum(R), 1), mean_R=round(sum(R) / len(R), 3) if R else None,
                ret=round((end / start - 1) * 100, 1) if start else 0.0, closed_dd=round(dd, 1), max_losing_streak=best_l,
                tp=ex['TP'], sl=ex['SL'], longs=sum(1 for t in ts if t.get('side') == 'Long'), shorts=sum(1 for t in ts if t.get('side') == 'Short'))


runs = {}
for v in GRID + CTRL1 + SENS + CTRL + TFV:
    r = load(v, '5y')
    if r: runs[(v, '5y')] = r
for per in ('6m', '1y', '3y', '5y'):
    r = load('MAIN_M4', per)
    if r: runs[('MAIN_M4', per)] = r
r = load('SIMPLE_M4', '5y')
if r: runs[('SIMPLE_M4', '5y')] = r

seg = {k: {s: seg_stats(r['trades'], *w) for s, w in SEGS.items()} for k, r in runs.items() if k[1] == '5y'}
dep = {k: dependence([dict(net_profit=t['net_profit'], close_time=t['close_time']) for t in r['trades']]) for k, r in runs.items()}
f = lambda x, s='': '–' if x is None else f'{x}{s}'  # noqa: E731


def seg_table(keys):
    out = ['| Version | Part | Trades | /month | /day | Win % | PF | Net R | Mean R | Return | Closed DD | Max losing run | TP / SL | Long / short |',
           '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|']
    for k in keys:
        if (k, '5y') not in seg: continue
        for s, x in seg[(k, '5y')].items():
            if s == 'Last 3 years': continue
            out.append(f"| **{k}** | {s} | {x['trades']} | {x['per_month']} | {f(x['per_day'])} | {f(x['win'])} | {f(x['pf'])} | {x['net_R']:+} | {f(x['mean_R'])} | "
                       f"{x['ret']:+}% | {x['closed_dd']}% | {x['max_losing_streak']} | {x['tp']} / {x['sl']} | {x['longs']} / {x['shorts']} |")
    return '\n'.join(out)


def grid_table():
    out = ['| Version | 5y trades (/month) | 5y PF | 5y return | Dev PF (n) | Val PF (n) | **OOS PF (n)** | OOS return | Last 12 m PF (n) | Without best day / trade (5y) |',
           '|---|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    for k in GRID:
        if (k, '5y') not in seg: continue
        s = seg[(k, '5y')]; a = s['All 5 years']; d = dep[(k, '5y')]
        out.append(f"| {k} | {a['trades']} ({a['per_month']}) | {f(a['pf'])} | {a['ret']:+}% | {f(s['Development 2021-23']['pf'])} ({s['Development 2021-23']['trades']}) | "
                   f"{f(s['Validation 2023-24']['pf'])} ({s['Validation 2023-24']['trades']}) | **{f(s['OOS 2024-26']['pf'])}** ({s['OOS 2024-26']['trades']}) | {s['OOS 2024-26']['ret']:+}% | "
                   f"{f(s['Last 12 months']['pf'])} ({s['Last 12 months']['trades']}) | ${d['without_best_day']:+,.0f} / ${d['without_best_trade']:+,.0f} |")
    return '\n'.join(out)


def native_table():
    out = ['| Window (Model 4) | Trades | /month | Return | PF | Win % | Equity DD rel / max | Sharpe | History |', '|---|---:|---:|---:|---:|---:|---:|---:|---|']
    for per in ('6m', '1y', '3y', '5y'):
        r = runs.get(('MAIN_M4', per))
        if not r: continue
        m = r['meta']['metrics']; months = {'6m': 6, '1y': 12, '3y': 36, '5y': 60}[per]
        out.append(f"| MAIN {per} | {m['trades']} | {round(m['trades'] / months, 1)} | {m['return_pct']:+}% | {m['profit_factor']} | {m['win_rate_pct']} | "
                   f"{f(r['eq_dd_rel'], '%')} / {m['max_drawdown_pct']}% | {m['sharpe_ratio']} | {m['history_quality']} |")
    r = runs.get(('SIMPLE_M4', '5y'))
    if r:
        m = r['meta']['metrics']
        out.append(f"| SIMPLE 5y | {m['trades']} | {round(m['trades'] / 60, 1)} | {m['return_pct']:+}% | {m['profit_factor']} | {m['win_rate_pct']} | "
                   f"{f(r['eq_dd_rel'], '%')} / {m['max_drawdown_pct']}% | {m['sharpe_ratio']} | {m['history_quality']} |")
    return '\n'.join(out)


ctl = [seg[(c, '5y')]['All 5 years'] for c in CTRL if (c, '5y') in seg]
ctl_pf = sum(x['pf'] or 0 for x in ctl) / len(ctl) if ctl else None; ctl_r = sum(x['mean_R'] or 0 for x in ctl) / len(ctl) if ctl else None


def gate_for(key5, key3=None):
    s = seg[(key5, '5y')]; a5 = s['All 5 years']
    if key3 and key3 in runs:
        m3 = runs[key3]['meta']['metrics']; r3, pf3, n3 = m3['return_pct'], m3['profit_factor'], m3['trades']
    else:
        a3 = s['Last 3 years']; r3, pf3, n3 = a3['ret'], a3['pf'], a3['trades']
    m5 = runs[(key5, '5y')]['meta']['metrics']; d = dep[(key5, '5y')]
    g = dict(positive=r3 > 0 and m5['return_pct'] > 0, pf=(pf3 or 0) >= 1.15 and (m5['profit_factor'] or 0) >= 1.15, trades=n3 >= 30,
             beats_control=ctl_pf is not None and (a5['pf'] or 0) > ctl_pf and (a5['mean_R'] or -9) > (ctl_r or 0),
             best_day=d.get('verdict') == 'PASS', clean=not any((runs[(key5, '5y')]['meta']['journal_flags'] or {}).get(k) for k in ('init_failed', 'critical')))
    return dict(checks=g, passed=all(g.values()), r3=r3, pf3=pf3, n3=n3, r5=m5['return_pct'], pf5=m5['profit_factor'])


gate = {}
if ('MAIN_M4', '5y') in runs: gate['MAIN (Model 4)'] = gate_for('MAIN_M4', ('MAIN_M4', '3y'))
if ('SIMPLE_M4', '5y') in runs: gate['SIMPLE (Model 4)'] = gate_for('SIMPLE_M4')
for k in TFV:
    if (k, '5y') in runs: gate[f'{k[:-3]} (Model 4)'] = gate_for(k)
yn = lambda b: 'yes' if b else '**no**'  # noqa: E731
gate_md = ['| Version | 3y return / PF / n | 5y return / PF | Positive both | PF ≥ 1.15 both | ≥ 30 trades | Beats random control | Best day / trade test | Verdict |',
           '|---|---|---|---|---|---|---|---|---|']
for k, g in gate.items():
    c = g['checks']
    gate_md.append(f"| {k} | {g['r3']:+}% / {f(g['pf3'])} / {g['n3']} | {g['r5']:+}% / {g['pf5']} | {yn(c['positive'])} | {yn(c['pf'])} | {yn(c['trades'])} | "
                   f"{yn(c['beats_control'])} | {yn(c['best_day'])} | **{'PASS' if g['passed'] else 'FAIL'}** |")

cnt_md = ['| Run | Setups M15 / M30 / H1 | Triggers | Bias-blocked | Outside session | Position open | Entries | Skipped stops / margin | Place fails |', '|---|---|---:|---:|---:|---:|---:|---|---:|']
for k, r in runs.items():
    c = r['counters']
    if c: cnt_md.append(f"| {k[0]} {k[1]} | {c['setups15']} / {c['setups30']} / {c['setups60']} | {c['triggers15'] + c['triggers30'] + c['triggers60']} | {c['bias_blocked']} | "
                        f"{c['session_blocked']} | {c['position_blocked']} | {c['entries']} | {c['skipped_stops']} / {c['skipped_margin']} | {c['place_fails']} |")
ticks = sorted({x for r in runs.values() for x in (r['meta'].get('real_tick_lines') or [])})
main_key = 'MAIN_M4' if ('MAIN_M4', '5y') in seg else 'ALL_R_B'
md = ['# US100 CRT three-candle raw study: results (generated by analyse.py)', '',
      'USTEC (Exness CFD), M1 chart, M15 / M30 / H1 setups, native MT5 (Model 1 screen, Model 4 confirmation), 150 ms, $10,000, 1% equity risk per trade (lots rounded up), '
      'end 2026-10-27 exclusive. Rules: RULES.md. Parts are split by trade entry date inside each 5y run; Return and closed DD are measured inside each part.', '',
      '## MAIN, SIMPLE and the single-timeframe MAIN versions: in-sample vs out-of-sample (Model 4)', seg_table(['MAIN_M4', 'SIMPLE_M4'] + TFV), '',
      '## MAIN, native Model 4 windows', native_table(), '',
      '## Random-direction controls (Model 4, 5y)', seg_table(CTRL), '',
      '## INVALID diagnostic: all 16 versions on Model 1 (Addendum 1: fills +3-4 points past the level, RR 1.5 -> ~1.0)', grid_table(), '',
      '## INVALID diagnostic: Model 1 controls and sensitivities', seg_table(CTRL1 + SENS), '',
      f"Control mean (RND1–3 Model 4, 5y): PF {f(ctl_pf and round(ctl_pf, 2))}, mean R {f(ctl_r and round(ctl_r, 3))}.", '',
      '## Raw gate (PIPELINE.md stage 4)', '\n'.join(gate_md), '',
      '## Best-day dependence (5y)', *[f"- {k[0]} {k[1]}: total ${d['total']:+,.0f}; without best day ${d.get('without_best_day', 0):+,.0f}; without best trade ${d.get('without_best_trade', 0):+,.0f}; "
                                       f"without 5 best days ${d.get('without_top5_days', 0):+,.0f}; verdict {d['verdict']}" for k, d in dep.items() if k[1] == '5y' and k[0] in ('MAIN_M4', 'SIMPLE_M4')], '',
      '## Execution counters', '\n'.join(cnt_md), '', 'Tick data lines: ' + '; '.join(ticks)]
(ROOT / 'RESULTS.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
(ROOT / 'RESULTS.json').write_text(json.dumps(dict(segments={f'{k[0]}|{k[1]}': v for k, v in seg.items()}, dependence={f'{k[0]}|{k[1]}': v for k, v in dep.items()},
                                                   gate=gate, control=dict(pf=ctl_pf, mean_R=ctl_r),
                                                   native={f'{k[0]}|{k[1]}': dict(r['meta']['metrics'], eq_dd_rel=r['eq_dd_rel']) for k, r in runs.items()},
                                                   counters={f'{k[0]}|{k[1]}': r['counters'] for k, r in runs.items()}), indent=1, default=str), encoding='utf-8')
print('\n'.join(md))

import matplotlib; matplotlib.use('Agg')  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
fig, axes = plt.subplots(2, 1, figsize=(12, 9))
for ax, keys, title in ((axes[0], ['MAIN_M4', 'SIMPLE_M4'] + CTRL, 'MAIN / SIMPLE vs random-direction controls (all Model 4)'),
                        (axes[1], ['MAIN_M4'] + TFV, 'MAIN vs single-timeframe versions (Model 4)')):
    for i, (name, (a, b)) in enumerate(list(SEGS.items())[:3]):
        ax.axvspan(datetime.fromisoformat(a), datetime.fromisoformat(b), color=['#f2f2f2', '#e6eef7', '#e8f5e9'][i], zorder=0)
        ax.text(datetime.fromisoformat(a) + timedelta(days=20), 0.02, name, transform=ax.get_xaxis_transform(), fontsize=8, color='#555')
    for k in keys:
        r = runs.get((k, '5y'))
        if not r: continue
        x, y = [datetime(2021, 10, 27)], [DEP]
        for t in r['trades']: x.append(t['close']); y.append(t['bal_after'])
        main = k in ('MAIN_M4', 'SIMPLE_M4')
        ax.step(x, y, where='post', lw=2 if main else 0.8, alpha=1 if main or k in CTRL else .7, ls='--' if k in CTRL else '-', label=k)
    ax.axhline(DEP, color='grey', lw=.7, ls='--'); ax.set_title(f'US100 CRT 1.5R · 1% risk · closed balance · {title}', fontsize=10); ax.legend(fontsize=7, ncol=4)
fig.tight_layout(); fig.savefig(ROOT / 'balance.png', dpi=130)
