"""Funded income table: FTMO17 and E10, guarded (installed FTMO / Prop Ready guard model) and unguarded (E10U = the Edge 10 package,
CUR17 = the same 17 FTMO17 EAs without a guard). FTMO funded $100k, First Payout income model (80% split, 14-day rewards), 36-month MC
(2,000 paths) + history. -> INCOME.md"""
import json
from pathlib import Path

H = Path(__file__).resolve().parent; SEL = H.parent / 'Prop Portfolio Selection 2026-11-03'
RISKS = ('0.50', '0.75', '1.00')
def path(stream, r):                                    # guarded 0.5 / 1.0 come from the earlier runs; everything else from here
    if stream == 'FTMO17' and r != '0.75': return SEL / f'FU-FTMO17-{r}.json'
    return H / f'FU-{stream}-{r}.json'
ROWS = [('FTMO17', 'guarded', 'FTMO17'), ('E10', 'guarded', 'E10'), ('FTMO17', 'no guard', 'CUR17'), ('E10 (Edge 10 package)', 'no guard', 'E10U')]
L = ['| Portfolio | Guard | Risk | Income / month while trading (median / mean) | First 12 months (mean) | Total 36 m (median / mean) | Median days until the account ends | Ends: frozen / breached / still trading at 36 m | Trades / month |',
     '|---|---|---|---|---:|---|---:|---|---:|']
for name, guard, stream in ROWS:
    for r in RISKS:
        p = path(stream, r)
        if not p.exists(): L.append(f'| {name} | {guard} | {r}% | still running | | | | | |'); continue
        m = json.loads(p.read_text(encoding='utf-8'))['mc']; e = m['ends']; n = m['n']
        frozen = e.get('frozen', 0) / n; breached = sum(v for k, v in e.items() if k not in ('alive', 'frozen')) / n
        L.append(f"| {name} | {guard} | {r}% | ${m['monthly_income_while_alive_median']:,.0f} / ${m['monthly_income_while_alive_mean']:,.0f} | ${m['first_year_income_mean']:,.0f} | "
                 f"${m['income_total_median']:,.0f} / ${m['income_total_mean']:,.0f} | {'> 1,092 (most still trading)' if m['median_days_to_end'] is None else format(m['median_days_to_end'], '.0f')} | "
                 f"{100 * frozen:.0f}% / {100 * breached:.0f}% / {100 * m['alive_at_horizon']:.0f}% | {m['trades_per_month_alive_median']:.1f} |")
(H / 'INCOME.md').write_text('\n'.join(L) + '\n', encoding='utf-8'); print('\n'.join(L))
