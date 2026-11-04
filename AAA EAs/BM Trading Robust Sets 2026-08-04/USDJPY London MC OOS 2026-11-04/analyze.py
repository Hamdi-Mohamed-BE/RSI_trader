"""Full breakdown + Monte Carlo for the USDJPY London native runs (run.py). Stage 6 of PIPELINE.md:
- per window (dev / val / oos / all, fresh $10k each): net, PF, win rate, trades per month / weekday, mean R, closed-balance DD,
  MT5 equity DD figures as reported, losing streak, best-day dependence;
- 'all' broken down by year, weekday, side and exit type;
- three-way Monte Carlo (robustness.three_monte_carlo: reshuffle / resample / randomize, 1,000 runs) on R per trade;
- day-block bootstrap (robustness.day_block_bootstrap, 5-weekday blocks, 10,000 paths) for 3- and 12-month horizons.
R = net / (1% of the closed balance before the trade) -> sums of R = % of the account at 1% without compounding.
-> ANALYSIS.json. python analyze.py"""
import gzip, json, statistics, sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

H = Path(__file__).resolve().parent
sys.path.insert(0, str(H.parents[1] / 'Calyx Research Pipeline'))
import robustness as rb  # noqa: E402

PLAN = json.loads((H / 'PLAN.json').read_text(encoding='utf-8')); WIN = PLAN['windows']


def ledger(period):
    folder = H / f'native/nw-USDJPY-PROD-{period}'
    T = sorted(json.loads(gzip.open(folder / 'trades.json.gz').read()), key=lambda t: t['close_time'])
    bal = 10000.0
    for t in T:
        t['r'] = t['net_profit'] / (0.01 * bal); t['bal_before'] = bal; bal += t['net_profit']
    return T, json.loads((folder / 'run.json').read_text(encoding='utf-8'))


def weekdays(a, b):
    a, b = date.fromisoformat(a), date.fromisoformat(b); out = []
    while a < b:
        if a.weekday() < 5: out.append(a.isoformat())
        a += timedelta(days=1)
    return out


def stats(T, a, b):
    if not T: return dict(trades=0)
    net = [t['net_profit'] for t in T]; R = [t['r'] for t in T]
    months = (date.fromisoformat(b) - date.fromisoformat(a)).days / 30.4375; wd = len(weekdays(a, b))
    bal = peak = 10000.0; dd = 0.0
    for v in net: bal += v; peak = max(peak, bal); dd = max(dd, (peak - bal) / peak)
    gw, gl = sum(v for v in net if v > 0), -sum(v for v in net if v < 0)
    return dict(trades=len(T), trades_per_month=round(len(T) / months, 2), trades_per_weekday=round(len(T) / wd, 3),
                net_usd=round(sum(net), 2), net_pct=round(100 * sum(net) / 10000, 2), pf=round(gw / gl, 3) if gl else None,
                win_pct=round(100 * sum(v > 0 for v in net) / len(net), 2), mean_r=round(statistics.fmean(R), 4),
                avg_win_r=round(statistics.fmean([r for r in R if r > 0]), 3) if any(r > 0 for r in R) else None,
                avg_loss_r=round(statistics.fmean([r for r in R if r < 0]), 3) if any(r < 0 for r in R) else None,
                closed_dd_pct=round(100 * dd, 2), losing_streak=rb.longest_losing_streak(net),
                costs_usd=round(sum(t['total_costs'] for t in T), 2), swap_usd=round(sum(t['swap'] for t in T), 2))


def exit_kind(t):
    c = (t.get('exit_comment') or '').lower()
    if c.startswith('sl'): return 'initial stop (loss)' if t['r'] < -0.05 else 'break-even stop'
    if c.startswith('tp'): return 'target'
    return 'time exit / EA close'


def group(T, key):
    g = defaultdict(list)
    for t in T: g[key(t)].append(t)
    out = {}
    for k in sorted(g):
        net = [t['net_profit'] for t in g[k]]; gl = -sum(v for v in net if v < 0)
        out[k] = dict(trades=len(net), net_usd=round(sum(net), 2), sum_r=round(sum(t['r'] for t in g[k]), 2),
                      pf=round(sum(v for v in net if v > 0) / gl, 3) if gl else None, win_pct=round(100 * sum(v > 0 for v in net) / len(net), 1))
    return out


def bootstrap(T, a, b, horizon):
    cal = weekdays(a, b); boot = rb.day_block_bootstrap(T, horizon, value='r', time='close_time', paths=10000, block_days=5, seed=20261104,
                                                      calendar_days=cal)
    # profit probability needs the totals distribution: redo the same paths for P(total <= 0)
    by = defaultdict(list)
    for t in T: by[t['close_time'][:10]].append(t['r'])
    days = sorted(set(cal) | set(by)); seq = [by.get(d, []) for d in days]; n = len(seq)
    import random
    rng = random.Random(20261104); red = 0
    for _ in range(10000):
        path = []
        while len(path) < horizon:
            s = rng.randrange(n)
            for k in range(5):
                path.append(seq[(s + k) % n])
                if len(path) >= horizon: break
        red += sum(v for d in path for v in d) <= 0
    boot['red_pct'] = round(100 * red / 10000, 2)
    return boot


out = dict(plan=dict(prod_sha=PLAN['prod_sha'], windows=WIN, inputs=PLAN['inputs']), windows={}, native_checks={})
ledgers = {}
for p in ('dev', 'val', 'oos', 'all'):
    T, run = ledger(p); ledgers[p] = T; a, b = WIN[p]
    out['windows'][p] = dict(stats(T, a, b), mt5=run['metrics'] if isinstance(run.get('metrics'), dict) else None)
    out['native_checks'][p] = dict(ok=run['ok'], report_checks=run['report_checks'], input_mismatches=run['input_mismatches'],
                                   journal_flags=run['journal_flags'], real_tick_lines=run['real_tick_lines'], report_sha256=run['report_sha256'])
    out['windows'][p]['dependence'] = rb.dependence(T, value='net_profit', time='close_time')
A = ledgers['all']
out['by_year'] = group(A, lambda t: t['close_time'][:4])
out['by_weekday'] = group(A, lambda t: datetime.fromisoformat(t['open_time']).strftime('%a'))
out['by_side'] = group(A, lambda t: t['side'])
out['by_exit'] = group(A, exit_kind)
months = group(A, lambda t: t['close_time'][:7]); out['months'] = dict(count=len(months), positive=sum(v['net_usd'] > 0 for v in months.values()),
                                                                     worst=min(months.items(), key=lambda kv: kv[1]['net_usd']),
                                                                     best=max(months.items(), key=lambda kv: kv[1]['net_usd']))
per_year = round(len(A) / ((date.fromisoformat(WIN['all'][1]) - date.fromisoformat(WIN['all'][0])).days / 365.25))
RA = [t['r'] for t in A]; RO = [t['r'] for t in ledgers['oos']]
out['three_mc'] = dict(all_full=rb.three_monte_carlo(RA), all_one_year=rb.three_monte_carlo(RA, horizon=per_year),
                       oos_full=rb.three_monte_carlo(RO), oos_one_year=rb.three_monte_carlo(RO, horizon=per_year),
                       cost_ladder_one_year={f'{c:.2f}': rb.three_monte_carlo(RA, horizon=per_year, extra_cost=c)['randomize']['both']
                                             for c in (0.02, 0.05, 0.10, 0.20)},
                       break_even_extra_cost_r=round(statistics.fmean(RA), 4), trades_per_year=per_year)
out['day_block_bootstrap'] = {f'{src}_{h}d': bootstrap(ledgers[src], *WIN[src], h) for src in ('all', 'oos') for h in (65, 261)}
(H / 'ANALYSIS.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8'); print('written ANALYSIS.json')
