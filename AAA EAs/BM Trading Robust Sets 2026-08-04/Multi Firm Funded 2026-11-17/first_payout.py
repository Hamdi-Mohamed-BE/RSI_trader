"""Owner 2026-11-18: "expected first min invest ... pass rate from first try ... which account to start with ... expected first payout in $ ... days".
Same frozen engine as sim.py (account() copied, plus: first payout amount, cash spent on fees before the first payout, first-try result).
Stream = recommended Best 1-Step list (VARIANT _N75: B9 + Asia Breakout, Nasdaq 5M x0.75). $100k accounts, MC 1,000 x 28-day blocks + history starts.
VARIANT=_N75 python first_payout.py -> FIRST_PAYOUT_N75.json. In-sample, hindsight-selected list, no news closes simulated."""
import json, os, statistics
import numpy as np

os.environ.setdefault('VARIANT', '_N75')
import sim

H = sim.H; VAR = sim.VAR


def account(rows, T, f):
    st = dict(buys=0, first_payout_day=None, first_payout=None, fees_before_payout=0.0, first_try=None, first_funded_day=None)
    state = 'buy'; size = T['size']
    for d, (dc, fl0, mn, fl1, ntr) in enumerate(rows):
        if state == 'buy':
            st['buys'] += 1
            if st['first_payout_day'] is None: st['fees_before_payout'] += T['fee']
            state = 'ch'; ph = 0; b = hwm = 1.0; nd = npd = 0; dp = []; refund_due = T['refund']
        if state == 'wait':
            if d < ready: continue
            state = 'fund'; b = hwm = 1.0; dp = []; next_pay = d + T['first']
            if st['first_funded_day'] is None: st['first_funded_day'] = d
        eq0 = b + f * fl0; anchor = b if T['dbasis'] == 'bal' else max(b, eq0)
        floor = (1 - T['ml']) if T['mk'] == 'static' else min(hwm - T['ml'], 1.0)
        mineq = b + f * mn
        if mineq <= floor + 1e-12 or anchor - mineq >= T['daily'] - 1e-12:
            if state == 'ch' and st['first_try'] is None: st['first_try'] = 'fail'
            state = 'buy'; continue
        b += f * dc; hwm = max(hwm, b); dp.append(f * dc)
        if ntr: nd += 1 if state == 'ch' else 0
        if state == 'ch':
            if f * dc >= 0.005: npd += 1
            tgt, mind, minp = T['phases'][ph]; prof = b - 1
            ok_best = T['best'] is None or (prof > 0 and max(dp) <= T['best'] * prof + 1e-12)
            if prof >= tgt - 1e-12 and nd >= mind and npd >= minp and ok_best:
                ph += 1; b = hwm = 1.0; nd = npd = 0; dp = []
                if ph == len(T['phases']):
                    state = 'wait'; ready = d + 4
                    if st['first_try'] is None: st['first_try'] = 'pass'
        elif d >= next_pay:
            prof = b - 1; ok_best = T['best'] is None or max(dp) <= T['best'] * prof + 1e-12
            if prof > 0 and prof >= T['minpay'] and ok_best:
                if st['first_payout_day'] is None: st['first_payout_day'] = d; st['first_payout'] = T['split'] * prof * size + refund_due
                refund_due = 0; b = hwm = 1.0; dp = []; next_pay = d + T['cycle']
        if st['first_payout_day'] is not None: break
    return st


def summ(S, T):
    n = len(S); fp = [s for s in S if s['first_payout_day'] is not None]
    pays = [s['first_payout'] for s in fp]; days = [s['first_payout_day'] for s in fp]; spent = [s['fees_before_payout'] for s in fp]
    q = lambda v, p: round(float(np.percentile(v, p)), 0) if v else None
    return dict(n=n, fee=round(T['fee'], 0), first_try_pass=round(100 * sum(s['first_try'] == 'pass' for s in S) / n, 1),
                first_try_unfinished=round(100 * sum(s['first_try'] is None for s in S) / n, 1),
                paid_within_3y=round(100 * len(fp) / n, 1), first_payout_median=q(pays, 50), first_payout_p25=q(pays, 25), first_payout_p75=q(pays, 75),
                first_payout_day_median=q(days, 50), first_payout_day_p25=q(days, 25), first_payout_day_p75=q(days, 75),
                funded_day_median=q([s['first_funded_day'] for s in S if s['first_funded_day'] is not None], 50),
                fees_before_first_payout_median=q(spent, 50), fees_before_first_payout_p90=q(spent, 90),
                one_fee_only=round(100 * sum(1 for s in fp if s['buys'] == 1) / n, 1),
                paid_within={w: round(100 * sum(1 for x in days if x <= w) / n, 1) for w in (60, 90, 120, 180)})


def main():
    D = json.loads((H / f'DAYS{VAR}.json').read_text()); rows = [tuple(r) for r in D['rows']]; paths = sim.mc_paths(rows)
    hist = [rows[s:s + sim.HORIZON] for s in range(0, len(rows) - sim.HORIZON + 1, 14)]
    out = {}
    for name in ('FTMO_1S', 'FTMO_2S', 'FP_STD', 'T5_HS'):
        T = sim.TYPES[name]
        for f in (0.005, 0.0075):
            k = f'{name}@{f * 100:g}'
            out[k] = dict(mc=summ([account(p, T, f) for p in paths], T), hist=summ([account(p, T, f) for p in hist], T))
            print(k, out[k]['mc'], flush=True)
    (H / f'FIRST_PAYOUT{VAR}.json').write_text(json.dumps(out, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
