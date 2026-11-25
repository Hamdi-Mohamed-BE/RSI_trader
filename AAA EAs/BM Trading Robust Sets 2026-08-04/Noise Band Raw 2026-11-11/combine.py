"""One account running the best setting per index (WIDE on all three; PAPER lost everywhere), with per-index risk weights. Replay of the native WIDE ledgers
(R per trade = net / 1% of that run's balance at entry), compounded on one balance, trades ordered by close time. Closed-trade drawdown (every trade is flat the same day;
intraday open risk of up to 3 simultaneous trades is not marked). Worst day = sum of that day's trade results in % of balance. python combine.py"""
import importlib.util, json, math, os, sys
from collections import defaultdict
os.environ['EA_STORE_DISABLE_MT5'] = '1'; sys.path.insert(0, '../../Calyx Research Pipeline')
s = importlib.util.spec_from_file_location('st', 'study.py'); m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
import robustness  # noqa: E402
L = {sym: m.ledger(sym, 'WIDE') for sym in m.ASSETS}
MIXES = {'A  all 3 at 1% each': dict(USTEC=1.0, US500=1.0, DE30=1.0),
         'B  Nasdaq 1.5% + S&P 0.75% (best-match risks)': dict(USTEC=1.5, US500=0.75),
         'C  B + DAX 0.5%': dict(USTEC=1.5, US500=0.75, DE30=0.5),
         'D  Nasdaq 1% + S&P 0.5% + DAX 0.25%': dict(USTEC=1.0, US500=0.5, DE30=0.25)}
WIN = {'all 2019-07': ('2019-07-16', m.END), 'from 2021': ('2021-01-01', m.END), 'dev': ('2019-07-16', '2023-11-21'), 'val': ('2023-11-21', '2024-11-21'),
       'oos': ('2024-11-21', m.END), 'last 12m': ('2025-11-21', m.END)}
out = {}
for name, w in MIXES.items():
    rows = sorted([dict(r, w=w[s_]) for s_ in w for r in L[s_]], key=lambda r: r['c']); res = {}
    for wn, (a, b) in WIN.items():
        x = [r for r in rows if a <= r['o'][:10] < b]; bal = pk = 1.0; dd = 0; day = defaultdict(float); yr = defaultdict(lambda: 1.0); mon = defaultdict(float)
        for r in x:
            p = r['w'] / 100 * r['r']; day[r['c'][:10]] += p; yr[r['c'][:4]] *= 1 + p; mon[r['c'][:7]] += p; bal *= 1 + p; pk = max(pk, bal); dd = max(dd, 1 - bal / pk)
        P = [r['w'] * r['r'] for r in x]; g = sum(v for v in P if v > 0); l = -sum(v for v in P if v < 0)
        months = (m.datetime.fromisoformat(b) - m.datetime.fromisoformat(a)).days / 30.4375
        res[wn] = dict(trades=len(x), per_month=round(len(x) / months, 1), per_day=round(len(x) / months / 21.7, 2), ret_pct=round(100 * (bal - 1), 1), pf=round(g / l, 2),
                       win=round(100 * sum(v > 0 for v in P) / len(P), 1), closed_dd_pct=round(100 * dd, 1), worst_day_pct=round(100 * min(day.values()), 2),
                       losing_months_pct=round(100 * sum(v <= 0 for v in mon.values()) / len(mon), 1), cagr=round(100 * (bal ** (12 / months) - 1), 1))
        if wn == 'all 2019-07': res['years'] = {k: round(100 * (v - 1), 1) for k, v in sorted(yr.items())}
    mc = robustness.three_monte_carlo([r['w'] * r['r'] for r in rows], runs=1000, seed=20261104)
    res['mc'] = dict(resample_red=mc['resample']['red_pct'], clumped=mc['reshuffle']['real_drawdown_worse_than_pct'])   # randomize adds a fixed cost per trade in input units -> not meaningful for weighted mixes
    out[name] = res
json.dump(out, open('COMBINE.json', 'w'), indent=1)
for k, v in out.items():
    print(k)
    for wn in WIN: print('   ', f'{wn:12s}', v[wn])
    print('    years', v['years'], 'mc', v['mc'])
