"""Owner 2026-11-10: 4-EA portfolio P4 (Overnight Bias ORB, Nasdaq 5M REPLACE DI OFF, EMA3, Gold Band Wave). Reads the p7.py `p4` job outputs
(CH/F1P/F1U/FU-P4[U]-<risk>.json) and the native all-years ledgers; no new runs. Run from AAA EAs/EA store:
uv run --with pandas --with numpy python "<this>"  -> P4_RESULTS.json, P4_RESULTS.md"""
import importlib.util, json, os
from pathlib import Path

os.environ['EA_STORE_DISABLE_MT5'] = '1'
H = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('p7', H / 'p7.py'); P7 = importlib.util.module_from_spec(spec); spec.loader.exec_module(P7)
RISKS = P7.P4_RISKS


def load(prefix, name, r):
    f = H / f'{prefix}-{name}-{r}.json'
    return json.loads(f.read_text(encoding='utf-8')) if f.exists() else None


pct = lambda x: '-' if x is None else f'{100 * x:.0f}%'  # noqa: E731
usd = lambda x: '-' if x is None else f'${x:,.0f}'  # noqa: E731
day = lambda x: '-' if x is None else f'{x:g}'  # noqa: E731


def main():
    split = P7.data_split.research_split('2019-01-01', '2026-11-10')
    W = {k: (split[n]['start'], split[n]['end_exclusive']) for k, n in (('dev', 'development'), ('val', 'validation'), ('oos', 'oos'))}
    W.update(all=('2019-01-01', '2026-11-10'), stream=('2021-10-07', '2026-10-06'), last_year=('2025-11-10', '2026-11-10'))
    R = P7.native_rows(); port = [r for k in P7.P4_EAS for r in R[k]]
    tw = P7.robustness.three_monte_carlo([r['r'] for r in sorted(port, key=lambda r: r['c'])], runs=1000, seed=20261104)
    out = dict(windows=W, native={w: P7.stats(port, *v) for w, v in W.items()}, years={str(y): P7.stats(port, f'{y}-01-01', f'{y + 1}-01-01')['total_r'] for y in range(2019, 2027)},
               mc=dict(resample=tw['resample']['red_pct'], randomize=tw['randomize']['both']['red_pct'], clumped=tw['reshuffle']['real_drawdown_worse_than_pct']),
               eas={k: {w: P7.stats(R[k], *v) for w, v in W.items()} for k in P7.P4_EAS}, ftmo={}, missing=[])
    for r in RISKS:
        f = dict(two_guard=load('CH', 'P4', r), two_free=load('CH', 'P4U', r), one_guard=load('F1P', 'P4', r), one_free=load('F1U', 'P4U', r), fund_guard=load('FU', 'P4', r), fund_free=load('FU', 'P4U', r))
        out['missing'] += [f'{k}-{r}' for k, v in f.items() if v is None]
        out['ftmo'][r] = {k: (v['mc'] if v else None) for k, v in f.items()}
    (H / 'P4_RESULTS.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8')

    L = ['# P4 = Overnight Bias ORB + Nasdaq 5M REPLACE (DI OFF) + EMA3 + Gold Band Wave', '',
         'FTMO: $100k, Python replay of the 2021-10 -> 2026-10 native streams, Monte Carlo 2,000 paths, in-sample. Guard 1.50 / 2.00% = hypothetical (installers cap lower).', '',
         '## Native, all years (fixed 1% R, each EA its own native run)', '', '| Window | Trades | /month | /day | Win % | PF | Total R | Closed DD R | Worst day R |', '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for w, s in out['native'].items():
        L.append(f"| {w} {W[w][0]} -> {W[w][1]} | {s['trades']} | {s['per_month']} | {s['per_weekday']} | {s['win']} | {s['pf']} | {s['total_r']:+} | {s['closed_dd_r']} | {s['worst_day_r']} |")
    L += ['', f"Years R: {out['years']}", f"Three-way MC: resample red {out['mc']['resample']}%, randomize red {out['mc']['randomize']}%, real DD worse than {out['mc']['clumped']}% of shuffles", '']
    L += ['## FTMO 2-step (pass both phases within 180 days)', '', '| Risk | Guard | Pass | Median days to funded | Funded <= 90 d | Breach | Stalled at buffer | Median trades |', '|---|---|---:|---:|---:|---:|---:|---:|']
    for r in RISKS:
        for g, k in (('guard', 'two_guard'), ('no guard', 'two_free')):
            x = out['ftmo'][r][k]
            L.append(f"| {r}% | {g} | " + (f"{pct(x['pass_both_180'])} | {day(x['median_days_funded'])} | {pct(x['funded_90'])} | {pct(x['breach'])} | {pct(x['stalled_buffer'])} | {day(x['median_trades'])} |" if x else 'missing |||||||'))
    L += ['', '## FTMO 1-Step (pass within 180 days)', '', '| Risk | Guard | Pass | Median days | Pass <= 30 / 60 / 90 d | Breach (daily / max) | Stuck at buffer | Median trades |', '|---|---|---:|---:|---|---|---:|---:|']
    for r in RISKS:
        for g, k in (('guard', 'one_guard'), ('no guard', 'one_free')):
            x = out['ftmo'][r][k]
            L.append(f"| {r}% | {g} | " + (f"{pct(x['pass_180'])} | {day(x['median_days'])} | {pct(x['pass_30'])} / {pct(x['pass_60'])} / {pct(x['pass_90'])} | {pct(x['breach'])} ({pct(x['breach_daily'])} / {pct(x['breach_static'])}) | {pct(x.get('stuck_buffer'))} | {day(x['median_trades'])} |" if x else 'missing |||||||'))
    L += ['', '## Funded $100k, FTMO funded rules, 36-month MC (80% split, no fee subtracted)', '', '| Risk | Guard | $/month while trading (median) | 36 m total median | 36 m total mean | First year median | Breach | Frozen | Still trading | First payout day (median) | Trades / month |', '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in RISKS:
        for g, k in (('guard', 'fund_guard'), ('no guard', 'fund_free')):
            x = out['ftmo'][r][k]
            if not x: L.append(f'| {r}% | {g} | missing ||||||||||'); continue
            n = x['n']; e = x['ends']; br = sum(v for kk, v in e.items() if kk not in ('alive', 'frozen')) / n
            L.append(f"| {r}% | {g} | {usd(x['monthly_income_while_alive_median'])} | {usd(x['income_total_median'])} | {usd(x['income_total_mean'])} | {usd(x['first_year_income_median'])} | {pct(br)} | {pct(e.get('frozen', 0) / n)} | {pct(e.get('alive', 0) / n)} | {day(x['first_payout_day_median'])} | {x['trades_per_month_alive_median']} |")
    L += ['', f"Missing: {out['missing']}"]
    (H / 'P4_RESULTS.md').write_text('\n'.join(L) + '\n', encoding='utf-8'); print('\n'.join(L))


if __name__ == '__main__':
    main()
