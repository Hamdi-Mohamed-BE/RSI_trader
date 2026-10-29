"""Owner 2026-10-29: trade the Nasdaq 5M signals manually on a FUTURES 50K evaluation (owner paste): $49/month, profit target $3,000,
consistency 55% (ASSUMED = best day <= 55% of total profit at the pass), max loss $2,000 (ASSUMED trailing the end-of-day balance and
locking at $50,000, the usual design; the paste does not say), daily loss limit $1,000 (ASSUMED soft: positions liquidated, no more trading
that day, account continues), max 5 mini / 50 micro, reset $49 (one reset credit per monthly rebill), funded activation $149.
Instrument: MNQ micro ($2 per point). The CFD ledger (USTEC, $1 per point per lot) gives points directly: contracts = floor($500 / (2 x stop
points)), min 1, max 50. P&L = contracts x 2 x points - $1.50 round trip per contract (ASSUMED commission + fees); CFD swap dropped.
FLAT = close at 15:10 CT (most futures evaluations forbid holding past the session close; the EA itself holds overnight): exit at the
last 5-minute mark before 15:10 CT. HOLD = the EA's own exits (only if the firm allows overnight). Intraday limits use the worst 5-minute
mark of each trade (trades without marks: their full stop). One position at a time; with FLAT the EA might have taken extra signals after
an early close — not in the ledger. Manual execution (late fills, missed days) NOT modelled. RETRY: a breach resets the account the next day.
Ledgers: Best Prop retest INPUTS-DI_ON / DI_OFF (production Nasdaq 5M, 5-minute marks), 2021-10 -> 2026-10. In-sample, NOT a forecast.
python futures_50k_nasdaq.py -> FUTURES_50K_NASDAQ.json / .md
"""
import json, math, random
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
import funded_sim as f

R = Path(__file__).resolve().parent; B = R.parent; CT = ZoneInfo('America/Chicago'); DAY = 86400.0
SIZE, TARGET, MLL, DLL, CONS = 50000.0, 3000.0, 2000.0, 1000.0, 0.55
RISK, POINT, COMM, MAXC = 500.0, 2.0, 1.50, 50
MONTHLY, RESET, ACTIVATION, HORIZON, SEED = 49.0, 49.0, 149.0, 365, 20261029


def load(di):
    c = json.loads((B / f'Best Prop Portfolio Retest 2026-10-20/INPUTS-{di}.json').read_text(encoding='utf-8'))['candidates']
    out = []
    for x in c:
        if x['ea'] != 'nasdaq-5m-candle-momentum' or not x['cl'] or x['end_censored']: continue
        o = datetime.fromtimestamp(x['op'], CT); flat = datetime(o.year, o.month, o.day, 15, 10, tzinfo=CT).timestamp()
        marks = [(m[0], m[1]) for m in (x.get('marks') or []) if m[0] <= x['cl']]
        hold_min = min([0.0] + [m[1] for m in marks]) if marks else -x['unit_risk']
        if x['cl'] <= flat or not marks:
            flat_pts, flat_cl, flat_min = x['unit_gross'], x['cl'], hold_min
        else:
            pre = [m for m in marks if m[0] <= flat] or marks[:1]
            flat_pts, flat_cl, flat_min = pre[-1][1], min(flat, x['cl']), min([0.0] + [m[1] for m in pre])
        out.append(dict(op=x['op'], cl=x['cl'], stop=x['unit_risk'], hold=x['unit_gross'], hold_min=hold_min, flat=flat_pts, flat_cl=flat_cl, flat_min=flat_min))
    return sorted(out, key=lambda r: r['op'])


def ct_day(t): return datetime.fromtimestamp(t, CT).date()


def mc_paths(rows, seg, n, seed):
    a, b = f.SEG[seg]; m = date.fromisoformat(a); m += timedelta(days=(7 - m.weekday()) % 7); end = date.fromisoformat(b); mons = []
    while m + timedelta(days=28) <= end: mons.append(m); m += timedelta(days=7)
    ops = np.array([r['op'] for r in rows]); rng = random.Random(seed); t0 = f.utc_ts(date(2030, 1, 7)); paths = []
    for _ in range(n):
        p = []
        for k in range(math.ceil(HORIZON / 28) + 1):
            s = mons[rng.randrange(len(mons))]; lo, hi = np.searchsorted(ops, [f.utc_ts(s), f.utc_ts(s) + 28 * DAY]); sh = t0 + k * 28 * DAY - f.utc_ts(s)
            p += [(r, sh) for r in rows[lo:hi]]
        paths.append((t0, p))
    return paths


def hist_paths(rows, seg):
    a, b = f.SEG[seg]; d = date.fromisoformat(a); out = []
    while f.utc_ts(d) + HORIZON * DAY <= f.utc_ts(b):
        if d.weekday() < 5: out.append((f.utc_ts(d), [(r, 0.0) for r in rows if r['op'] >= f.utc_ts(d)]))
        d += timedelta(days=1)
    return out


def attempt_chain(t0, trades, mode, cost_r):
    t_end = t0 + HORIZON * DAY; fresh = True; resets = 0; ntr = 0; first = None; prev_cl = -1.0; blocked = None
    for r, sh in trades:
        op = r['op'] + sh
        if op >= t_end: break
        if op < t0: continue
        if mode == 'HOLD' and op < prev_cl: continue
        d = ct_day(op)
        if d == blocked: continue                                     # a reset account starts the next trading day
        if fresh:
            bal, floor, eod_high, locked, cur_day, day_start, dll_hit, day_pnl = SIZE, SIZE - MLL, SIZE, False, None, SIZE, False, {}
            fresh = False
        if d != cur_day:
            if cur_day is not None:                                   # end of the previous trading day: trail the floor on the EOD balance
                eod_high = max(eod_high, bal)
                if not locked:
                    floor = max(floor, min(eod_high - MLL, SIZE)); locked = floor >= SIZE
            cur_day, day_start, dll_hit = d, bal, False
        if dll_hit: continue
        stop = r['stop']; n = max(1, min(MAXC, int(math.floor(RISK / (POINT * stop) + 1e-9))))
        pts, worst, cl = (r['flat'], r['flat_min'], r['flat_cl']) if mode == 'FLAT' else (r['hold'], r['hold_min'], r['cl'])
        pnl = n * POINT * (pts - cost_r * stop) - n * COMM; low = bal + n * POINT * worst
        prev_cl = cl + sh; ntr += 1
        if low <= floor:                                              # trailing max loss touched intraday -> breach, reset tomorrow
            resets += 1; first = first or ('breach', (op - t0) / DAY); fresh = True; blocked = d; continue
        if low - day_start <= -DLL:                                   # daily loss limit: liquidated at -$1,000 for the day
            pnl = (day_start - DLL) - bal; dll_hit = True
        bal += pnl; kd = d if mode == 'FLAT' else ct_day(cl + sh); day_pnl[kd] = day_pnl.get(kd, 0.0) + pnl
        prof = bal - SIZE
        if prof >= TARGET and max(day_pnl.values()) <= CONS * prof:
            days = (cl + sh - t0) / DAY; first = first or ('pass', days)
            return dict(funded=days, resets=resets, trades=ntr, first=first, contracts=n)
    return dict(funded=None, resets=resets, trades=ntr, first=first or ('open', None), contracts=None)



def summary(res):
    fd = np.array([r['funded'] if r['funded'] is not None else -1.0 for r in res]); ok = fd >= 0
    rs = np.array([r['resets'] for r in res]); tr = np.array([r['trades'] for r in res])
    months = np.where(ok, np.ceil(np.maximum(fd, 1) / 30), 12); cost = MONTHLY * months + RESET * np.maximum(0, rs - (months - 1)) + np.where(ok, ACTIVATION, 0)
    first = [r['first'][0] for r in res]; fp = [r['first'][1] for r in res if r['first'][0] == 'pass']
    span = np.where(ok, np.maximum(fd, 1), HORIZON)
    q = lambda v, p: round(float(np.percentile(v, p)), 0) if len(v) else None  # noqa: E731
    return dict(paths=len(res), first_pass=round(first.count('pass') / len(res), 3), first_breach=round(first.count('breach') / len(res), 3),
                first_pass_day=q(fp, 50), within={d: round(float((ok & (fd <= d)).mean()), 3) for d in (14, 30, 60, 90, 180, 365)},
                days_median=q(fd[ok], 50), days_p25=q(fd[ok], 25), days_p75=q(fd[ok], 75), resets_mean=round(float(rs.mean()), 2),
                cost_mean=round(float(cost.mean()), 0), cost_median=q(cost, 50), cost_if_funded_median=q(cost[ok], 50),
                trades_month=round(float(np.median(tr / (span / 30.4375))), 1), trades_day=round(float(np.median(tr / span)), 2))


def main():
    out = {}
    for di in ('DI_ON', 'DI_OFF'):
        rows = load(di); n_cross = sum(1 for r in rows if r['flat_cl'] < r['cl'])
        mc = mc_paths(rows, 'all', 3000, SEED); hist = hist_paths(rows, 'all'); seg = {s: mc_paths(rows, s, 1500, SEED + i + 1) for i, s in enumerate(('dev', 'val', 'oos'))}
        cn = [max(1, min(MAXC, int(RISK // (POINT * r['stop'])))) for r in rows]
        for mode in ('FLAT', 'HOLD'):
            for cost in (0.0, 0.10):
                k = f"{di}|{mode}|{cost}"
                o = dict(di=di, mode=mode, cost_r=cost, trades_ledger=len(rows), crossing_1510ct=n_cross, contracts_median=float(np.median(cn)),
                         risk_median=round(float(np.median([c * POINT * r['stop'] for c, r in zip(cn, rows)])), 0),
                         mc=summary([attempt_chain(t0, p, mode, cost) for t0, p in mc]), hist=summary([attempt_chain(t0, p, mode, cost) for t0, p in hist]))
                if cost == 0.0:
                    o.update({s: summary([attempt_chain(t0, p, mode, cost) for t0, p in pp]) for s, pp in seg.items()})
                out[k] = o; m = o['mc']
                print(k, 'first pass/breach', m['first_pass'], m['first_breach'], 'median days', m['days_median'], 'within', m['within'], 'cost', m['cost_mean'], flush=True)
    (R / 'FUTURES_50K_NASDAQ.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8')
    pct = lambda v: f'{100 * v:.0f}%'  # noqa: E731
    md = ['# Nasdaq 5M signals, $500 per trade (MNQ), futures 50K evaluation (generated by futures_50k_nasdaq.py)', '',
          'Rules from the owner paste; trailing EOD max loss, soft daily limit and 55% best-day consistency are assumptions. Retry after a breach, up to 365 days.',
          'MC = 3,000 resampled paths (history in brackets). In-sample, NOT a forecast.', '',
          '| DI | Holding | Extra cost | 1st attempt pass / breach | Funded ≤ 14 / 30 / 60 / 90 / 180 d | Median days to funded (p25–p75) [hist] | Resets (mean) | Total cost mean / median | Trades / month (/ day) |',
          '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for v in out.values():
        m, h = v['mc'], v['hist']; w = m['within']
        md.append(f"| {v['di']} | {v['mode']} | {v['cost_r']}R | {pct(m['first_pass'])} / {pct(m['first_breach'])} | {pct(w[14])} / {pct(w[30])} / {pct(w[60])} / {pct(w[90])} / {pct(w[180])} | "
                  f"{m['days_median']} ({m['days_p25']}–{m['days_p75']}) [{h['days_median']}] | {m['resets_mean']} | ${m['cost_mean']:,.0f} / ${m['cost_median']:,.0f} | {m['trades_month']} ({m['trades_day']}) |")
    md += ['', '## By market period (MC, no extra cost): median days / funded ≤ 30 d', '', '| DI | Holding | 2021-23 | 2023-24 | 2024-26 |', '|---|---|---:|---:|---:|']
    for v in out.values():
        if 'dev' in v:
            md.append(f"| {v['di']} | {v['mode']} | " + ' | '.join(f"{v[s]['days_median']} d / {pct(v[s]['within'][30])}" for s in ('dev', 'val', 'oos')) + ' |')
    (R / 'FUTURES_50K_NASDAQ.md').write_text('\n'.join(md) + '\n', encoding='utf-8'); print('\n'.join(md))


if __name__ == '__main__':
    main()
