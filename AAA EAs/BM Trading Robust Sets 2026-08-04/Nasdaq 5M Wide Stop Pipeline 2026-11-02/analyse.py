"""Nasdaq 5M wide-stop pipeline: segment stats (development / validation / OOS by entry date), the frozen selection rules of PLAN.md,
plateau check, yearly table, Monte Carlo on the chosen version. -> RESULTS.md, RESULTS.json, balance.png
Run from AAA EAs/EA store:  uv run --with matplotlib python "<study>/analyse.py" """
import gzip, json, math, random, sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ROOT = Path(__file__).resolve().parent
VARS = json.loads((ROOT / 'VARIANTS.json').read_text(encoding='utf-8'))
SEG = {'dev': ('2019-01-01', '2023-11-01'), 'val': ('2023-11-01', '2024-11-01'), 'oos': ('2024-11-01', '2026-11-01'), 'all': ('2019-01-01', '2026-11-01'),
       'last12': ('2025-11-01', '2026-11-01')}
DEP, RISK = 10000.0, 0.01
BASE = 'P060_M1_DION'                                     # = current production preset


def load(name):
    d = ROOT / 'native' / f'nw-USTEC-{name}-full'
    if not (d / 'run.json').exists(): return None
    meta = json.loads((d / 'run.json').read_text())
    t = json.loads(gzip.decompress((d / 'trades.json.gz').read_bytes()))
    for x in t: x['open'] = datetime.fromisoformat(x['open_time']); x['close'] = datetime.fromisoformat(x['close_time'])
    t.sort(key=lambda x: x['close']); bal = DEP
    for x in t: x['R'] = x['net_profit'] / (RISK * bal); x['b0'] = bal; bal += x['net_profit']; x['b1'] = bal
    return dict(meta=meta, trades=t)


def seg(t, a, b):
    A, B = datetime.fromisoformat(a), datetime.fromisoformat(b); ts = [x for x in t if A <= x['open'] < B]
    days = (B - A).days; wk = sum(1 for i in range(days) if (A + timedelta(days=i)).weekday() < 5)
    R = [x['R'] for x in ts]; p = [x['net_profit'] for x in ts]; gp, gl = sum(v for v in p if v > 0), -sum(v for v in p if v < 0)
    cum = pk = ddr = 0.0
    for r in R: cum += r; pk = max(pk, cum); ddr = max(ddr, pk - cum)
    b0 = ts[0]['b0'] if ts else DEP; b1 = ts[-1]['b1'] if ts else DEP; peak = b0; dd = 0.0; bal = b0
    for x in ts: bal += x['net_profit']; peak = max(peak, bal); dd = max(dd, (peak - bal) / peak * 100)
    return dict(n=len(ts), per_month=round(len(ts) / (days / 30.4375), 2), per_week=round(len(ts) / (days / 7), 2), per_day=round(len(ts) / wk, 3) if wk else None,
                win=round(100 * sum(v > 0 for v in p) / len(p), 1) if p else None, pf=round(gp / gl, 3) if gl else None, net_R=round(sum(R), 1),
                dd_R=round(ddr, 1), ret=round((b1 / b0 - 1) * 100, 1), dd=round(dd, 1))


runs = {k: load(k) for k in VARS}; runs = {k: v for k, v in runs.items() if v}
stats = {k: {s: seg(r['trades'], *w) for s, w in SEG.items()} for k, r in runs.items()}
for k, r in runs.items(): stats[k]['native'] = r['meta']['metrics']


def neighbours(k):
    if not k.startswith('P'): return []
    st, m, di = k.split('_'); order = ['P040', 'P060', 'P080', 'P100', 'P115', 'P130', 'P150', 'P200']; i = order.index(st)
    return [f'{order[j]}_{m}_{di}' for j in (i - 1, i + 1) if 0 <= j < len(order)]


elig = {}
for k, s in stats.items():
    d = s['dev']; ok = d['n'] >= 200 and (d['pf'] or 0) >= 1.15 and d['net_R'] > 0
    plateau = all((stats.get(n, {}).get('dev', {}).get('pf') or 0) >= 1.10 for n in neighbours(k)) if ok else False
    elig[k] = dict(eligible=ok, plateau=plateau, score=round(d['net_R'] / max(d['dd_R'], 1), 3))
cands = sorted([k for k, e in elig.items() if e['eligible'] and e['plateau']], key=lambda k: -elig[k]['score'])
chosen = cands[0] if cands else None
verdict = None
if chosen:
    v = stats[chosen]['val']; verdict = 'PASS_VALIDATION' if v['net_R'] > 0 and (v['pf'] or 0) >= 1.10 else 'REJECTED_AT_VALIDATION'


def mc(trades, paths=2000, horizon_weeks=52, seed=20261102):
    """4-week block bootstrap of the full ledger (R per trade at 1% risk, compounding)."""
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
    return dict(paths=paths, horizon='1 year', p_loss_year=round(loss / paths, 3), ret_p10=q(rets, .1), ret_p50=q(rets, .5), ret_p90=q(rets, .9),
                dd_p50=q(dds, .5), dd_p95=q(dds, .95), dd_max=round(100 * max(dds), 1))


mcs = {k: mc(runs[k]['trades']) for k in {BASE, chosen} if k and k in runs}


def years(k):
    out = {}; t = runs[k]['trades']
    for y in range(2019, 2027):
        ts = [x for x in t if x['open'].year == y]
        if ts: b0 = ts[0]['b0']; out[y] = round((ts[-1]['b1'] / b0 - 1) * 100, 1)
    return out


f = lambda x: '–' if x is None else x  # noqa: E731
md = ['# Nasdaq 5M wide-stop pipeline: results (generated by analyse.py)', '',
      'USTEC M5, production EX5 + preset, inputs only, native MT5 Model 1, 1% risk, $10k, 2019-01-01 -> 2026-11-01. Parts split by trade entry date.',
      f'Baseline (current production) = {BASE}. Selection on development only (PLAN.md).', '',
      f"**Chosen:** {chosen} -> **{verdict}**" if chosen else '**No version met the development rules (PF >= 1.15, >= 200 trades, plateau).**', '',
      '## Top 25 by development score (net R / max DD R) + baseline',
      '| Version | Dev n (/wk) | Dev PF | Dev net R | Dev DD R | Plateau | Val PF / R | **OOS PF / R / return** | All 2019-26 return / PF / win / DD | Trades/week |',
      '|---|---:|---:|---:|---:|---|---:|---:|---:|---:|']
for k in sorted(stats, key=lambda k: -elig[k]['score'])[:25] + ([BASE] if BASE in stats else []):
    s = stats[k]; d, v, o, a = s['dev'], s['val'], s['oos'], s['all']
    md.append(f"| {'**' + k + '**' if k in (chosen, BASE) else k} | {d['n']} ({d['per_week']}) | {f(d['pf'])} | {d['net_R']} | {d['dd_R']} | "
              f"{'yes' if elig[k]['plateau'] else 'no' if elig[k]['eligible'] else '–'} | {f(v['pf'])} / {v['net_R']} | {f(o['pf'])} / {o['net_R']} / {o['ret']:+}% | "
              f"{a['ret']:+}% / {f(a['pf'])} / {f(a['win'])}% / {a['dd']}% | {a['per_week']} |")
md += ['', '## Stop width x management (DI ON): development PF / OOS PF', '| Stop | ' + ' | '.join(f'M{i}' for i in range(1, 8)) + ' |', '|---|' + '---:|' * 7]
for st in ['P040', 'P060', 'P080', 'P100', 'P115', 'P130', 'P150', 'P200']:
    md.append(f"| {st[1]}.{st[2:]}% | " + ' | '.join(f"{f(stats.get(f'{st}_M{i}_DION', {}).get('dev', {}).get('pf'))} / {f(stats.get(f'{st}_M{i}_DION', {}).get('oos', {}).get('pf'))}" for i in range(1, 8)) + ' |')
for k in [x for x in (BASE, chosen) if x]:
    md += ['', f'## {k}: every part', '| Part | Trades | /month | /week | /day | Win % | PF | Net R | Return | Closed DD |', '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for sname, label in (('dev', 'Development 2019-23'), ('val', 'Validation 2023-24'), ('oos', 'OOS 2024-26'), ('last12', 'Last 12 months'), ('all', 'All 2019-26')):
        x = stats[k][sname]; md.append(f"| {label} | {x['n']} | {x['per_month']} | {x['per_week']} | {f(x['per_day'])} | {f(x['win'])} | {f(x['pf'])} | {x['net_R']} | {x['ret']:+}% | {x['dd']}% |")
    md.append('| Year | ' + ' | '.join(str(y) for y in years(k)) + ' |'); md.append('|---|' + '---:|' * len(years(k)))
    md.append('| Return | ' + ' | '.join(f'{v:+}%' for v in years(k).values()) + ' |')
    if k in mcs: m = mcs[k]; md.append(f"\nMonte Carlo (2,000 x 1 year, 4-week blocks): P(losing year) {m['p_loss_year']:.0%}; return p10 / p50 / p90 {m['ret_p10']}% / {m['ret_p50']}% / {m['ret_p90']}%; max DD p50 / p95 {m['dd_p50']}% / {m['dd_p95']}%.")
(ROOT / 'RESULTS.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
(ROOT / 'RESULTS.json').write_text(json.dumps(dict(stats=stats, eligibility=elig, candidates=cands[:20], chosen=chosen, verdict=verdict, monte_carlo=mcs), indent=1, default=str), encoding='utf-8')
print('\n'.join(md))

import matplotlib; matplotlib.use('Agg')  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
fig, ax = plt.subplots(figsize=(12, 5))
for i, (n, (a, b)) in enumerate(list(SEG.items())[:3]):
    ax.axvspan(datetime.fromisoformat(a), datetime.fromisoformat(b), color=['#f2f2f2', '#e6eef7', '#e8f5e9'][i], zorder=0)
for k in [x for x in (BASE, chosen) if x] + cands[1:4]:
    x = [datetime(2019, 1, 1)] + [t['close'] for t in runs[k]['trades']]; y = [DEP] + [t['b1'] for t in runs[k]['trades']]
    ax.step(x, y, where='post', lw=2 if k in (BASE, chosen) else .8, label=k + (' (production)' if k == BASE else ' (chosen)' if k == chosen else ''))
ax.set_yscale('log'); ax.legend(fontsize=8); ax.set_title('Nasdaq 5M · USTEC M5 · 1% risk · closed balance (log) · dev / val / OOS shaded', fontsize=10)
fig.tight_layout(); fig.savefig(ROOT / 'balance.png', dpi=130)
