"""Render RESULTS-SIZE-*.json into SIZES.md. Formatting only."""
import json
from pathlib import Path

R = Path(__file__).resolve().parent
S = {int(p.stem.split('-')[-1]): json.loads(p.read_text(encoding='utf-8')) for p in sorted(R.glob('RESULTS-SIZE-*.json'))}


def pct(v): return '-' if v is None else f'{100 * v:.0f}%'
def usd(v): return '-' if v is None else f'${v:,.0f}'
def num(v): return '-' if v is None else f'{v:g}'
def fee(x): return f"€{x['fee_eur']}" if x['fee_eur'] else 'n/a (not an FTMO size)'


def e2e_table(src, sc):
    lines = ['| Account | Fee | Funded | Days to funded (median / mean) | Paid ≤120 d | Paid ≤180 d | Paid at all | Days start → payout request (median / mean, p25–p75) | Payout (median / mean) | Expected payout per challenge | Trades / month (funded) | / day |',
             '|---|---|---|---|---|---|---|---|---|---|---|---|']
    for size, x in sorted(S.items()):
        s = x['e2e_mc'][sc] if src == 'mc' else x['e2e'][f'{sc}|{src}_starts']; m = x['means'][f'e2e_mc|{sc}' if src == 'mc' else f'e2e|{sc}|{src}_starts']
        f = x['funded_mc']['recorded_exness' if sc == 'base' else 'fixed_cost_stress'] if src == 'mc' else x['funded'][f"{'recorded_exness' if sc == 'base' else 'fixed_cost_stress'}|{src}"]
        t = s['20']; mt = m['20']
        lines.append(f"| ${size:,} | {fee(x)} | {pct(s['funded_access'])} | {num(s['median_funded_access_day'])} / {num(m['mean_funded_access_day'])} | {pct(t['paid_120'])} | {pct(t['paid_180'])} | {pct(t['paid_any'])} | "
                     f"{num(t['median_total_day'])} / {num(mt['mean_total_day'])} ({num(t['p25_total_day'])}–{num(t['p75_total_day'])}) | {usd(t['median_payout'])} / {usd(mt['mean_payout'])} | {usd(t['ev_payout'])} | {f['trades_per_month']} | {f['trades_per_weekday']} |")
    return '\n'.join(lines)


def funded_table(src, cost):
    lines = ['| Account | Paid ≤30 d | Paid ≤180 d | Day of request (median / mean) | Payout (median / mean, p25–p75) | Expected payout per funded account | Breach before payout | Stuck at 92% buffer | Trades skipped (min lot, median) | Trades / month | / day |',
             '|---|---|---|---|---|---|---|---|---|---|---|']
    for size, x in sorted(S.items()):
        s = x['funded_mc'][cost] if src == 'mc' else x['funded'][f'{cost}|{src}']; m = x['means'][f'funded_mc|{cost}' if src == 'mc' else f'funded|{cost}|{src}']
        t = s['20']; mt = m['20']
        lines.append(f"| ${size:,} | {pct(t['paid_30'])} | {pct(t['paid_180'])} | {num(t['median_day'])} / {num(mt['mean_day'])} | {usd(t['median_payout'])} / {usd(mt['mean_payout'])} ({usd(t['p25_payout'])}–{usd(t['p75_payout'])}) | "
                     f"{usd(t['ev_payout'])} | {pct(t['breach_before'])} | {pct(t['stuck_buffer'])} | {num(m['skipped_min_lot_median'])} | {s['trades_per_month']} | {s['trades_per_weekday']} |")
    return '\n'.join(lines)


parts = ['# Account sizes (generated from RESULTS-SIZE-*.json) — DI OFF, earliest payout policy ($20 minimum)', '',
         'Parity: ' + '; '.join(f"{k}: {v.get('parity_vs_main_10k', 'n/a')}" for k, v in sorted(S.items()) if k == 10000), '']
for src, lbl in (('mc', 'Monte Carlo (2,000 paths)'), ('all', 'All history (every weekday start)'), ('oos', 'OOS 2024-26 starts')):
    for sc in ('base', 'stress'):
        parts += [f'## From buying the challenge · {lbl} · {sc}', '', e2e_table(src, sc), '']
for src, lbl in (('mc', 'Monte Carlo'), ('all', 'All history'), ('oos', 'OOS 2024-26')):
    parts += [f'## Funded account only · {lbl} · recorded costs', '', funded_table(src, 'recorded_exness'), '']
(R / 'SIZES.md').write_text('\n'.join(parts) + '\n', encoding='utf-8')
print('\n'.join(parts))
