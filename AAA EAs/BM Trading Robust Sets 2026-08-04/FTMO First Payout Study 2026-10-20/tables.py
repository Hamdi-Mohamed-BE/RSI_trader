"""Render RESULTS.json into markdown tables (TABLES.md). No computation beyond formatting."""
import json
from pathlib import Path

R = Path(__file__).resolve().parent
X = json.loads((R / 'RESULTS.json').read_text(encoding='utf-8'))
WIN = [('development', 'Dev 2021-23'), ('validation', 'Val 2023-24'), ('oos', 'OOS 2024-26'), ('all', 'All 5y')]


def pct(v): return '-' if v is None else f'{100 * v:.0f}%'
def usd(v): return '-' if v is None else f'${v:,.0f}'
def rng(a, b, f): return '-' if a is None else f'{f(a)}–{f(b)}'
def num(v): return '-' if v is None else (f'{v:g}' if isinstance(v, (int, float)) else str(v))


def funded_rows(name, cost, th):
    rows = [(lbl, X['funded'][f'{name}|{cost}|{w}']) for w, lbl in WIN] + [('Monte Carlo', X['funded_mc'][f'{name}|{cost}'])]
    out = ['| Window | Starts | Paid ≤30 d | ≤60 d | ≤90 d | ≤180 d | Median day (p25–p75) | Median payout (p25–p75) | Expected payout / account | Breach before payout | No payout, stuck at $9,200 | Trades / 180 d | / month | / day |',
           '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    for lbl, s in rows:
        t = s[str(th)]
        out.append(f"| {lbl} | {s['n']} | {pct(t['paid_30'])} | {pct(t['paid_60'])} | {pct(t['paid_90'])} | {pct(t['paid_180'])} | "
                   f"{num(t['median_day'])} ({rng(t['p25_day'], t['p75_day'], num)}) | {usd(t['median_payout'])} ({rng(t['p25_payout'], t['p75_payout'], usd)}) | "
                   f"{usd(t['ev_payout'])} | {pct(t['breach_before'])} | {pct(t['stuck_buffer'])} | {num(s['median_trades_180d'])} | {s['trades_per_month']} | {s['trades_per_weekday']} |")
    return '\n'.join(out)


def threshold_rows(name, cost):
    out = ['| Request when closed profit ≥ | Evidence | Paid ≤180 d | Median day | Median payout | Expected payout / account | Breach before payout | Trades / month | / day |', '|---|---|---|---|---|---|---|---|---|']
    for th in (20, 250, 500, 1000):
        for lbl, s in (('All 5y', X['funded'][f'{name}|{cost}|all']), ('OOS 2024-26', X['funded'][f'{name}|{cost}|oos']), ('Monte Carlo', X['funded_mc'][f'{name}|{cost}'])):
            t = s[str(th)]
            out.append(f"| ${th:,} | {lbl} | {pct(t['paid_180'])} | {num(t['median_day'])} | {usd(t['median_payout'])} | {usd(t['ev_payout'])} | {pct(t['breach_before'])} | {s['trades_per_month']} | {s['trades_per_weekday']} |")
    return '\n'.join(out)


def e2e_rows(name, th):
    out = ['| Scenario | Challenge starts | Funded | Paid ≤120 d | ≤180 d | ≤270 d | ≤365 d | Median days start → request (p25–p75) | Median payout | Expected payout / challenge bought | Median trades (chain) |',
           '|---|---|---|---|---|---|---|---|---|---|---|']
    for sc in ('base', 'stress'):
        rows = [(f'{lbl} starts', X['e2e'].get(f'{name}|{sc}|{w}_starts')) for w, lbl in WIN] + [('Monte Carlo', X['e2e_mc'][f'{name}|{sc}'])]
        for lbl, s in rows:
            if not s: continue
            t = s[str(th)]
            out.append(f"| {sc} · {lbl} | {s['n']} | {pct(s['funded_access'])} | {pct(t['paid_120'])} | {pct(t['paid_180'])} | {pct(t['paid_270'])} | {pct(t['paid_365'])} | "
                       f"{num(t['median_total_day'])} ({rng(t['p25_total_day'], t['p75_total_day'], num)}) | {usd(t['median_payout'])} | {usd(t['ev_payout'])} | {num(s['median_trades_chain'])} |")
    return '\n'.join(out)


parts = ['# Tables (generated from RESULTS.json)', '',
         f"Parity: {json.dumps(X['parity'])}", '']
for name in ('DI_OFF', 'DI_ON'):
    for cost in ('recorded_exness', 'fixed_cost_stress'):
        parts += [f'## Funded only · {name} · {cost} · request at first flat moment ≥ day 14 with ≥ $20 profit', '', funded_rows(name, cost, 20), '']
    parts += [f'## Payout policy comparison · {name} · recorded_exness', '', threshold_rows(name, 'recorded_exness'), '']
    parts += [f'## End to end (challenge start → first request, $20 policy) · {name}', '', e2e_rows(name, 20), '']
    parts += [f'## End to end ($500 policy) · {name}', '', e2e_rows(name, 500), '']
(R / 'TABLES.md').write_text('\n'.join(parts) + '\n', encoding='utf-8')
print('\n'.join(parts))
