"""Render INCOME-*.json into INCOME.md. Formatting only."""
import json
from pathlib import Path

R = Path(__file__).resolve().parent
X = {(p.stem.split('-')[1], int(p.stem.split('-')[2])): json.loads(p.read_text(encoding='utf-8')) for p in sorted(R.glob('INCOME-*-*.json'))}


def usd(v): return '-' if v is None else f'${v:,.0f}'
def pct(v): return '-' if v is None else f'{100 * v:.0f}%'
def days(v, horizon): return f'> {horizon:.0f} (not reached)' if v is None else f'{v:g}'


head = ('| Policy · costs · evidence | Accounts | Ended ≤6 m | ≤12 m | ≤24 m | Ends: breach / frozen / alive | Median days to end | Payouts (median) | '
        'Avg monthly income while alive (pooled) | Per-account monthly (median / mean) | Total income until end (median / mean, p25–p75) | First-year income (median / mean) | Trades / month | / day |')
rows = [head, '|' + '---|' * 14]
for (cost, th), x in sorted(X.items(), key=lambda kv: (kv[0][1], kv[0][0] != 'recorded_exness')):
    pol = '$20 every 14 d' if th == 20 else '≥ 2% ($2,000) every 14 d'
    for lbl, s in (('history 12 m, all starts', x['hist']['all_starts']), ('history 12 m, OOS starts', x['hist'].get('oos_starts')),
                   ('history 12 m, dev starts', x['hist'].get('development_starts')), ('Monte Carlo 36 m', x['mc'])):
        if not s: continue
        e = s['ends']; n = s['n']
        rows.append(f"| {pol} · {'recorded' if cost == 'recorded_exness' else 'stress'} · {lbl} | {n} | {pct(s.get('ended_by_6m'))} | {pct(s.get('ended_by_12m'))} | {pct(s.get('ended_by_24m'))} | "
                    f"{pct(e.get('breach', 0) / n)} / {pct(e.get('frozen', 0) / n)} / {pct(e.get('alive', 0) / n)} | {days(s['median_days_to_end'], s['horizon_days'])} | {s['payouts_median']:g} | "
                    f"{usd(s['pooled_income_per_alive_month'])} | {usd(s['monthly_income_while_alive_median'])} / {usd(s['monthly_income_while_alive_mean'])} | "
                    f"{usd(s['income_total_median'])} / {usd(s['income_total_mean'])} ({usd(s['income_total_p25'])}–{usd(s['income_total_p75'])}) | "
                    f"{usd(s['first_year_income_median'])} / {usd(s['first_year_income_mean'])} | {s['trades_per_month_alive_median']} | {s['trades_per_weekday_alive_median']} |")
text = '# One funded $100k account — income until it ends (generated from INCOME-*.json)\n\n' + '\n'.join(rows) + '\n'
(R / 'INCOME.md').write_text(text, encoding='utf-8'); print(text)
