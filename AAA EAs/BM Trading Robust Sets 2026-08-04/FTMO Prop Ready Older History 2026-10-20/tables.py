"""Print markdown tables from OLDER-SUMMARY.json and BOOTSTRAP-SUMMARY.json (no computation of new outcomes)."""
import json, sys
from pathlib import Path

R = Path(__file__).resolve().parent
pct = lambda x: '—' if x is None else f'{100 * x:.1f}%'  # noqa: E731
num = lambda x: '—' if x is None else f'{x:g}'  # noqa: E731


def older():
    s = json.loads((R / 'OLDER-SUMMARY.json').read_text(encoding='utf-8'))
    print(f"## Part A — older history replay ({s['window'][0]} → {s['window'][1]}, {s['starts']} starts)\n")
    print('| Policy | Costs | Handover | Breaches | Both phases ≤ 60 / 90 / 120 / 180 days | Unfinished at 180 d | Median days to both (completed) | Median days to funded | Phase 1 ≤ 60 d | Worst equity DD $ | Worst day $ | Distinct pass dates | Median trades (/month, /weekday) |')
    print('|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---|')
    for k, v in s['results'].items():
        p, c, h = k.split('|'); x = v['summary']; w = x['both_within']
        print(f"| {p} | {c.replace('_exness', '').replace('fixed_cost_', '')} | {'next day' if h.startswith('next') else '2 business days'} | {pct(x['breach_share'])} | "
              f"{pct(w['60'])} / {pct(w['90'])} / {pct(w['120'])} / {pct(w['180'])} | {pct(x['unfinished_share'])} | {num(x['median_days_both'])} | {num(x['median_days_funded'])} | "
              f"{pct(x['phase1_within_60'])} | {x['eqdd_max']:,.0f} | {x['day_max']:,.0f} | {v['distinct_pass_dates']} | {num(x['median_trades'])} ({x['median_trades_per_month']}, {x['median_trades_per_weekday']}) |")
    print('\n### By start year (recorded costs, next-day handover)\n')
    print('| Policy | Start year | Starts | Both ≤ 180 d | Median days to both | Breaches | Worst equity DD $ |')
    print('|---|---|---:|---:|---:|---:|---:|')
    for p in ('FLAT50', 'FLAT100'):
        for y, x in s['results'][f'{p}|recorded_exness|next_prague_midnight']['by_start_year'].items():
            print(f"| {p} | {y} | {x['n']} | {pct(x['both_within']['180'])} | {num(x['median_days_both'])} | {pct(x['breach_share'])} | {x['eqdd_max']:,.0f} |")
    print(f"\nFLAT100 survives the pre-declared older-history rule: **{s['flat100_survives']}**\n")


def boot():
    s = json.loads((R / 'BOOTSTRAP-SUMMARY.json').read_text(encoding='utf-8'))
    print(f"## Part B — 4-week block bootstrap ({s['paths']:,} paired paths per pool, seed {s['seed']}; {s['excluded_end_censored']} end-censored candidates excluded)\n")
    print('| Pool | Policy | Costs | P(breach) | P(both ≤ 60 / 90 / 120 / 180 d) | P(unfinished at 180 d) | Median days to both | Median days to funded | Equity DD p95 / p99 $ | Worst day p95 / p99 $ | Median trades (/month) |')
    print('|---|---|---|---:|---|---:|---:|---:|---|---|---|')
    for k, x in s['results'].items():
        pool, p, c = k.split('|'); w = x['both_within']
        print(f"| {pool} | {p} | {c.replace('_exness', '').replace('fixed_cost_', '')} | {pct(x['breach_share'])} | {pct(w['60'])} / {pct(w['90'])} / {pct(w['120'])} / {pct(w['180'])} | "
              f"{pct(x['unfinished_share'])} | {num(x['median_days_both'])} | {num(x['median_days_funded'])} | {x['eqdd_p95']:,.0f} / {x['eqdd_p99']:,.0f} | {x['day_p95']:,.0f} / {x['day_p99']:,.0f} | "
              f"{num(x['median_trades'])} ({x['median_trades_per_month']}) |")
    print(f"\nFLAT100 P(breach) ≤ 5% in all pools and cost scenarios: **{s['flat100_breach_le_5pct_all']}**; ≤ 1%: **{s['flat100_breach_le_1pct_all']}**\n")


if __name__ == '__main__':
    {'older': older, 'boot': boot}[sys.argv[1]]()
