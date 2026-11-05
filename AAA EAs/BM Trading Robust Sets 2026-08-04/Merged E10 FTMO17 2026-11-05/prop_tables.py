"""FTMO tables for FTMO17, E10 and M22, with and without guard, from the frozen-engine outputs (this folder, Edge Portfolio E10 2026-11-04, Prop Portfolio
Selection 2026-11-03). 2021-10 -> 2026-10 streams, $100k, 2,000-path MC. -> TABLES_PROP.md"""
import json
from pathlib import Path

H = Path(__file__).resolve().parent; DIRS = (H, H.parent / 'Edge Portfolio E10 2026-11-04', H.parent / 'Prop Portfolio Selection 2026-11-03')
RISKS = ('0.50', '0.75', '1.00'); PORT = (('FTMO17', 'FTMO17', 'CUR17'), ('E10', 'E10', 'E10U'), ('M22', 'M22', 'M22U'), ('E10 + Gold Overnight', 'E11', 'E11U'), ('Core 9', 'C9', 'C9U'))
pct = lambda v: '-' if v is None else f'{100 * v:.0f}%'  # noqa: E731


def load(f):
    for d in DIRS:
        if (d / f).exists(): return json.loads((d / f).read_text(encoding='utf-8'))
    return None


L = ['## FTMO 2-step: pass both phases within 180 days', '| Portfolio | Guard | Risk | Pass | Funded within 90 d | Median days to funded | Breach | Stuck | Pass by start: 2021-23 / 2023-24 / 2024-26 |', '|---|---|---|---:|---:|---:|---:|---:|---|']
for label, g, u in PORT:
    for name, tag in ((g, 'guard'), (u, 'no guard')):
        for r in RISKS:
            d = load(f'CH-{name}-{r}.json')
            if not d: L.append(f'| {label} | {tag} | {r}% | missing |||||| '); continue
            m, h = d['mc'], d['hist']
            L.append(f"| {label} | {tag} | {r}% | {pct(m['pass_both_180'])} | {pct(m['funded_90'])} | {m['median_days_funded']} | {pct(m['breach'])} | {pct(m['stalled_buffer'])} | {' / '.join(pct(h[s]['pass_both_180']) for s in ('dev', 'val', 'oos'))} |")
L += ['', '## FTMO 1-Step: pass within 180 days (guard = the built ftmo 1_step guard)', '| Portfolio | Guard | Risk | Pass | Pass within 60 / 90 d | Median days | Breach | Stuck | Pass by start: 2021-23 / 2023-24 / 2024-26 |', '|---|---|---|---:|---|---:|---:|---:|---|']
for label, g, u in PORT:
    for name, tag, pre in ((g, 'guard', 'F1P'), (u, 'no guard', 'F1U')):
        for r in RISKS:
            d = load(f'{pre}-{name}-{r}.json')
            if not d: L.append(f'| {label} | {tag} | {r}% | missing |||||| '); continue
            m, h = d['mc'], d['hist']
            L.append(f"| {label} | {tag} | {r}% | {pct(m['pass_180'])} | {pct(m['pass_60'])} / {pct(m['pass_90'])} | {m['median_days']} | {pct(m['breach'])} | {pct(m['stuck_buffer'])} | {' / '.join(pct(h[s]['pass_180']) for s in ('dev', 'val', 'oos'))} |")
L += ['', '## Funded $100k (FTMO standard funded rules, 36-month MC)', '| Portfolio | Guard | Risk | Income / month while trading | Total 36 m median / mean | Median life (days) | Frozen / breached / still trading | Trades / month |', '|---|---|---|---:|---|---:|---|---:|']
for label, g, u in PORT:
    for name, tag in ((g, 'guard'), (u, 'no guard')):
        for r in RISKS:
            d = load(f'FU-{name}-{r}.json')
            if not d: L.append(f'| {label} | {tag} | {r}% | missing ||||| '); continue
            m = d['mc']; e = m['ends']; n = m['n']; life = m['median_days_to_end']
            br = sum(v for k, v in e.items() if k not in ('alive', 'frozen')) / n
            L.append(f"| {label} | {tag} | {r}% | ${m['monthly_income_while_alive_median']:,.0f} | ${m['income_total_median'] / 1000:,.0f}k / ${m['income_total_mean'] / 1000:,.0f}k | {'> 1,092' if life is None else f'{life:.0f}'} | {100 * e.get('frozen', 0) / n:.0f}% / {100 * br:.0f}% / {100 * m['alive_at_horizon']:.0f}% | {m['trades_per_month_alive_median']:.1f} |")
(H / 'TABLES_PROP.md').write_text('\n'.join(L) + '\n', encoding='utf-8'); print('\n'.join(L))
