"""Metrics, gate, yearly split, controls and balance graph for the gold 1am NY ORB raw study (adapted from the FTSE three-setup raw study).
Run from AAA EAs/EA store:  uv run --with matplotlib python "<study>/analyse.py"   -> RESULTS.md, RESULTS.json, balance.png"""
import gzip, json, math, re, sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1] / 'EA store'))
from app.mt5_evidence_jobs import _metric, _read_report  # noqa: E402

CFG = json.loads((ROOT / 'run-config.json').read_text(encoding='utf-8'))
END = datetime.strptime(CFG['end_date'], '%Y.%m.%d')
DEP, RISK = 10000.0, float(CFG['common_inputs']['InpRiskPercent']) / 100
MAIN, CONTROLS, PERIODS = list(CFG['variants']), list(CFG['controls']), list(CFG['periods'])
LABEL = {k: v['label'] for grp in ('variants', 'controls') for k, v in CFG[grp].items()}


def start(per): return datetime.strptime(CFG['periods'][per], '%Y.%m.%d')


def load(v, per):
    d = ROOT / 'native' / f'nw-XAUUSD-{v}-{per}'
    if not (d / 'run.json').exists(): return None, [], None, None
    meta = json.loads((d / 'run.json').read_text())
    trades = json.loads(gzip.decompress((d / 'trades.json.gz').read_bytes()))
    for t in trades:
        t['open'] = datetime.fromisoformat(t['open_time']); t['close'] = datetime.fromisoformat(t['close_time'])
    trades.sort(key=lambda t: t['close'])
    j = gzip.decompress((d / 'journal.txt.gz').read_bytes()).decode('utf-8', 'ignore')
    m = re.findall(r'GORB_SUMMARY ([^\r\n]*)', j)
    counters = {k: int(x) for k, x in (kv.split('=') for kv in m[-1].split())} if m else None
    if counters is not None:   # 10018 = market closed at the bar open (entry skipped, harmless); anything else is a real failure
        counters['market_closed_skips'] = counters.get('market_closed', 0); counters['other_place_fails'] = counters.get('place_fails', 0)
    rep = next(iter(sorted(d.glob('*.htm.gz'))), None); rel = None
    if rep:
        tmp = d / '_report.htm'; tmp.write_bytes(gzip.decompress(rep.read_bytes()))
        try: rel = float(re.search(r'([\d.]+)\s*%', _metric(_read_report(tmp), 'Equity Drawdown Relative')).group(1))
        except Exception: rel = None
        tmp.unlink()
    return meta, trades, counters, rel


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


def stats(trades, per, meta, rel):
    S = start(per); p = [t['net_profit'] for t in trades]; days = (END - S).days
    weekdays = sum(1 for i in range(days) if (S + timedelta(days=i)).weekday() < 5)
    gp, gl = sum(x for x in p if x > 0), -sum(x for x in p if x < 0)
    bal, peak, bdd, R = DEP, DEP, 0.0, []
    for t in trades:
        R.append(t['net_profit'] / (RISK * bal)); bal += t['net_profit']; peak = max(peak, bal); bdd = max(bdd, (peak - bal) / peak * 100)
    daily = defaultdict(float)
    for t in trades: daily[t['close'].date()] += t['net_profit']
    eq, rets = DEP, []
    for i in range(days):
        d = (S + timedelta(days=i)).date()
        if d.weekday() < 5 or d in daily: rets.append(daily.get(d, 0.0) / eq); eq += daily.get(d, 0.0)
    mean = sum(rets) / len(rets) if rets else 0; sd = math.sqrt(sum((r - mean) ** 2 for r in rets) / len(rets)) if rets else 0
    best5 = sum(sorted(daily.values(), reverse=True)[:5])
    aw, al, mw, ml = streaks(p)
    ex = defaultdict(int)
    for t in trades:
        c = (t.get('exit_comment') or '').lower()
        ex['TP' if c.startswith('tp') else 'SL' if c.startswith('sl') else 'time'] += 1
    m = (meta or {}).get('metrics', {})
    return dict(trades=len(p), per_month=round(len(p) / (days / 30.4375), 2), per_day=round(len(p) / weekdays, 3),
                ret=round(sum(p) / DEP * 100, 2), pf=round(gp / gl, 2) if gl else None, win=round(100 * sum(x > 0 for x in p) / len(p), 1) if p else None,
                avg_w=aw, avg_l=al, max_w=mw, max_l=ml, sharpe=round(mean / sd * math.sqrt(252), 2) if sd > 0 and len(p) >= 10 else None,
                bal_dd=round(bdd, 2), eq_dd_maximal=m.get('max_drawdown_pct'), eq_dd_relative=rel, mean_R=round(sum(R) / len(R), 3) if R else None,
                exits=dict(ex), net=round(sum(p), 2), costs=round(sum(t['total_costs'] for t in trades), 2),
                net_without_best5_days=round(sum(p) - best5, 2), longs=sum(1 for t in trades if t.get('side') == 'Long'),
                shorts=sum(1 for t in trades if t.get('side') == 'Short'))


rows, cnts, trades_by = {}, {}, {}
for per in PERIODS:
    for v in MAIN + CONTROLS:
        meta, trades, cnt, rel = load(v, per)
        if meta is None: continue
        rows[(v, per)] = dict(variant=v, period=per, **stats(trades, per, meta, rel), flags=meta.get('journal_flags'), real_ticks=meta.get('real_tick_lines'))
        cnts[(v, per)] = cnt; trades_by[(v, per)] = trades

f = lambda x, s='': '—' if x is None else f'{x}{s}'  # noqa: E731
HDR = ('| Version | Window | Trades | /month | /day | Return | PF | Win % | Avg win / loss streak (max) | Sharpe | Bal DD | Eq DD rel / max | Mean R | No 5 best days | Exits TP / SL / 24h |\n'
       '|---|---|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---|')


def line(v, per):
    r = rows[(v, per)]; e = r['exits']
    return (f"| **{v}** {LABEL[v]} | {per} | {r['trades']} | {r['per_month']} | {r['per_day']} | {r['ret']:+.2f}% | {f(r['pf'])} | {f(r['win'])} | "
            f"{r['avg_w']} / {r['avg_l']} ({r['max_w']} / {r['max_l']}) | {f(r['sharpe'])} | {r['bal_dd']}% | {f(r['eq_dd_relative'], '%')} / {f(r['eq_dd_maximal'], '%')} | "
            f"{f(r['mean_R'])} | ${r['net_without_best5_days']:+,.0f} | {e.get('TP', 0)} / {e.get('SL', 0)} / {e.get('time', 0)} |")


def table(keys, pers):
    return HDR + '\n' + '\n'.join(line(v, p) for v in keys for p in pers if (v, p) in rows)


def year_table(keys, per='max'):
    S = start(per); yrs = list(range(S.year, END.year + 1))
    out = ['| Version | ' + ' | '.join(str(y) for y in yrs) + ' | Positive years |', '|---|' + '---|' * len(yrs) + '---:|']
    for v in keys:
        if (v, per) not in rows: continue
        bal, cells, pos = DEP, [], 0
        for y in yrs:
            p = [t['net_profit'] for t in trades_by[(v, per)] if t['close'].year == y]
            gp, gl = sum(x for x in p if x > 0), -sum(x for x in p if x < 0)
            cells.append(f"{sum(p) / bal * 100:+.1f}% (PF {f(round(gp / gl, 2) if gl else None)}, n{len(p)})"); bal += sum(p); pos += sum(p) > 0
        out.append(f"| {v} | " + ' | '.join(cells) + f" | {pos}/{len(yrs)} |")
    return '\n'.join(out)


def side_table():
    out = ['| Window | Longs | Long net $ | Shorts | Short net $ |', '|---|---:|---:|---:|---:|']
    for per in PERIODS:
        ts = trades_by.get(('ORB05', per))
        if not ts: continue
        L = [t for t in ts if t.get('side') == 'Long']; Sh = [t for t in ts if t.get('side') == 'Short']
        out.append(f"| {per} | {len(L)} | {sum(t['net_profit'] for t in L):+,.0f} | {len(Sh)} | {sum(t['net_profit'] for t in Sh):+,.0f} |")
    return '\n'.join(out)


def mean_of(keys, per='5y'):
    rs = [rows[(k, per)] for k in keys if (k, per) in rows]
    return (sum(r['pf'] or 0 for r in rs) / len(rs), sum(r['mean_R'] or 0 for r in rs) / len(rs)) if rs else (None, None)


rnd5, rnd3 = mean_of(['RND1', 'RND2', 'RND3'], '5y'), mean_of(['RND1', 'RND2', 'RND3'], '3y')
gate = {}
for v in MAIN:
    if not all((v, p) in rows for p in ('3y', '5y')): continue
    r3, r5 = rows[(v, '3y')], rows[(v, '5y')]
    beats = rnd5[0] is not None and (r5['pf'] or 0) > rnd5[0] and (r5['mean_R'] or -9) > rnd5[1]
    clean = all(not any((rows[(v, p)]['flags'] or {}).get(k) for k in ('init_failed', 'critical')) and not (cnts[(v, p)] or {}).get('other_place_fails')
                and not (cnts[(v, p)] or {}).get('close_fails') for p in PERIODS if (v, p) in rows)
    g = dict(positive=r3['ret'] > 0 and r5['ret'] > 0, pf=(r3['pf'] or 0) >= 1.15 and (r5['pf'] or 0) >= 1.15, trades=r3['trades'] >= 30,
             beats_control=beats, best_day=r5['net_without_best5_days'] > 0, clean=clean)
    gate[v] = dict(checks=g, passed=all(g.values()))
yn = lambda b: 'yes' if b else '**no**'  # noqa: E731
gate_md = ('| Version | 3y and 5y positive | PF ≥ 1.15 both | ≥ 30 trades | Beats controls (5y) | Positive without 5 best days (5y) | Clean (only market-closed skips allowed) | Verdict |\n|---|---|---|---|---|---|---|---|\n' +
           '\n'.join(f"| {v} | {yn(g['checks']['positive'])} | {yn(g['checks']['pf'])} | {yn(g['checks']['trades'])} | {yn(g['checks']['beats_control'])} | "
                     f"{yn(g['checks']['best_day'])} | {yn(g['checks']['clean'])} | **{'PASS' if g['passed'] else 'FAIL'}** |" for v, g in gate.items()))
ctl_md = (f"Random-direction control means (RND1–3): 5y PF {f(rnd5[0] and round(rnd5[0], 2))}, mean R {f(rnd5[1] and round(rnd5[1], 3))}; "
          f"3y PF {f(rnd3[0] and round(rnd3[0], 2))}, mean R {f(rnd3[1] and round(rnd3[1], 3))}.")
cnt_md = ('| Run | NY days | Signals | Entries | Reverses | Force closes 06:00 | Skipped (stops / margin) | Market-closed / other place fails / close fails |\n|---|---:|---:|---:|---:|---:|---|---|\n' +
          '\n'.join(f"| {k[0]} {k[1]} | {c['days']} | {c['signals']} | {c['entries']} | {c['reverses']} | {c['force_closes']} | {c['skipped_stops']} / {c['skipped_margin']} | "
                    f"{c['market_closed_skips']} / {c['other_place_fails']} / {c['close_fails']} |" for k, c in cnts.items() if c))
ticks = sorted({x for r in rows.values() for x in (r['real_ticks'] or [])})
md = ['# Gold 1am New York ORB raw study — results (generated by analyse.py)', '',
      'XAUUSD (Exness CFD), M5, native MT5 Model 4, 150 ms, $10,000, 1% equity risk per trade (lots rounded up, max 2.0 lots), end 2026-10-27 exclusive. Rules: RULES.md.',
      'Eq DD "rel" = MT5 Equity Drawdown Relative; "max" = MT5 Equity Drawdown Maximal. "No 5 best days" = net profit minus the 5 best closing days.', '',
      '## Main version, every window', table(MAIN, PERIODS), '', '## Calendar years (5y window; each year % of its start balance)', year_table(MAIN + CONTROLS, '5y'), '',
      '## Long vs short (ORB05)', side_table(), '', '## Controls and sensitivities (3y and 5y)', table(CONTROLS, ['3y', '5y']), '', ctl_md, '', '## Raw gate', gate_md, '',
      '## Execution counters', cnt_md, '', 'Tick data lines: ' + '; '.join(ticks)]
(ROOT / 'RESULTS.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
(ROOT / 'RESULTS.json').write_text(json.dumps(dict(rows={f'{k[0]}|{k[1]}': v for k, v in rows.items()}, counters={f'{k[0]}|{k[1]}': v for k, v in cnts.items()},
                                                   gate=gate, controls=dict(rnd5=rnd5, rnd3=rnd3)), indent=2, default=str), encoding='utf-8')
print('\n'.join(md))

import matplotlib; matplotlib.use('Agg')  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
fig, axes = plt.subplots(2, 1, figsize=(12, 8.5))
style = {'ORB05': ('#1f77b4', 2.0), 'S_1R': ('#2ca02c', 1.2), 'S_2R': ('#ff7f0e', 1.2), 'S_NOREV': ('#9467bd', 1.0)}
for ax, keys, per, title in ((axes[0], MAIN, '5y', '5 years, main version'), (axes[1], MAIN + CONTROLS, '5y', '5 years, main version, random-direction controls and sensitivities')):
    for v in keys:
        ts = trades_by.get((v, per))
        if not ts: continue
        x, y, bal = [start(per)], [DEP], DEP
        for t in ts: bal += t['net_profit']; x.append(t['close']); y.append(bal)
        col, lw = style.get(v, ('#aaaaaa', 0.8))
        ax.step(x, y, where='post', label=f'{v}: {LABEL[v]}', lw=lw, color=col)
    ax.axhline(DEP, color='grey', lw=.7, ls='--'); ax.set_title(f'XAUUSD M5 gold 1am NY ORB · native MT5 Model 4 · 1% risk · closed balance · {title}', fontsize=10)
    ax.legend(fontsize=7)
fig.tight_layout(); fig.savefig(ROOT / 'balance.png', dpi=130)
