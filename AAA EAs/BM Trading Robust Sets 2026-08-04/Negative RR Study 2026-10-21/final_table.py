"""Render the final Negative RR tables (FINAL.md) from E2E-*.json, INCOME-*.json and STANDALONE.json. Formatting only."""
import json
from pathlib import Path

R = Path(__file__).resolve().parent; P = R / 'prop'
LV = [('base-fresh', 'Current targets'), ('rr075', '0.75R'), ('rr060', '0.60R'), ('rr050', '0.50R')]
def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def pct(v): return '-' if v is None else f'{100 * v:.0f}%'
def usd(v): return '-' if v is None else f'${v:,.0f}'
def num(v): return '-' if v is None else f'{v:g}'


def challenge_table(cost, handover, mc):
    head = ('| Target | OOS starts: pass both ≤180 d | funded ≤90 d | median days to funded | All starts 2021-26: pass ≤180 d | funded ≤90 d | median days | '
            'Monte Carlo: funded | first payout | median days to payout request | median payout | Trades / month | / day |')
    lines = [head, '|' + '---|' * 13]
    for lv, label in LV:
        x = read(P / f'E2E-{lv}.json'); o = x['challenge_oos'][f'{cost}|{handover}']; a = x['challenge_all'][f'{cost}|{handover}']; m = x['e2e_mc'][mc]
        lines.append(f"| {label} | {pct(o['pass_both_180'])} | {pct(o['funded_90'])} | {num(o['median_days_funded'])} | {pct(a['pass_both_180'])} | {pct(a['funded_90'])} | "
                     f"{num(a['median_days_funded'])} | {pct(m['funded_access'])} | {pct(m['20']['paid_any'])} | {num(m['20']['median_total_day'])} | {usd(m['20']['median_payout'])} | "
                     f"{round(a['median_trades'] / (180 / 30.4375), 1)} | {round(a['median_trades'] / (180 * 5 / 7), 2)} |")
    return '\n'.join(lines)


def income_table(risk, cost, src):
    lines = ['| Target | Avg monthly income while trading | Median days until bots stop | Still trading at end | Breach / frozen | Total income (median / mean) | First-year income (mean) | First payout (median) | Trades / month | / day |',
             '|' + '---|' * 10]
    for lv, label in LV:
        f = P / f'INCOME-{lv}-{risk:g}-{cost}.json'
        if not f.exists(): continue
        x = read(f); s = x['mc'] if src == 'mc' else x['hist'][src]; n = s['n']; e = s['ends']; med = s['median_days_to_end']
        lines.append(f"| {label} | {usd(s['pooled_income_per_alive_month'])} | {'> ' + str(s['horizon_days']) if med is None else f'{med:g}'} | {pct(s['alive_at_horizon'])} | "
                     f"{pct(e.get('breach', 0) / n)} / {pct(e.get('frozen', 0) / n)} | {usd(s['income_total_median'])} / {usd(s['income_total_mean'])} | {usd(s['first_year_income_mean'])} | "
                     f"{usd(s['first_payout_median'])} | {s['trades_per_month_alive_median']} | {s['trades_per_weekday_alive_median']} |")
    return '\n'.join(lines)


def standalone_table(window):
    S = read(R / 'STANDALONE.json'); order = ['base', 'rr075', 'rr060', 'rr050']
    lines = [f'| EA ({window}) | Current: return / avg R / win rate | 0.75R | 0.60R | 0.50R | Trades / month (current → 0.50R) |', '|---|---|---|---|---|---|']
    for ea, w in S.items():
        row = w[window]
        cells = [f"{row[lv]['ret']}% / {row[lv]['avg_r']}R / {row[lv]['win_rate']}%" for lv in order]
        lines.append(f"| {ea} | " + ' | '.join(cells) + f" | {row['base']['per_month']} → {row['rr050']['per_month']} |")
    return '\n'.join(lines)


parts = ['# Negative RR Study — final tables (generated)', '']
base = read(P / 'E2E-base.json'); parts += [f"Parity: {base.get('parity')}", '']
parts += ['## Prop challenge + first payout — Best Prop 9, $10k, DI OFF, recorded costs, next-midnight handover', '', challenge_table('recorded_exness', 'next_prague_midnight', 'base'), '']
parts += ['## Same, stress costs + two-business-day handover', '', challenge_table('fixed_cost_stress', 'two_business_day_wait', 'stress'), '']
for risk in (0.01, 0.005):
    for cost in ('recorded_exness', 'fixed_cost_stress'):
        parts += [f'## Funded $100k income until it ends — {risk * 100:g}% risk, {cost}, Monte Carlo 36 months', '', income_table(risk, cost, 'mc'), '']
    parts += [f'## Funded $100k income — {risk * 100:g}% risk, recorded, history 12 months (all starts)', '', income_table(risk, 'recorded_exness', 'all_starts'), '']
for w in ('5 years', 'OOS 2024-26', 'Dev 2021-23'):
    parts += [f'## Standalone native per EA — {w}', '', standalone_table(w), '']
(R / 'FINAL.md').write_text('\n'.join(parts) + '\n', encoding='utf-8'); print('\n'.join(parts))
