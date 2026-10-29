"""Cumulative P(reached $10k) and P(bust) by day, all-period MC (5,000 paths, 365 days, same paths as search.py final).

python chart.py  ->  CHART-TIME-TO-10K.png
"""
import importlib.util, json, math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

R = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('search', R / 'search.py'); S = importlib.util.module_from_spec(spec); spec.loader.exec_module(S)
INK, MUTED, GRID, SURFACE = '#0b0b0b', '#52514e', '#e4e3df', '#fcfcfb'
COLORS = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#6250d6']

d = S.load_json('DEV.json'); v = S.load_json('VALIDATION.json'); final = S.load_json('FINAL.json')
kelly = {n: s.get('kelly', 0.) for n, s in d['lane_stats'].items()}
configs = [('Chosen: TOP5 at 50% per trade', v['chosen']), ('FTMO 17-EA basket at 20%', S.baseline_rows()[3]),
           ('FTMO 17-EA basket at 10%', S.baseline_rows()[2]), ('RSI VWAP alone at 100%', d['rsi_vwap_best']),
           ('Prop ready nine at 5%', S.baseline_rows()[0])]
ev = S.build(S.mc_paths('all', n=5000, horizon=365)); days = np.arange(0, 366)
fig, axes = plt.subplots(1, 2, figsize=(13, 5.2), facecolor=SURFACE)
for (label, r), color in zip(configs, COLORS):
    o = S.simulate(ev, r['lanes'], tuple(r['policy']), S.cap_of(r), kelly, 365)
    stored = next((x for x in final['rows'] if x['horizon'] == 365 and x['basket'] == r['basket'] and x['policy_name'] == r['policy_name']), None)
    if stored: assert abs(float((o[:, 2] >= 0).mean()) - stored['mc']['p10k']) < 1e-9, label
    hit = [(o[:, 2] >= 0) & (o[:, 2] <= x) for x in days]; bust = [(o[:, 3] >= 0) & (o[:, 3] <= x) for x in days]
    ph = [100 * h.mean() for h in hit]; pb = [100 * b.mean() for b in bust]
    axes[0].plot(days, ph, color=color, lw=2, label=f'{label}: {ph[90]:.1f}% by day 90, {ph[365]:.1f}% by day 365')
    axes[1].plot(days, pb, color=color, lw=2, label=f'{label}: {pb[90]:.0f}% by day 90')
axes[0].set_ylim(0, 50); axes[1].set_ylim(0, 105)
for ax, title, ylab in ((axes[0], r'Chance the \$100 account has reached \$10,000', '% of 5,000 paths'), (axes[1], 'Chance the account has blown (<$10)', '% of 5,000 paths')):
    ax.set_facecolor(SURFACE); ax.axvline(90, color=MUTED, lw=0.8, ls=(0, (4, 3))); ax.text(92, ax.get_ylim()[1] * 0.55, '3 months', color=MUTED, fontsize=8, va='top')
    ax.grid(axis='y', color=GRID, lw=0.6); ax.set_axisbelow(True)
    for side in ('top', 'right'): ax.spines[side].set_visible(False)
    for side in ('left', 'bottom'): ax.spines[side].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=8); ax.set_xlabel('Days from start', color=MUTED, fontsize=9); ax.set_ylabel(ylab, color=MUTED, fontsize=9)
    ax.set_title(title, color=INK, fontsize=11, loc='left'); ax.legend(fontsize=7.5, frameon=False, loc='upper left'); ax.set_xlim(0, 365)
fig.suptitle(r'\$100 start, all-period Monte Carlo (4-week blocks of 2021–2026 in-sample EA trades, no extra costs)', color=INK, fontsize=12, x=0.01, ha='left')
fig.tight_layout(); fig.savefig(R / 'CHART-TIME-TO-10K.png', dpi=130, facecolor=SURFACE); print('CHART-TIME-TO-10K.png')
