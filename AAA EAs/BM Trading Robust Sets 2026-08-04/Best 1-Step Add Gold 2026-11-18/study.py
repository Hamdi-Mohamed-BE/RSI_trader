"""Owner 2026-11-18: "XAU Regime Switch (M5) and Asia Breakout (H1): which one is worth adding to the profile ... we can replace some EA already in there".
Streams (2021-10-07 -> 2026-10-06, 5-minute marks, native long-history runs):
  - B9 = the current Best 1-Step (9 EAs, weekend / holiday flat) = Multi Firm Funded 2026-11-17/INPUTS_B9.json (from Best 1-Step UK100 Monday INPUTS-B1XM).
  - xau-regime-switch + asia-breakout from Prop Portfolio Selection 2026-11-03/INPUTS-FULL.json (installer effective inputs), with the SAME weekend / holiday flat
    transform (Best 1-Step Search 2026-11-11/weekend_flat.py) because the profile closes everything before weekends and holidays.
Variants: B9, +RS, +AB, +RS+AB, RSI VWAP replaced by RS / AB / RS+AB. Closed-trade R stats (data_split dev / val / OOS on this window, years, last 12 months,
worst day, DD, daily correlation, three-way MC) + the multi-firm funded engine (Multi Firm Funded 2026-11-17/sim.py, VARIANT files).
In-sample; the two EAs were chosen after seeing today's gold drop (hindsight). python study.py streams | stats"""
import importlib.util, json, sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

H = Path(__file__).resolve().parent; B = H.parent; MF = B / 'Multi Firm Funded 2026-11-17'; sys.path.insert(0, str(B.parent / 'Calyx Research Pipeline'))
import robustness  # noqa: E402

NEW = ('xau-regime-switch', 'asia-breakout')
VARIANTS = {'B9': ([], []), 'B9_RS': (['xau-regime-switch'], []), 'B9_AB': (['asia-breakout'], []), 'B9_RSAB': (list(NEW), []),
            'B8_RS': (['xau-regime-switch'], ['xau-rsi-vwap']), 'B8_AB': (['asia-breakout'], ['xau-rsi-vwap']), 'B8_RSAB': (list(NEW), ['xau-rsi-vwap'])}


def load(name, path):
    s = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


def R(c): return (c['unit_gross'] + c['unit_commission'] + c['unit_swap']) / c['unit_risk']


def streams():
    b9 = json.loads((MF / 'INPUTS_B9.json').read_text()); full = json.loads((B / 'Prop Portfolio Selection 2026-11-03/INPUTS-FULL.json').read_text())
    assert b9['window'] == full['window'], (b9['window'], full['window'])
    end = b9['year_end_exclusive_epoch']; W = load('weekend_flat', B / 'Best 1-Step Search 2026-11-11/weekend_flat.py'); new = []; st = Counter()
    for c in (x for x in full['candidates'] if x['ea'] in NEW):
        cls = W.sym_class(c['symbol']); cl = c['cl'] if c['cl'] is not None else end
        if W.in_flat(c['op'], cls): st[c['ea'] + ' removed'] += 1; continue
        f = W.first_flat(c['op'], cl, cls)
        if f is None: new.append(c); st[c['ea'] + ' unchanged'] += 1; continue
        x = dict(c); marks = [mk for mk in c['marks'] if mk[0] < f]; g = marks[-1][1] if marks else 0.0; frac = (f - c['op']) / max(1, cl - c['op'])
        x.update(cl=f, unit_gross=g, unit_swap=c['unit_swap'] * frac, marks=marks, weekend_flat_cut=True); new.append(x); st[c['ea'] + ' cut'] += 1
    raw = {ea: round(sum(R(c) for c in full['candidates'] if c['ea'] == ea), 1) for ea in NEW}
    flat = {ea: round(sum(R(c) for c in new if c['ea'] == ea), 1) for ea in NEW}
    meta = {k: v for k, v in b9.items() if k != 'candidates'}
    for name, (add, drop) in VARIANTS.items():
        cands = [c for c in b9['candidates'] if c['ea'] not in drop] + [c for c in new if c['ea'] in add]
        (MF / f'INPUTS_{name}.json').write_text(json.dumps(dict(meta, candidates=cands), separators=(',', ':')), encoding='utf-8')
    out = dict(weekend_transform=dict(st), total_r_raw=raw, total_r_weekend_flat=flat)
    (H / 'STREAMS.json').write_text(json.dumps(out, indent=1), encoding='utf-8'); print(json.dumps(out, indent=1))


END = 1791237600.0   # window end exclusive (2026-10-06 Prague midnight); a trade still open at the end is booked there, as in the source ledgers


def day(ts): return datetime.fromtimestamp(ts if ts is not None else END - 1, timezone.utc).strftime('%Y-%m-%d')


def stats_of(cands, a, b):
    x = sorted(((c['cl'] or END - 1, R(c)) for c in cands if a <= day(c['op']) < b), key=lambda t: t[0])
    if not x: return {}
    gw = sum(r for _, r in x if r > 0); gl = -sum(r for _, r in x if r < 0); eq = pk = dd = 0.0; days = defaultdict(float)
    for t, r in x: eq += r; pk = max(pk, eq); dd = max(dd, pk - eq); days[day(t)] += r
    months = (datetime.fromisoformat(b) - datetime.fromisoformat(a)).days / 30.4375
    return dict(trades=len(x), per_month=round(len(x) / months, 1), per_day=round(len(x) / months / 21, 2), total_r=round(sum(r for _, r in x), 1),
                pf=round(gw / gl, 3), avg_r=round(sum(r for _, r in x) / len(x), 3), closed_dd_r=round(dd, 1), worst_day_r=round(min(days.values()), 2))


def stats():
    W = {'all': ('2021-10-07', '2026-10-06'), 'dev': ('2021-10-07', '2023-10-06'), 'val': ('2023-10-06', '2024-10-06'), 'oos': ('2024-10-06', '2026-10-06'),
         'last_12m': ('2025-10-06', '2026-10-06'), '2022': ('2022-01-01', '2023-01-01'), '2023': ('2023-01-01', '2024-01-01'), '2024': ('2024-01-01', '2025-01-01'),
         '2025': ('2025-01-01', '2026-01-01')}
    out = {}; base = json.loads((MF / 'INPUTS_B9.json').read_text())['candidates']
    bd = defaultdict(float)
    for c in base: bd[day(c['cl'])] += R(c)
    for name in VARIANTS:
        cands = json.loads((MF / f'INPUTS_{name}.json').read_text())['candidates']
        seq = [R(c) for c in sorted(cands, key=lambda c: c['cl'] or END - 1)]; tw = robustness.three_monte_carlo(seq, runs=1000, seed=20261104)
        out[name] = dict({w: stats_of(cands, *v) for w, v in W.items()}, mc=dict(resample_red=tw['resample']['red_pct'], randomize_red=tw['randomize']['both']['red_pct']))
    for ea in NEW + ('xau-rsi-vwap',):
        src = 'INPUTS_B9_RSAB.json' if ea in NEW else 'INPUTS_B9.json'
        cands = [c for c in json.loads((MF / src).read_text())['candidates'] if c['ea'] == ea]
        d = defaultdict(float)
        for c in cands: d[day(c['cl'])] += R(c)
        ks = sorted(set(d) | set(bd)); import statistics
        xs = [d.get(k, 0.0) for k in ks]; ys = [bd.get(k, 0.0) - (d.get(k, 0.0) if ea == 'xau-rsi-vwap' else 0.0) for k in ks]
        corr = statistics.correlation(xs, ys)
        gold = defaultdict(float)
        for c in base:
            if c['symbol'] == 'XAUUSD' and c['ea'] != ea: gold[day(c['cl'])] += R(c)
        corr_gold = statistics.correlation(xs, [gold.get(k, 0.0) for k in ks])
        out['ea_' + ea] = dict({w: stats_of(cands, *v) for w, v in W.items()}, daily_corr_with_rest=round(corr, 3), daily_corr_with_other_gold=round(corr_gold, 3))
    (H / 'STATS.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    for k, v in out.items():
        print(k)
        for w in ('all', 'dev', 'val', 'oos', 'last_12m'):
            s = v[w]; print('   %-9s n=%5d %5.1f/mo R=%+6.1f PF=%.3f avgR=%+.3f DD=%5.1fR worstDay=%+.2f' % (w, s['trades'], s['per_month'], s['total_r'], s['pf'], s['avg_r'], s['closed_dd_r'], s['worst_day_r']))
        print('   years', {y: v[y].get('total_r') for y in ('2022', '2023', '2024', '2025')}, v.get('mc', ''), {k2: v[k2] for k2 in v if k2.startswith('daily')})


if __name__ == '__main__':
    {'streams': streams, 'stats': stats}[sys.argv[1]]()
