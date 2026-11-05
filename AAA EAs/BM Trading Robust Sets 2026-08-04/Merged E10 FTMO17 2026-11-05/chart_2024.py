"""Equity curves since 2024-01-01 for FTMO17, E10 and Mixed: $10k at 1% (fixed and compounding) and a funded $100k with no guard, breach marked. -> EQUITY_2024.png"""
import json
from datetime import datetime
from pathlib import Path
import matplotlib; matplotlib.use('Agg')
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
H = Path(__file__).resolve().parent; E = json.loads((H / 'EQUITY_2024.json').read_text(encoding='utf-8')); F = json.loads((H / 'FUNDED_2024.json').read_text(encoding='utf-8'))
C = {'FTMO17': '#2a78d6', 'E10': '#eb6834', 'M22': '#1baf7a'}; N = {'FTMO17': 'FTMO17', 'E10': 'E10', 'M22': 'Mixed'}; INK, MUTED, GRID = '#0b0b0b', '#52514e', '#e7e6e1'
plt.rcParams.update({'text.parse_math': False, 'font.family': 'DejaVu Sans', 'font.size': 11, 'axes.edgecolor': GRID, 'text.color': INK, 'axes.labelcolor': MUTED, 'xtick.color': MUTED, 'ytick.color': MUTED})
fig, ax = plt.subplots(2, 2, figsize=(15, 9.5), facecolor='#fcfcfb')


def style(a, title, money=True):
    a.set_facecolor('#fcfcfb'); a.set_title(title, loc='left', fontsize=12.5, fontweight='bold', pad=10); a.grid(axis='y', color=GRID, lw=1); a.set_axisbelow(True)
    for s in ('top', 'right', 'left'): a.spines[s].set_visible(False)
    a.tick_params(length=0); a.xaxis.set_major_locator(mdates.MonthLocator(bymonth=(1, 7))); a.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    if money: a.yaxis.set_major_formatter(lambda v, _: f'${v:,.0f}')


def label_ends(a, ends):                                   # keep the end labels apart
    ends = sorted(ends, key=lambda e: e[1]); lo, hi = a.get_ylim(); log = a.get_yscale() == 'log'
    import math
    pos = [(math.log10(v) if log else v) for _, v, _ in ends]; span = (math.log10(hi) - math.log10(lo)) if log else hi - lo
    for i in range(1, len(pos)): pos[i] = max(pos[i], pos[i - 1] + span * 0.055)
    for (x, _, text), p in zip(ends, pos):
        a.annotate(text, (x, 10 ** p if log else p), xytext=(6, 0), textcoords='offset points', va='center', fontsize=10.5, color=INK, annotation_clip=False)


def dates(c): return [datetime.fromisoformat(p[0]).replace(tzinfo=None) for p in c]


for key, a, title in (('fixed', ax[0, 0], '$10k, fixed $100 per trade (1% of the start), no guard'), ('compound', ax[0, 1], '$10k, 1% of current balance per trade, no guard (log scale)')):
    ends = []
    for n in C:
        x = E[n][key]; pts = x['curve']; a.plot(dates(pts), [p[1] for p in pts], color=C[n], lw=2, label=f"{N[n]}: max closed DD {x['max_closed_dd_pct']:.1f}%", solid_capstyle='round'); ends.append((dates(pts)[-1], pts[-1][1], f"{N[n]} ${pts[-1][1]:,.0f}"))
    if key == 'compound': a.set_yscale('log')
    style(a, title); a.legend(frameon=False, loc='upper left', fontsize=10.5); label_ends(a, ends)
for r, a, title in (('1.00', ax[1, 0], 'Funded $100k at 1%, no guard: balance + rewards'), ('0.50', ax[1, 1], 'Funded $100k at 0.5%, no guard: balance + rewards')):
    ends = []
    for n in C:
        x = F[f'{n}-{r}']; pts = x['curve']; d = [datetime.fromisoformat(p[0]) for p in pts]; y = [p[1] for p in pts]; breach = x['end'] == 'breach'
        a.plot(d, y, color=C[n], lw=2, label=f"{N[n]}: {'breach ' + x['end_date'] if breach else 'alive to ' + x['end_date']}, rewards ${x['income']:,.0f}", solid_capstyle='round')
        if breach: a.plot(d[-1], y[-1], marker='X', ms=11, color=C[n], mec='#fcfcfb', mew=1.5, ls='none', zorder=5)
    style(a, title); a.axhline(100000, color=MUTED, lw=1, ls=(0, (3, 3))); a.legend(frameon=False, loc='upper left', fontsize=10.5)
    if r == '1.00':
        a.xaxis.set_major_locator(mdates.MonthLocator()); a.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y')); a.set_ylim(top=a.get_ylim()[1] + 9000)
    else:
        a.set_ylim(top=a.get_ylim()[1] + 70000)
fig.text(0.012, 0.012, 'Python replay of native backtests, in-sample. Top: closed balance, 2024-01 to 2026-10. Bottom: FTMO standard funded rules with floating losses, one start date, data to 2026-10-05. X = breach.', fontsize=9.5, color=MUTED)
fig.tight_layout(rect=(0, 0.03, 0.96, 1), w_pad=5, h_pad=2.5); fig.savefig(H / 'EQUITY_2024.png', dpi=130, facecolor=fig.get_facecolor())
