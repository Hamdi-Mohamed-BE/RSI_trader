"""Monte Carlo for XAU Weakness production vs market fill (owner 2026-11-03). Source = native ledgers of the 'all' (2019-01 -> 2026-11)
and 'oos' (2024-11 -> 2026-11) runs. Each trade -> R = net / (1% of the closed balance before it). Day-block bootstrap
(Calyx Research Pipeline robustness.day_block_bootstrap convention: 5-weekday blocks, empty weekdays kept), 10,000 paths, seed 20261103,
horizons 3 and 12 months. Sums of R = % of account at 1% risk without compounding. python mc.py"""
import gzip, json, random, sys
from datetime import date, timedelta
from pathlib import Path
R = Path(__file__).resolve().parent
sys.path.insert(0, str(R.parent.parent / 'Calyx Research Pipeline')); import robustness as rb  # noqa: E402
SEED, PATHS, BLOCK = 20261103, 10000, 5
WIN = {'all': (date(2019, 1, 1), date(2026, 11, 1)), 'oos': (date(2024, 11, 1), date(2026, 11, 1))}

def ledger(tag, period):
    T = sorted(json.loads(gzip.open(R / f'native/nw-XAUUSD-{tag}-{period}/trades.json.gz').read()), key=lambda t: t['close_time'])
    bal = 10000.0
    for t in T: t['r'] = t['net_profit'] / (0.01 * bal); bal += t['net_profit']
    return T

def weekdays(a, b):
    out = []; d = a
    while d < b:
        if d.weekday() < 5: out.append(d.isoformat())
        d += timedelta(days=1)
    return out

def run(tag, period, horizon):
    T = ledger(tag, period); cal = weekdays(*WIN[period])
    by = {}
    for t in T: by.setdefault(t['close_time'][:10], []).append(t['r'])
    days = sorted(set(cal) | set(by))          # as robustness.py: weekend-dated closes keep their trades
    seq = [by.get(d, []) for d in days]; n = len(seq); rng = random.Random(SEED); tot, dds, streak = [], [], []
    for _ in range(PATHS):
        path = []
        while len(path) < horizon:
            s = rng.randrange(n)
            for k in range(BLOCK):
                path.append(seq[(s + k) % n])
                if len(path) >= horizon: break
        flat = [v for d in path for v in d]; tot.append(sum(flat)); dds.append(rb.max_drawdown(flat)); streak.append(rb.longest_losing_streak(flat))
    tot.sort(); dds.sort(); streak.sort(); q = lambda a, p: round(rb._quantile(a, p), 2)  # noqa: E731
    ref = rb.day_block_bootstrap(T, horizon, value='r', paths=PATHS, block_days=BLOCK, seed=SEED, calendar_days=cal)
    assert abs(ref['max_drawdown']['p95'] - q(dds, .95)) <= 0.0051, 'mismatch vs robustness.py (2 vs 4 decimals)'
    return dict(tag=tag, source=period, horizon_weekdays=horizon, trades=len(T), mean_r=round(sum(t['r'] for t in T) / len(T), 3),
                total_p05=q(tot, .05), total_p25=q(tot, .25), total_p50=q(tot, .5), total_p75=q(tot, .75), total_p95=q(tot, .95),
                p_loss=round(sum(x < 0 for x in tot) / PATHS, 3), dd_p50=q(dds, .5), dd_p95=q(dds, .95), dd_p99=q(dds, .99),
                streak_p50=q(streak, .5), streak_p95=q(streak, .95))

out = [run(t, p, h) for p in ('all', 'oos') for t in ('PROD', 'ON') for h in (65, 261)]
(R / 'MC.json').write_text(json.dumps(dict(seed=SEED, paths=PATHS, block=BLOCK, results=out), indent=1), encoding='utf-8')
for o in out: print(o)
