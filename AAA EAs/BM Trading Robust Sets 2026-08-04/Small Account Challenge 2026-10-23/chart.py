"""Balance fan charts for the Monte Carlo paths (same paths and sizing as sim.py) + native single paths.

python chart.py  ->  CHART-MC.png, CHART-NATIVE.png
"""
import bisect, json, math, random
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import sim

R = Path(__file__).resolve().parent
PANELS = [('PR9', 'F05'), ('PR9', 'F10'), ('FTMO17', 'F03'), ('FTMO17', 'F05')]
INK, MUTED, GRID, SURFACE, BLUE = '#0b0b0b', '#52514e', '#e4e3df', '#fcfcfb', '#2a78d6'
BAND_OUTER, BAND_INNER = '#cde2fb', '#86b6ef'


def trajectory(trades, t0, policy):
    """sim.path with the closed balance recorded at the end of every calendar day (bust freezes the balance)."""
    horizon = t0 + sim.HORIZON * sim.DAY; events = []
    for i, tr in enumerate(trades):
        if tr[0] >= horizon: break
        events.append((tr[0], 1, i)); events.append((tr[1], 0, i))
    events.sort()
    bal = sim.START_BAL; open_ = {}; busy = set(); daily = [bal] * (sim.HORIZON + 1); reached10 = False
    for t, kind, i in events:
        if t >= horizon: break
        op, cl, ea, sym, ur, un = trades[i]
        if kind == 0:
            if i not in open_: continue
            lots = open_.pop(i); busy.discard(ea); bal = round(bal + lots * un, 2)
            d = int((t - t0) // sim.DAY)
            for k in range(d, sim.HORIZON + 1): daily[k] = bal
            if bal >= 10000: reached10 = True
            if bal < sim.BUST: break
        else:
            if ea in busy: continue
            spec = sim.SPECS[sym]; budget = sim.risk_for(policy, bal) * bal
            lots = math.floor(budget / ur / spec['step'] + 1e-9) * spec['step']
            if lots < spec['min'] - 1e-9:
                if spec['min'] * ur <= 3 * budget + 1e-9: lots = spec['min']
                else: continue
            open_[i] = min(lots, spec['max']); busy.add(ea)
    return daily, bal, reached10


def quantile(sorted_vals, p): return sorted_vals[min(len(sorted_vals) - 1, int(p * len(sorted_vals)))]


def mc_fan():
    cache = {}
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), sharex=True, sharey=True, facecolor=SURFACE)
    for ax, (stream, pol) in zip(axes.flat, PANELS):
        if stream not in cache: cache[stream] = sim.load(stream)
        trades = cache[stream]; rng = random.Random(sim.MC_SEED); paths = []; hits = 0
        for k, (t0, rows) in enumerate(sim.mc_paths(trades, rng, sim.MC_PATHS)):
            daily, end, hit = trajectory(rows, t0, pol); paths.append(daily); hits += hit
            if k < 100: assert abs(end - sim.path(rows, t0, pol)['bal_end']) < 0.011, (stream, pol, k)
        stored = json.loads((R / f'RESULT-{stream}.json').read_text(encoding='utf-8'))['policies'][pol]['mc']
        assert abs(hits / len(paths) - stored['reach_10k']) < 1e-9, (stream, pol, hits / len(paths), stored['reach_10k'])
        cols = [sorted(p[d] for p in paths) for d in range(sim.HORIZON + 1)]; x = range(sim.HORIZON + 1)
        q = {p: [max(quantile(c, p), 1) for c in cols] for p in (.1, .25, .5, .75, .9)}
        ax.set_facecolor(SURFACE)
        ax.fill_between(x, q[.1], q[.9], color=BAND_OUTER, lw=0, label='10th–90th percentile')
        ax.fill_between(x, q[.25], q[.75], color=BAND_INNER, lw=0, label='25th–75th percentile')
        ax.plot(x, q[.5], color=BLUE, lw=2, label='Median path')
        for level, text in ((100, 'start $100'), (5000, '$5k'), (10000, '$10k')):
            ax.axhline(level, color=MUTED, lw=0.8, ls=(0, (4, 3)))
            ax.text(sim.HORIZON, level * 1.12, text, color=MUTED, fontsize=8, ha='right')
        ax.set_yscale('log'); ax.set_ylim(5, 2e5); ax.grid(axis='y', color=GRID, lw=0.6); ax.set_axisbelow(True)
        for side in ('top', 'right'): ax.spines[side].set_visible(False)
        for side in ('left', 'bottom'): ax.spines[side].set_color(GRID)
        ax.tick_params(colors=MUTED, labelsize=8)
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f'${v:,.0f}'))
        name = {'PR9': 'Prop ready nine', 'FTMO17': 'FTMO 17-EA basket'}[stream]
        ax.set_title(f'{name}, {int(pol[1:])}% risk per trade — reach $10k {100 * stored["reach_10k"]:.0f}%, bust {100 * stored["bust"]:.0f}%',
                     color=INK, fontsize=10, loc='left')
    for ax in axes[1]: ax.set_xlabel('Days from start', color=MUTED, fontsize=9)
    for ax in axes[:, 0]: ax.set_ylabel('Closed balance (log scale)', color=MUTED, fontsize=9)
    axes[0, 0].legend(loc='upper left', fontsize=8, frameon=False)
    fig.suptitle('$100 small-account challenge — 5,000 Monte Carlo paths (4-week blocks of 2021–2026 in-sample trades)', color=INK, fontsize=12, x=0.01, ha='left')
    fig.tight_layout(); fig.savefig(R / 'CHART-MC.png', dpi=130, facecolor=SURFACE); print('CHART-MC.png')


def native_chart():
    folder = R / 'native'
    runs = [(n, json.loads((folder / n / 'results.json').read_text())) for n in ('F05-2y', 'F10-2y', 'F05-1y', 'F10-1y') if (folder / n / 'results.json').exists()]
    capped = R / 'native-CAPPED-1PCT/F05-2y/results.json'
    if capped.exists(): runs.append(('Production EA, 1% cap (min lot) 2y', json.loads(capped.read_text())))
    if not runs: return
    fig, ax = plt.subplots(figsize=(11, 5), facecolor=SURFACE); ax.set_facecolor(SURFACE)
    colors = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#6250d6']
    for (name, res), color in zip(runs, colors):
        pts = sorted((t['close_time'], t['net_profit']) for t in res['trades']); bal = 100.0; xs, ys = [], []
        import pandas as pd
        for ct, pnl in pts: bal += pnl; xs.append(pd.Timestamp(ct)); ys.append(max(bal, 1))
        label = name if 'Production' in name else f"Research copy {name[1:3].lstrip('0')}% risk, {name[-2:]}"
        ax.plot(xs, ys, color=color, lw=2, label=f"{label}: end ${ys[-1]:,.0f}" if ys else label)
    ax.axhline(100, color=MUTED, lw=0.8, ls=(0, (4, 3)))
    ax.set_yscale('log'); ax.grid(axis='y', color=GRID, lw=0.6); ax.set_axisbelow(True)
    for side in ('top', 'right'): ax.spines[side].set_visible(False)
    for side in ('left', 'bottom'): ax.spines[side].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=8); ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f'${v:,.0f}'))
    ax.set_ylabel('Closed balance (log scale)', color=MUTED, fontsize=9); ax.legend(fontsize=8, frameon=False, loc='upper left')
    ax.set_title('Native MT5, Nasdaq 5M EA alone, $100 deposit, USTEC M5 Model 4 (one historical path each)', color=INK, fontsize=11, loc='left')
    fig.tight_layout(); fig.savefig(R / 'CHART-NATIVE.png', dpi=130, facecolor=SURFACE); print('CHART-NATIVE.png')


if __name__ == '__main__':
    import sys
    if 'native' not in sys.argv[1:]: mc_fan()
    native_chart()
