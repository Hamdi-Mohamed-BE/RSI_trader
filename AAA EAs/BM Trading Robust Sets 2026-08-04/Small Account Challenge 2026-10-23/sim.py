"""Small account challenge simulation (PLAN.md). No MT5.

python sim.py theory | run <stream> | table
"""
import bisect, json, math, random, statistics, sys, time
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

R = Path(__file__).resolve().parent; B = R.parent; Z = ZoneInfo('Europe/Prague')
START_BAL = 100.0; GOALS = (5000.0, 10000.0); BUST = 10.0; HORIZON = 730; DAY = 86400
DATA_START, DATA_END, HIST_LAST = date(2021, 10, 7), date(2026, 10, 6), date(2024, 10, 6)
MC_PATHS, MC_SEED, BLOCK_DAYS = 5000, 20261023, 28
POLICIES = {'F03': [(0, .03)], 'F05': [(0, .05)], 'F10': [(0, .10)], 'F15': [(0, .15)], 'F20': [(0, .20)],
            'LADDER_10': [(0, .10), (1000, .05), (5000, .025)], 'LADDER_20': [(0, .20), (1000, .10), (5000, .05)]}
STREAMS = {'NAS5M': ('Best Prop Portfolio Retest 2026-10-20/INPUTS-DI_ON.json', {'nasdaq-5m-candle-momentum'}),
           'PR9': ('Best Prop Portfolio Retest 2026-10-20/INPUTS-DI_ON.json', None),
           'FTMO17': ('Portfolio Prop Comparison 2026-10-22/INPUTS-FTMO17.json', None)}
SPECS = json.loads((R / 'SPECS.json').read_text(encoding='utf-8'))['symbols']


def midnight(d): return datetime.combine(d, datetime.min.time(), tzinfo=Z).timestamp()


def load(stream):
    path, only = STREAMS[stream]
    data = json.loads((B / path).read_text(encoding='utf-8'))
    rows = []
    for c in data['candidates']:
        if c['end_censored'] or (only and c['ea'] not in only): continue
        rows.append((c['op'], c['cl'], c['ea'], c['symbol'], c['unit_risk'], c['unit_gross'] + c['unit_commission'] + c['unit_swap']))
    rows.sort(); return rows


def risk_for(policy, balance):
    f = POLICIES[policy][0][1]
    for threshold, value in POLICIES[policy]:
        if balance >= threshold: f = value
    return f


def path(trades, t0, policy):
    """trades: (op, cl, ea, symbol, unit_risk, unit_net) with op >= t0, sorted by op. Closed-balance sizing at entry."""
    horizon = t0 + HORIZON * DAY; events = []
    for i, tr in enumerate(trades):
        if tr[0] >= horizon: break
        events.append((tr[0], 1, i)); events.append((tr[1], 0, i))  # closes before opens at equal time
    events.sort()
    bal = START_BAL; open_ = {}; busy = set(); reached = {}; bust_t = None; half_t = None; n = skipped = 0; peak = bal; maxdd = 0.; over = 0; bal1y = None
    for t, kind, i in events:
        if bal1y is None and t >= t0 + 365 * DAY: bal1y = bal
        if t >= horizon: break
        op, cl, ea, sym, ur, un = trades[i]
        if kind == 0:
            if i not in open_: continue
            lots = open_.pop(i); busy.discard(ea); bal = round(bal + lots * un, 2); n += 1
            peak = max(peak, bal); maxdd = max(maxdd, (peak - bal) / peak)
            for g in GOALS:
                if g not in reached and bal >= g: reached[g] = t
            if half_t is None and bal < START_BAL / 2: half_t = t
            if bal < BUST: bust_t = t; break
        else:
            if ea in busy or bust_t is not None: continue
            spec = SPECS[sym]; budget = risk_for(policy, bal) * bal
            lots = math.floor(budget / ur / spec['step'] + 1e-9) * spec['step']
            if lots < spec['min'] - 1e-9:
                if spec['min'] * ur <= 3 * budget + 1e-9: lots = spec['min']
                else: skipped += 1; continue
            lots = min(lots, spec['max'])
            open_[i] = lots; busy.add(ea)
            if sum(open_[j] * trades[j][4] for j in open_) > bal: over += 1
    days = lambda t: None if t is None else round((t - t0) / DAY, 1)  # noqa: E731
    return dict(r5=days(reached.get(5000.0)), r10=days(reached.get(10000.0)), bust=days(bust_t), half=days(half_t), bal_end=bal, bal_1y=bal1y if bal1y is not None else bal,
                trades=n, skipped=skipped, maxdd=round(maxdd, 4), over_exposed=over)


def summarize(rows):
    n = len(rows); med = lambda v: round(statistics.median(v), 1) if v else None  # noqa: E731
    q = lambda v, p: sorted(v)[min(len(v) - 1, int(p * len(v)))] if v else None  # noqa: E731
    out = dict(n=n, reach_5k=round(sum(r['r5'] is not None for r in rows) / n, 4), reach_10k=round(sum(r['r10'] is not None for r in rows) / n, 4),
               bust=round(sum(r['bust'] is not None for r in rows) / n, 4),
               days_5k_median=med([r['r5'] for r in rows if r['r5'] is not None]), days_10k_median=med([r['r10'] for r in rows if r['r10'] is not None]),
               days_10k_p25=q([r['r10'] for r in rows if r['r10'] is not None], .25), days_10k_p75=q([r['r10'] for r in rows if r['r10'] is not None], .75),
               days_bust_median=med([r['bust'] for r in rows if r['bust'] is not None]),
               bal_1y_median=round(statistics.median(r['bal_1y'] for r in rows), 2), bal_2y_median=round(statistics.median(r['bal_end'] for r in rows), 2),
               maxdd_median=round(statistics.median(r['maxdd'] for r in rows), 4), skipped_median=statistics.median(r['skipped'] for r in rows),
               over_exposed_share=round(sum(r['over_exposed'] > 0 for r in rows) / n, 4))
    alive = [r for r in rows if r['bust'] is None]
    out['trades_per_month_median'] = round(statistics.median(r['trades'] / (HORIZON / 30.4375) for r in alive), 2) if alive else None
    out['trades_per_day_median'] = round(out['trades_per_month_median'] / 30.4375, 3) if alive else None
    out['ended_below_100'] = round(sum(r['bal_end'] < START_BAL for r in rows) / n, 4)
    out['ever_below_50'] = round(sum(r['half'] is not None for r in rows) / n, 4)
    out['days_below_50_median'] = med([r['half'] for r in rows if r['half'] is not None])
    out['neither'] = round(1 - sum((r['r5'] is not None) or (r['bust'] is not None) for r in rows) / n, 4)
    return out


def mc_paths(trades, rng, n):
    """Block bootstrap: 26 random 4-week blocks of real trades (by open time), shifted onto one synthetic timeline."""
    ops = [t[0] for t in trades]; mondays, m = [], date(2021, 10, 11)
    while m + timedelta(days=BLOCK_DAYS) <= DATA_END: mondays.append(m); m += timedelta(days=7)
    index = {m: (bisect.bisect_left(ops, midnight(m)), bisect.bisect_left(ops, midnight(m + timedelta(days=BLOCK_DAYS)))) for m in mondays}
    t0 = midnight(date(2030, 1, 7))
    for _ in range(n):
        rows = []
        for k in range(HORIZON // BLOCK_DAYS + 1):
            src = mondays[rng.randrange(len(mondays))]; shift = t0 + k * BLOCK_DAYS * DAY - midnight(src); lo, hi = index[src]
            rows += [(a + shift, b + shift, ea, s, u, v) for a, b, ea, s, u, v in trades[lo:hi]]
        rows.sort(); yield t0, rows


def run(stream):
    began = time.time(); trades = load(stream); ops = [t[0] for t in trades]
    out = dict(stream=stream, trades=len(trades), policies={})
    for pol in POLICIES:
        hist = []; d = DATA_START
        while d <= HIST_LAST:
            if d.weekday() < 5:
                t0 = midnight(d); hist.append(path(trades[bisect.bisect_left(ops, t0):], t0, pol))
            d += timedelta(days=1)
        rng = random.Random(MC_SEED); mc = [path(rows, t0, pol) for t0, rows in mc_paths(trades, rng, MC_PATHS)]
        out['policies'][pol] = dict(hist=summarize(hist), mc=summarize(mc))
        h, m = out['policies'][pol]['hist'], out['policies'][pol]['mc']
        print(stream, pol, 'hist 10k', h['reach_10k'], 'bust', h['bust'], '| MC 10k', m['reach_10k'], 'bust', m['bust'], 'days10k', m['days_10k_median'], f'{time.time() - began:.0f}s', flush=True)
    (R / f'RESULT-{stream}.json').write_text(json.dumps(out, indent=1), encoding='utf-8')


def theory():
    """Part A: ±20% per trade, 1:1, from $100; goal $5k/$10k; bust < $10; 400 trades max."""
    out = {}
    for p in (.50, .55, .60, .65):
        rng = random.Random(MC_SEED); res = Counter(); n10 = []
        for _ in range(100000):
            b = 100.0; k = 0; hit5 = False
            while k < 400:
                k += 1; b *= 1.2 if rng.random() < p else 0.8
                if b >= 5000 and not hit5: hit5 = True; res['5k'] += 1
                if b >= 10000: res['10k'] += 1; n10.append(k); break
                if b < 10: res['bust'] += 1; break
        out[f'{p:.2f}'] = dict(reach_5k=res['5k'] / 1e5, reach_10k=res['10k'] / 1e5, bust=res['bust'] / 1e5,
                               trades_to_10k_median=statistics.median(n10) if n10 else None,
                               growth_per_trade=round(math.exp(p * math.log(1.2) + (1 - p) * math.log(0.8)) - 1, 5))
        print(p, out[f'{p:.2f}'])
    (R / 'THEORY.json').write_text(json.dumps(out, indent=1), encoding='utf-8')


def table():
    pct = lambda v: '-' if v is None else f'{100 * v:.1f}%'; usd = lambda v: '-' if v is None else f'${v:,.0f}'  # noqa: E731
    th = json.loads((R / 'THEORY.json').read_text(encoding='utf-8'))
    L = ['# Small Account Challenge — results (generated)', '', '## A. The classic 20 pips challenge as a ±20% 1:1 bet (no market data, 100,000 paths)', '',
         '| Win rate | Growth per trade (median path) | Reach $5k | Reach $10k | Bust (<$10) | Median trades to $10k |', '|---:|---:|---:|---:|---:|---:|']
    for p, v in th.items():
        L.append(f"| {float(p) * 100:.0f}% | {100 * v['growth_per_trade']:+.2f}% | {pct(v['reach_5k'])} | {pct(v['reach_10k'])} | {pct(v['bust'])} | {v['trades_to_10k_median'] or '-'} |")
    for src, title in (('mc', 'C. Monte Carlo, 5,000 paths, 2 years'), ('hist', 'B. History, every weekday start 2021-10-07 → 2024-10-06, 2 years')):
        L += ['', f'## {title}', '', '| Stream | Policy | Reach $5k | Median days to $5k | Reach $10k | Median days to $10k (p25–p75) | Ever halved (<$50) / median days | Bust (<$10) | Median days to bust | Ended below $100 | Median balance 1y / 2y | Median max DD | Trades / month | / day |',
              '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
        for stream in STREAMS:
            p = R / f'RESULT-{stream}.json'
            if not p.is_file(): continue
            for pol, v in json.loads(p.read_text(encoding='utf-8'))['policies'].items():
                s = v[src]
                L.append(f"| {stream} | {pol} | {pct(s['reach_5k'])} | {s['days_5k_median'] or '-'} | {pct(s['reach_10k'])} | {s['days_10k_median'] or '-'} ({s['days_10k_p25'] or '-'}–{s['days_10k_p75'] or '-'}) | "
                         f"{pct(s['ever_below_50'])} / {s['days_below_50_median'] or '-'} | {pct(s['bust'])} | {s['days_bust_median'] or '-'} | {pct(s['ended_below_100'])} | {usd(s['bal_1y_median'])} / {usd(s['bal_2y_median'])} | {pct(s['maxdd_median'])} | {s['trades_per_month_median'] or '-'} | {s['trades_per_day_median'] or '-'} |")
    (R / 'RESULTS.md').write_text('\n'.join(L) + '\n', encoding='utf-8'); print('\n'.join(L))


if __name__ == '__main__':
    {'theory': theory, 'run': lambda: run(sys.argv[2]), 'table': table}[sys.argv[1]]()
