"""Side-by-side tables FTMO17 (Prop Portfolio Selection 2026-11-03) vs E10 (this folder), G5 (Portfolio 5 vs FTMO17 2026-11-04) for reference. -> TABLES.md"""
import json
from pathlib import Path

H = Path(__file__).resolve().parent; SEL = H.parent / 'Prop Portfolio Selection 2026-11-03'
G5D = H.parent / 'Portfolio 5 vs FTMO17 2026-11-04'
src = lambda name, f: {'FTMO17': SEL, 'G5': G5D}.get(name, H) / f  # noqa: E731
pct = lambda v: '—' if v is None else f'{100 * v:.1f}%'  # noqa: E731
L = []


def load(name, f):
    p = src(name, f); return json.loads(p.read_text(encoding='utf-8')) if p.exists() else None


L.append('## FTMO 2-step, $100k, pass both phases within 180 days')
L.append('| Portfolio | Risk | MC pass | Funded ≤ 60 / 90 d | Breach | Stuck at buffer | Median days to funded (p25–p75) | Hist all / dev / val / OOS | Median trades | Eq DD p95 |')
L.append('|---|---|---:|---|---:|---:|---|---|---:|---:|')
for risk in ('0.50', '1.00'):
    for name in ('FTMO17', 'E10', 'G5'):
        d = load(name, f'CH-{name}-{risk}.json')
        if not d: continue
        m, h = d['mc'], d['hist']
        L.append(f"| {name} | {risk}% | {pct(m['pass_both_180'])} | {pct(m['funded_60'])} / {pct(m['funded_90'])} | {pct(m['breach'])} | {pct(m['stalled_buffer'])} | "
                 f"{m['median_days_funded']} ({m['p25_funded']}–{m['p75_funded']}) | {' / '.join(pct(h[s]['pass_both_180']) for s in ('all', 'dev', 'val', 'oos'))} | "
                 f"{m['median_trades']:.0f} | ${m['eqdd_p95']:,.0f} |")
L.append('\n## FTMO 1-Step with the built ftmo 1_step guard, $100k, pass within 180 days')
L.append('| Portfolio | Risk | MC pass | Pass ≤ 30 / 60 / 90 d | Breach | Stuck | Median days (p25–p75) | Hist all / dev / val / OOS | Median trades |')
L.append('|---|---|---:|---|---:|---:|---|---|---:|')
for risk in ('0.50', '0.75', '1.00'):
    for name in ('FTMO17', 'E10', 'G5'):
        d = load(name, f'F1P-{name}-{risk}.json')
        if not d: continue
        m, h = d['mc'], d['hist']
        within = ' / '.join(pct(m.get(f'pass_{k}')) for k in (30, 60, 90))
        L.append(f"| {name} | {risk}% | {pct(m['pass_180'])} | {within} | {pct(m['breach'])} | {pct(m['stuck_buffer'])} | {m['median_days']} ({m.get('p25_days')}–{m.get('p75_days')}) | "
                 f"{' / '.join(pct(h[s]['pass_180']) for s in ('all', 'dev', 'val', 'oos'))} | {m.get('median_trades')} |")
L.append('\n## Funded FTMO $100k (36-month MC + history)')
L.append('| Portfolio | Risk | Income / month while alive (median) | Total income median / mean | Median days to end | Still trading at 36 m | First payout day (median) | Trades / month |')
L.append('|---|---|---:|---|---:|---:|---:|---:|')
for risk in ('0.50', '1.00'):
    for name in ('FTMO17', 'E10', 'G5'):
        d = load(name, f'FU-{name}-{risk}.json')
        if not d: continue
        m = d['mc']
        L.append(f"| {name} | {risk}% | ${m['monthly_income_while_alive_median']:,.0f} | ${m['income_total_median']:,.0f} / ${m['income_total_mean']:,.0f} | "
                 f"{m['median_days_to_end']:.0f} | {pct(m['alive_at_horizon'])} | {m['first_payout_day_median']} | {m['trades_per_month_alive_median']:.1f} |")
mc = json.loads((H / 'MC3.json').read_text(encoding='utf-8')) if (H / 'MC3.json').exists() else None
if mc:
    L.append('\n## Three-way Monte Carlo (stage 6, per trade in R, no guard)')
    L.append('| Portfolio | Trades (per month) | Win % | PF | Mean R | Real DD R / shuffle p95 | Real DD worse than | Resample red (5 y / 1 y) | Randomize red 1 y (+0.05R / +0.10R) |')
    L.append('|---|---|---:|---:|---:|---|---:|---|---|')
    for name, v in mc.items():
        f, y = v['full'], v['one_year']
        L.append(f"| {name} | {v['trades']} ({v['trades_per_month']}) | {v['win_pct']}% | {v['pf']} | {v['mean_r']} | {f['real']['max_drawdown']:.1f} / {f['reshuffle']['max_drawdown']['p95']:.1f} | "
                 f"{f['reshuffle']['real_drawdown_worse_than_pct']}% | {f['resample']['red_pct']}% / {y['resample']['red_pct']}% | {y['randomize']['both']['red_pct']}% / {v['one_year_cost_010']['both']['red_pct']}% |")
(H / 'TABLES.md').write_text('\n'.join(L) + '\n', encoding='utf-8'); print('\n'.join(L))
