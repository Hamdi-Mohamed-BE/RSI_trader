"""Table of the per-phase FTMO stats (phase_stats.py outputs PS-*.json). $100k accounts, MC 2,000 paths. -> PHASE_STATS.md"""
import json
from pathlib import Path

H = Path(__file__).resolve().parent
NAMES = [('Core 9', 'C9', 'C9U'), ('E10', 'E10', 'E10U'), ('FTMO17', 'FTMO17', 'CUR17')]; RISKS = ('0.50', '0.75', '1.00')


def load(kind, name, r):
    f = H / f'PS-{kind}-{name}-{r}.json'
    return json.loads(f.read_text(encoding='utf-8')) if f.exists() else None


pct = lambda x: '-' if x is None else f'{100 * x:.0f}%'  # noqa: E731
usd = lambda x: '-' if x is None else f'${x:,.0f}'  # noqa: E731
day = lambda x: '-' if x is None else f'{x:g}'  # noqa: E731


def phase(p):
    if not p: return ['-'] * 7
    return [pct(p['passed']), day(p['median_days_pass']), pct(p['breached']), day(p['median_days_breach']), day(p['median_trading_days_breach']), f"{usd(p['worst_closed_day_median'])} / {usd(p['worst_closed_day_p95'])} / {usd(p['worst_closed_day_max'])}", str(p['n_breach'])]


L = ['# Per-phase FTMO stats, $100k, Monte Carlo 2,000 paths (2021-10 -> 2026-10 streams, in-sample)', '',
     'Phase rows count only the paths that reached that phase (Phase 2 = paths that passed Phase 1). Days = calendar days from the phase start, inclusive. Trading days = days with at least one entry.',
     'Worst closed day = biggest loss of trades CLOSED on one day in that phase (median / 95th percentile / worst path). Floating = worst intraday equity loss of the whole path, reported separately.', '']
for title, kind in (('FTMO 2-step', 'two'), ('FTMO 1-Step', 'one')):
    L += [f'## {title}', '', '| Portfolio | Guard | Risk | Phase | Reached | Pass | Median days to pass | Breach | Median days to breach | Median trading days before breach | Worst closed day (median / p95 / max) | Breaches (paths) | Overall pass / breach | Floating worst day (median / p95 / max) |',
          '|---|---|---|---|---:|---:|---:|---:|---:|---:|---|---:|---|---|']
    for label, g, u in NAMES:
        for name, tag in ((g, 'guard'), (u, 'no guard')):
            for r in RISKS:
                d = load(kind, name, r)
                if not d: L.append(f'| {label} | {tag} | {r}% | | missing |||||||||'); continue
                fl = f"{usd(d['floating_day_median'])} / {usd(d['floating_day_p95'])} / {usd(d['floating_day_max'])}"
                for ph in ('phase1', 'phase2') if kind == 'two' else ('phase1',):
                    p = d.get(ph)
                    if p is None: continue
                    name_ph = {'phase1': 'Phase 1' if kind == 'two' else 'Challenge', 'phase2': 'Phase 2'}[ph]
                    L.append(f"| {label} | {tag} | {r}% | {name_ph} | {pct(p['entered_share'])} | " + ' | '.join(phase(p)) + f" | {pct(d['pass_all'])} / {pct(d['breach_any'])} | {fl} |")
    L.append('')
L += ['## Funded (FTMO standard funded rules, 36-month MC)', '', '| Portfolio | Guard | Risk | Income / month while trading (median) | 36 m total median | Breach | Frozen | Still trading | Median days to breach | Median trading days before breach | Median days to freeze | Worst closed day (median / p95 / max) | Floating worst day (median / p95 / max) | Trades / month |',
      '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---:|']
for label, g, u in NAMES:
    for name, tag in ((g, 'guard'), (u, 'no guard')):
        for r in RISKS:
            d = load('fund', name, r)
            if not d: L.append(f'| {label} | {tag} | {r}% | missing ||||||||||'); continue
            i = d['income']
            L.append(f"| {label} | {tag} | {r}% | {usd(i['monthly_median'])} | {usd(i['total_median'])} | {pct(d['breach_share'])} | {pct(d['frozen_share'])} | {pct(d['alive_share'])} | {day(d['median_days_breach'])} | {day(d['median_trading_days_breach'])} | {day(d['median_days_frozen'])} | "
                     f"{usd(d['worst_closed_day_median'])} / {usd(d['worst_closed_day_p95'])} / {usd(d['worst_closed_day_max'])} | {usd(d['floating_day_median'])} / {usd(d['floating_day_p95'])} / {usd(d['floating_day_max'])} | {i['trades_per_month']} |")
(H / 'PHASE_STATS.md').write_text('\n'.join(L) + '\n', encoding='utf-8'); print('\n'.join(L[:12])); print('written', sum(1 for x in L if x.startswith('|')), 'rows')
