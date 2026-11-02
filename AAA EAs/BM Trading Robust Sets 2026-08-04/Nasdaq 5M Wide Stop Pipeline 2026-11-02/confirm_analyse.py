"""Nasdaq 5M wide-stop pipeline, Model 4 confirmation: the Model 1 search finalists re-run on native Model 4 (real / generated ticks).
Same segments, yearly table and Monte Carlo (2,000 x 1 year, 4-week blocks, seed 20261102) as analyse.py, plus a Model 1 vs Model 4
trade match (same entry minute and direction). -> CONFIRM.md, CONFIRM.json, confirm_balance.png
Run from AAA EAs/EA store:  uv run --with matplotlib python "<study>/confirm_analyse.py" A6_M1_DION P060_M1_DION P130_M6_DION"""
import gzip, json, random, sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ROOT = Path(__file__).resolve().parent
SEG = {'dev': ('2019-01-01', '2023-11-01'), 'val': ('2023-11-01', '2024-11-01'), 'oos': ('2024-11-01', '2026-11-01'),
       'last12': ('2025-11-01', '2026-11-01'), 'all': ('2019-01-01', '2026-11-01')}
LABEL = {'dev': 'Development 2019-23', 'val': 'Validation 2023-24', 'oos': 'OOS 2024-26', 'last12': 'Last 12 months', 'all': 'All 2019-26'}
DEP, RISK = 10000.0, 0.01
NAMES = sys.argv[1:] or ['A6_M1_DION', 'P060_M1_DION', 'P130_M6_DION']


def load(case):
    d = ROOT / 'native' / f'nw-USTEC-{case}-full'
    if not (d / 'run.json').exists(): return None
    meta = json.loads((d / 'run.json').read_text())
    if not meta.get('ok'): return None
    t = json.loads(gzip.decompress((d / 'trades.json.gz').read_bytes()))
    for x in t: x['open'] = datetime.fromisoformat(x['open_time']); x['close'] = datetime.fromisoformat(x['close_time'])
    t.sort(key=lambda x: x['close']); bal = DEP
    for x in t: x['R'] = x['net_profit'] / (RISK * bal); x['b0'] = bal; bal += x['net_profit']; x['b1'] = bal
    return dict(meta=meta, trades=t)


def seg(t, a, b):
    A, B = datetime.fromisoformat(a), datetime.fromisoformat(b); ts = [x for x in t if A <= x['open'] < B]
    days = (B - A).days; wk = sum(1 for i in range(days) if (A + timedelta(days=i)).weekday() < 5)
    R = [x['R'] for x in ts]; p = [x['net_profit'] for x in ts]; gp, gl = sum(v for v in p if v > 0), -sum(v for v in p if v < 0)
    b0 = ts[0]['b0'] if ts else DEP; b1 = ts[-1]['b1'] if ts else DEP; peak = bal = b0; dd = 0.0
    for x in ts: bal += x['net_profit']; peak = max(peak, bal); dd = max(dd, (peak - bal) / peak * 100)
    return dict(n=len(ts), per_month=round(len(ts) / (days / 30.4375), 2), per_week=round(len(ts) / (days / 7), 2), per_day=round(len(ts) / wk, 3),
                win=round(100 * sum(v > 0 for v in p) / len(p), 1) if p else None, pf=round(gp / gl, 3) if gl else None, net_R=round(sum(R), 1),
                ret=round((b1 / b0 - 1) * 100, 1), dd=round(dd, 1))


def years(t):
    out = {}
    for y in range(2019, 2027):
        ts = [x for x in t if x['open'].year == y]
        if ts: out[y] = round((ts[-1]['b1'] / ts[0]['b0'] - 1) * 100, 1)
    return out


def mc(trades, paths=2000, horizon_weeks=52, seed=20261102):
    start = datetime(2019, 1, 7); blocks = defaultdict(list)
    for x in trades: blocks[(x['close'] - start).days // 28].append(x['R'])
    keys = sorted(blocks); allb = [blocks.get(i, []) for i in range(keys[0], keys[-1] + 1)]
    rng = random.Random(seed); rets, dds, loss = [], [], 0
    for _ in range(paths):
        bal = peak = 1.0; dd = 0.0
        for _ in range(horizon_weeks // 4):
            for r in rng.choice(allb):
                bal *= 1 + r * RISK; peak = max(peak, bal); dd = max(dd, 1 - bal / peak)
        rets.append(bal - 1); dds.append(dd); loss += bal < 1
    q = lambda v, p: round(100 * sorted(v)[int(p * (len(v) - 1))], 1)  # noqa: E731
    return dict(paths=paths, p_loss_year=round(loss / paths, 3), ret_p5=q(rets, .05), ret_p10=q(rets, .1), ret_p50=q(rets, .5), ret_p90=q(rets, .9),
                dd_p50=q(dds, .5), dd_p95=q(dds, .95), dd_max=round(100 * max(dds), 1), p_dd_over_20=round(sum(d > .2 for d in dds) / paths, 3))


def match(m1, m4):
    key = lambda x: (x['open'].replace(second=0), x['side'])  # noqa: E731
    a = {key(x): x for x in m1}; b = {key(x): x for x in m4}; common = set(a) & set(b)
    dr = [b[k]['R'] - a[k]['R'] for k in common]
    return dict(m1=len(m1), m4=len(m4), matched=len(common), share_m4=round(len(common) / len(m4), 3) if m4 else None,
                mean_dR=round(sum(dr) / len(dr), 3) if dr else None, only_m1=len(set(a) - common), only_m4=len(set(b) - common))


res = {}
for k in NAMES:
    r4, r1 = load(k + '_M4'), load(k)
    if not r4: print('missing Model 4 run for', k); continue
    s4 = {s: seg(r4['trades'], *w) for s, w in SEG.items()}; s1 = {s: seg(r1['trades'], *w) for s, w in SEG.items()} if r1 else None
    res[k] = dict(native_m4=r4['meta']['metrics'], m4=s4, m1=s1, years_m4=years(r4['trades']), years_m1=years(r1['trades']) if r1 else None,
                  mc_m4=mc(r4['trades']), match=match(r1['trades'], r4['trades']) if r1 else None, trades=r4['trades'])

f = lambda x: '–' if x is None else x  # noqa: E731
md = ['# Nasdaq 5M wide-stop: Model 4 confirmation (generated by confirm_analyse.py)', '',
      'USTEC M5, production EX5 fe9f391db5af + preset, inputs only, native MT5 **Model 4** (real ticks from 2026-01, generated before), 1% risk, '
      '$10k, 150 ms, 2019-01-01 -> 2026-11-01. Parts by entry date. All parts were viewed during the Model 1 search: OOS is retrospective.', '']
for k, v in res.items():
    nm = v['native_m4']
    md += [f'## {k}', f"Native report: net {nm['return_pct']:+}% , PF {nm['profit_factor']}, {nm['trades']} trades, equity DD (MT5 maximal) "
           f"{nm['max_drawdown_pct']}%, history quality {nm['history_quality']}.", '',
           '| Part | Trades | /month | /week | /day | Win % | PF M4 (M1) | Net R M4 (M1) | Return M4 (M1) | Closed DD M4 (M1) |',
           '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for s in SEG:
        a = v['m4'][s]; b = v['m1'][s] if v['m1'] else {}
        md.append(f"| {LABEL[s]} | {a['n']} | {a['per_month']} | {a['per_week']} | {a['per_day']} | {f(a['win'])} | {f(a['pf'])} ({f(b.get('pf'))}) | "
                  f"{a['net_R']} ({f(b.get('net_R'))}) | {a['ret']:+}% ({f(b.get('ret'))}%) | {a['dd']}% ({f(b.get('dd'))}%) |")
    y4, y1 = v['years_m4'], v['years_m1'] or {}
    md += ['', '| Year | ' + ' | '.join(map(str, y4)) + ' |', '|---|' + '---:|' * len(y4),
           '| Model 4 | ' + ' | '.join(f'{x:+}%' for x in y4.values()) + ' |', '| Model 1 | ' + ' | '.join(f"{f(y1.get(y))}%" for y in y4) + ' |']
    m = v['mc_m4']; mt = v['match']
    md += ['', f"Monte Carlo (Model 4 ledger, 2,000 x 1 year, 4-week blocks): P(losing year) {m['p_loss_year']:.0%}; return p5 / p10 / p50 / p90 "
           f"{m['ret_p5']}% / {m['ret_p10']}% / {m['ret_p50']}% / {m['ret_p90']}%; closed DD p50 / p95 / max {m['dd_p50']}% / {m['dd_p95']}% / {m['dd_max']}%; "
           f"P(DD > 20%) {m['p_dd_over_20']:.0%}."]
    if mt: md.append(f"Model 1 vs Model 4: {mt['m1']} vs {mt['m4']} trades, {mt['matched']} same entry minute + direction ({mt['share_m4']:.0%} of Model 4), "
                     f"mean R difference on matched trades {mt['mean_dR']:+}.")
    md.append('')
(ROOT / 'CONFIRM.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
(ROOT / 'CONFIRM.json').write_text(json.dumps({k: {x: y for x, y in v.items() if x != 'trades'} for k, v in res.items()}, indent=1, default=str), encoding='utf-8')
print('\n'.join(md))

import matplotlib; matplotlib.use('Agg')  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
fig, ax = plt.subplots(figsize=(12, 5))
for i, s in enumerate(['dev', 'val', 'oos']):
    ax.axvspan(*(datetime.fromisoformat(x) for x in SEG[s]), color=['#f2f2f2', '#e6eef7', '#e8f5e9'][i], zorder=0)
for k, v in res.items():
    t = v['trades']; ax.step([datetime(2019, 1, 1)] + [x['close'] for x in t], [DEP] + [x['b1'] for x in t], where='post', lw=1.6,
                             label=k + (' (production)' if k == 'P060_M1_DION' else ''))
ax.set_yscale('log'); ax.legend(fontsize=8)
ax.set_title('Nasdaq 5M · USTEC M5 · native Model 4 · 1% risk · closed balance (log) · dev / val / OOS shaded', fontsize=10)
fig.tight_layout(); fig.savefig(ROOT / 'confirm_balance.png', dpi=130)
