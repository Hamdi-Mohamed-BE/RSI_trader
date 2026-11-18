"""Multi-firm funded income (rules in RULES.md, frozen before the run). Run: python sim.py days | run | combos"""
import json, random, statistics, sys
from datetime import date, datetime, time, timedelta, timezone
from itertools import product
from pathlib import Path

import numpy as np

H = Path(__file__).resolve().parent; B = H.parent
import os
SRC_BASE = B / 'Best 1-Step UK100 Monday 2026-11-11/INPUTS-B1XM.json'
VAR = os.environ.get('VARIANT', '')   # '' = as installed, '_nohedge' = no-opposite-trade rule (INPUTS-NOHEDGE.json)
SRC = SRC_BASE if not VAR else H / ('INPUTS-NOHEDGE.json' if VAR == '_nohedge' else f'INPUTS{VAR}.json')
HORIZON = 1096; MONTH = 30.4375; NM = 36; PATHS = 1000; SEED = 20261117; BLOCK = 28
RISKS = (0.0025, 0.004, 0.005, 0.0075, 0.01)
EUR = 1.16
COST = float(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[1] in ('run', 'combos') else 0.0   # extra cost in R per closed trade (stress)
TAG = VAR + ('' if COST == 0 else f'_cost{COST:g}')
# daily basis: 'bal' = day-start balance, 'max' = higher of day-start balance / equity, 'init' = fixed % of initial measured from the higher
TYPES = {
    'FTMO_1S': dict(size=1e5, fee=499 * EUR, refund=0, phases=[(.10, 0, 0)], best=.50, daily=.03, dbasis='bal', ml=.10, mk='trail_lock', split=.90, first=14, cycle=14, minpay=0.0, cap='FTMO'),
    'FTMO_2S': dict(size=1e5, fee=540 * EUR, refund=540 * EUR, phases=[(.10, 4, 0), (.05, 4, 0)], best=None, daily=.05, dbasis='bal', ml=.10, mk='static', split=.80, first=14, cycle=14, minpay=0.0, cap='FTMO'),
    'FP_STD': dict(size=1e5, fee=605, refund=0, phases=[(.08, 3, 0), (.05, 3, 0)], best=None, daily=.05, dbasis='max', ml=.10, mk='static', split=.80, first=14, cycle=14, minpay=.01, cap='FP'),
    'FP_PRO': dict(size=1e5, fee=513, refund=0, phases=[(.06, 0, 0), (.06, 0, 0)], best=None, daily=.03, dbasis='max', ml=.06, mk='static', split=.80, first=14, cycle=14, minpay=.01, cap='FP'),
    'T5_HS': dict(size=1e5, fee=495, refund=495, phases=[(.10, 0, 3), (.05, 0, 3)], best=None, daily=.05, dbasis='max', ml=.10, mk='static', split=.80, first=14, cycle=14, minpay=0.0, cap='T5'),
    'FN_2S25': dict(size=2.5e4, fee=200, refund=0, phases=[(.08, 5, 0), (.05, 5, 0)], best=None, daily=.05, dbasis='max', ml=.10, mk='static', split=.80, first=21, cycle=14, minpay=0.0, cap='FN'),
}


def last_sunday(y, m):
    d = (date(y, m + 1, 1) if m < 12 else date(y + 1, 1, 1)) - timedelta(days=1)
    while d.weekday() != 6: d -= timedelta(days=1)
    return datetime.combine(d, time(1), timezone.utc).timestamp()


def prague_midnight(d):
    s = datetime.combine(d, time(0), timezone.utc).timestamp()
    return s - (7200 if last_sunday(d.year, 3) <= s - 7200 < last_sunday(d.year, 10) else 3600)


def build_days():
    D = json.loads(SRC.read_text(encoding='utf-8')); t0, t1 = D['year_begin_epoch'], D['year_end_exclusive_epoch']
    d0 = date.fromisoformat(D['window'][0]); nd = (date.fromisoformat(D['window'][1]) - d0).days
    mids = np.array([prague_midnight(d0 + timedelta(days=i)) for i in range(nd + 1)]); assert mids[0] == t0 and mids[-1] == t1
    T, dE, dC, cnt = [], [], [], []; total = 0.0; n = 0
    for c in D['candidates']:
        if c['cl'] is None: c = dict(c, cl=t1 - 1)   # still open at the data end: booked at its last value (same as the source ledger)
        ur = c['unit_risk']; ec = c['entry_unit_cost']; R = (c['unit_gross'] + c['unit_commission'] + c['unit_swap']) / ur; prev = ec / ur
        T.append(c['op']); dE.append(prev); dC.append(0.0); cnt.append(0)
        for mk in c['marks']:
            if mk[0] >= c['cl']: break
            v = (mk[1] + ec) / ur; T.append(mk[0]); dE.append(v - prev); dC.append(0.0); cnt.append(0); prev = v
        T.append(c['cl']); dE.append(R - prev); dC.append(R); cnt.append(1); total += R; n += 1
    o = np.argsort(np.array(T), kind='stable'); T = np.array(T)[o]; dE = np.array(dE)[o]; dC = np.array(dC)[o]; cnt = np.array(cnt)[o]
    E = np.cumsum(dE); C = np.cumsum(dC); di = np.searchsorted(mids, T, 'right') - 1; assert di.min() >= 0 and di.max() < nd
    rows = []; e_prev = c_prev = 0.0; j = 0
    for d in range(nd):
        k = j
        while k < len(T) and di[k] == d: k += 1
        if k > j:
            mn = min(e_prev, float(E[j:k].min())); e1, c1 = float(E[k - 1]), float(C[k - 1]); ntr = int(cnt[j:k].sum())
        else:
            mn, e1, c1, ntr = e_prev, e_prev, c_prev, 0
        rows.append((c1 - c_prev, e_prev - c_prev, mn - c_prev, e1 - c1, ntr)); e_prev, c_prev, j = e1, c1, k
    out = dict(source=str(SRC), trades=n, total_r=round(total, 2), days=nd, start=D['window'][0], end_exclusive=D['window'][1], rows=rows)
    (H / f'DAYS{VAR}.json').write_text(json.dumps(out), encoding='utf-8'); print('trades', n, 'total R', round(total, 2), 'days', nd, 'worst day min eq R', round(min(r[2] for r in rows), 2))


def account(rows, T, f):
    """One slot of type T at risk f over len(rows) days. Returns monthly net income list, stats."""
    inc = [0.0] * NM; fees = [0.0] * NM; st = dict(buys=0, breaches_ch=0, breaches_f=0, funded=0, payouts=0, first_payout_day=None, days_funded=0, first_funded_day=None, buys_to_first_funded=None, refunds=0.0)
    state = 'buy'; size = T['size']
    for d, (dc, fl0, mn, fl1, ntr) in enumerate(rows):
        if COST: dc -= COST * ntr; mn -= COST * ntr
        m = min(NM - 1, int(d / MONTH))
        if state == 'buy':
            fees[m] += T['fee']; st['buys'] += 1; state = 'ch'; ph = 0; b = hwm = 1.0; nd = npd = 0; dp = []; refund_due = T['refund']
        if state == 'wait':
            if d < ready: continue
            state = 'fund'; b = hwm = 1.0; dp = []; next_pay = d + T['first']; st['funded'] += 1
            if st['first_funded_day'] is None: st['first_funded_day'] = d; st['buys_to_first_funded'] = st['buys']
        if state == 'fund': st['days_funded'] += 1
        eq0 = b + f * fl0; anchor = b if T['dbasis'] == 'bal' else max(b, eq0)
        floor = (1 - T['ml']) if T['mk'] == 'static' else min(hwm - T['ml'], 1.0)
        mineq = b + f * mn
        if mineq <= floor + 1e-12 or anchor - mineq >= T['daily'] - 1e-12:
            st['breaches_ch' if state == 'ch' else 'breaches_f'] += 1; state = 'buy'; continue
        b += f * dc; hwm = max(hwm, b); dp.append(f * dc)
        if ntr: nd += 1 if state == 'ch' else 0
        if state == 'ch':
            if f * dc >= 0.005: npd += 1
            tgt, mind, minp = T['phases'][ph]; prof = b - 1
            ok_best = T['best'] is None or (prof > 0 and max(dp) <= T['best'] * prof + 1e-12)
            if prof >= tgt - 1e-12 and nd >= mind and npd >= minp and ok_best:
                ph += 1; b = hwm = 1.0; nd = npd = 0; dp = []
                if ph == len(T['phases']): state = 'wait'; ready = d + 4
        elif d >= next_pay:
            prof = b - 1; ok_best = T['best'] is None or max(dp) <= T['best'] * prof + 1e-12
            if prof > 0 and prof >= T['minpay'] and ok_best:
                inc[m] += T['split'] * prof * size + refund_due; st['refunds'] += refund_due; refund_due = 0; st['payouts'] += 1
                if st['first_payout_day'] is None: st['first_payout_day'] = d
                b = hwm = 1.0; dp = []; next_pay = d + T['cycle']
    return [i - x for i, x in zip(inc, fees)], st


def mc_paths(rows):
    rnd = random.Random(SEED); nb = len(rows) // BLOCK; need = HORIZON // BLOCK + 1; out = []
    for _ in range(PATHS):
        p = []
        for _ in range(need): k = rnd.randrange(nb); p.extend(rows[k * BLOCK:(k + 1) * BLOCK])
        out.append(p[:HORIZON])
    return out


def run():
    D = json.loads((H / f'DAYS{VAR}.json').read_text()); rows = [tuple(r) for r in D['rows']]; paths = mc_paths(rows)
    hist = [rows[s:s + HORIZON] for s in range(0, len(rows) - HORIZON + 1, 14)]
    res = {}
    for name, T in TYPES.items():
        for f in RISKS:
            k = f'{name}@{f * 100:g}'; out = {}
            for ev, P in (('mc', paths), ('hist', hist)):
                M, S = zip(*(account(p, T, f) for p in P)); M = np.array(M)
                tot = M.sum(1); fp = [s['first_payout_day'] for s in S if s['first_payout_day'] is not None]
                out[ev] = dict(n=len(P), monthly_mean=round(float(tot.mean() / NM), 0), monthly_median=round(float(np.median(tot) / NM), 0),
                               total_p10=round(float(np.percentile(tot, 10)), 0), total_p90=round(float(np.percentile(tot, 90)), 0), loss_36m=round(float((tot < 0).mean() * 100), 1),
                               first_year_mean=round(float(M[:, :12].sum(1).mean()), 0), last_two_years_mean_month=round(float(M[:, 12:].sum(1).mean() / 24), 0),
                               fees_mean=round(float(np.mean([s['buys'] for s in S]) * T['fee']), 0), buys_mean=round(float(np.mean([s['buys'] for s in S])), 2),
                               breaches_funded_mean=round(float(np.mean([s['breaches_f'] for s in S])), 2), breaches_challenge_mean=round(float(np.mean([s['breaches_ch'] for s in S])), 2),
                               payouts_mean=round(float(np.mean([s['payouts'] for s in S])), 1), never_paid=round(100 * (1 - len(fp) / len(P)), 1),
                               first_payout_day_median=round(statistics.median(fp), 0) if fp else None, funded_share=round(float(np.mean([s['days_funded'] for s in S]) / HORIZON * 100), 1))
                ff = [s['first_funded_day'] for s in S if s['first_funded_day'] is not None]; nf = len(P)
                out[ev].update(funded_within={w: round(100 * sum(1 for x in ff if x <= w) / nf, 1) for w in (30, 60, 90, 180, 365)},
                               first_funded_day_median=round(statistics.median(ff), 0) if ff else None, first_funded_day_mean=round(statistics.mean(ff), 0) if ff else None,
                               first_funded_p25_p75=[float(np.percentile(ff, 25)), float(np.percentile(ff, 75))] if ff else None,
                               attempts_to_first_funded_mean=round(statistics.mean(s['buys_to_first_funded'] for s in S if s['buys_to_first_funded']), 2) if ff else None,
                               payout_within={w: round(100 * sum(1 for x in fp if x <= w) / nf, 1) for w in (60, 90, 180, 365)})
                out[ev].update(refunds_mean=round(float(np.mean([s['refunds'] for s in S])), 0), fees_to_first_funded_mean=round(float(np.mean([s['buys_to_first_funded'] * T['fee'] for s in S if s['buys_to_first_funded']])), 0),
                               attempts_to_first_funded_p90=float(np.percentile([s['buys_to_first_funded'] for s in S if s['buys_to_first_funded']], 90)), never_funded=round(100 * (1 - len(ff) / nf), 1),
                               one_attempt_share=round(100 * sum(1 for s in S if s['buys_to_first_funded'] == 1) / nf, 1))
                if ev == 'mc':
                    np.save(H / f'mc_{k}{TAG}.npy', M)
                    np.save(H / f'mcff_{k}{TAG}.npy', np.array([[s['first_funded_day'] if s['first_funded_day'] is not None else 99999, s['first_payout_day'] if s['first_payout_day'] is not None else 99999] for s in S]))
            res[k] = out; print(k, out['mc'], flush=True)
    (H / f'TYPES{TAG}.json').write_text(json.dumps(res, indent=1), encoding='utf-8')


CAPS = dict(FTMO=400e3, FP=400e3, T5=100e3, FN=100e3)
GOAL = 1e4


def stats(tot, c, R, rk):
    avg = tot.mean(1); fees = sum(k * R[f'{n}@{rk}']['mc']['fees_mean'] for n, k in c.items())
    return dict(combo={n: k for n, k in c.items() if k}, capital=sum(k * TYPES[n]['size'] for n, k in c.items()), monthly_mean=round(float(avg.mean()), 0),
                monthly_median=round(float(np.median(avg)), 0), monthly_p10=round(float(np.percentile(avg, 10)), 0), p_avg_goal=round(float((avg >= GOAL).mean() * 100), 1),
                months_ge_goal=round(float((tot >= GOAL).mean() * 100), 1), months_le_0=round(float((tot <= 0).mean() * 100), 1),
                first_year_month_mean=round(float(tot[:, :12].mean()), 0), years_2_3_month_mean=round(float(tot[:, 12:].mean()), 0),
                worst_3m_p50=round(float(np.median(np.min(np.stack([tot[:, i:i + 3].sum(1) for i in range(12, NM - 2)], 1), 1)) / 3), 0), fees_36m=round(fees, 0),
                buys_36m=round(sum(k * R[f'{n}@{rk}']['mc']['buys_mean'] for n, k in c.items()), 1))


def combos():
    R = json.loads((H / f'TYPES{TAG}.json').read_text()); res = {}
    names = list(TYPES); choices = [range(0, int(CAPS[TYPES[n]['cap']] // TYPES[n]['size']) + 1) for n in names]
    for f in (0.005, 0.0075, 0.01):
        rk = f'{f * 100:g}'; M = {n: np.load(H / f'mc_{n}@{rk}{TAG}.npy') for n in names}; ok = []
        for cnt in product(*choices):
            c = dict(zip(names, cnt)); alloc = {}
            for n, k in c.items(): alloc[TYPES[n]['cap']] = alloc.get(TYPES[n]['cap'], 0) + k * TYPES[n]['size']
            if sum(cnt) == 0 or any(v > CAPS[g] for g, v in alloc.items()): continue
            tot = sum(k * M[n] for n, k in c.items() if k); avg = tot.mean(1)
            if (avg >= GOAL).mean() >= 0.80: ok.append((c, tot))
        ok.sort(key=lambda x: (sum(k * TYPES[n]['size'] for n, k in x[0].items()), -np.percentile(x[1].mean(1), 10)))
        res[rk] = dict(cheapest=[stats(t, c, R, rk) for c, t in ok[:8]], n_ok=len(ok))
        print(rk, res[rk]['n_ok']); [print('  ', x) for x in res[rk]['cheapest'][:4]]
    (H / f'COMBOS{TAG}.json').write_text(json.dumps(res, indent=1), encoding='utf-8')


def evaluate(spec):
    """spec like FTMO_2S=2,FP_STD=2,T5_HS=1@1 -> stats with and without cost stress files present."""
    body, rk = spec.split('@'); c = {a: int(b) for a, b in (x.split('=') for x in body.split(','))}; out = {}
    for tag in ('', '_cost0.05'):
        R = json.loads((H / f'TYPES{tag}.json').read_text()); tot = sum(k * np.load(H / f'mc_{n}@{rk}{tag}.npy') for n, k in c.items())
        out[tag or 'base'] = stats(tot, c, R, rk)
    return out


if __name__ == '__main__':
    (lambda: print(json.dumps(evaluate(sys.argv[2]), indent=1))) () if sys.argv[1] == 'eval' else {'days': build_days, 'run': run, 'combos': combos}[sys.argv[1]]()
