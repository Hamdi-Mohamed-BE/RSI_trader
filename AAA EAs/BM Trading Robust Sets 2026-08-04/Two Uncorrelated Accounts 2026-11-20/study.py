"""Owner 2026-11-20: "two uncorrelated profiles from the Best 1-Step profile, so when we buy 2 accounts it's almost 100% one of them passes; can it be faster,
aim for 1 month". Plan frozen before results (this docstring):

Data: Multi Firm Funded 2026-11-17/INPUTS_N75.json = the recommended Best 1-Step list (B9 + Asia Breakout, Nasdaq 5M P&L x0.75, weekend / holiday flat applied),
3,499 trades 2021-10-07 -> 2026-10-06 with 5-minute marks. Day rows rebuilt per EA group exactly like sim.py build_days (Prague days; closed change, start
floating, intraday minimum equity incl. open trades).
Account: FTMO 1-Step $100k-normalised rules of sim.py TYPES['FTMO_1S']: +10% target, best day <= 50% of profit, daily 3% from the Prague-midnight balance
(intraday minimum equity), 10% max loss trailing the end-of-day balance (locked at initial). First attempt only; outcome = day of pass / breach / still running.
Candidates:
  FULL_1      one account, full profile, risk r                     (today's plan)
  FULL_2RISK  two accounts, full profile, risks r1 <= r2            (same trades -> highly correlated)
  SPLIT       two accounts, EA groups A / B (every 2-way split of the 10 EAs, >= 2 EAs each), risks rA, rB
  SPLIT_SYM   SPLIT restricted to splits where no symbol is traded by both accounts (FTMO: no opposite trades across accounts)
Risk grid per account: 0.75, 1.0, 1.25, 1.5, 2.0 %. Objective: P(at least one account passes within 30 days).
Selection on DEV starts only (every weekday 2021-10-07 -> 2024-10-07, minus 60 days room); reported on TEST starts (2024-10-07 -> 2026-08-07, never used
for choosing) and on Monte Carlo (2,000 paths of 28-day blocks over all 5 years, the SAME block draws for both accounts so their correlation is kept).
Also reported: within 60 days, P(both breach), P(neither passes in 60 days), each account alone, fees ($10k FTMO 1-Step ~ $92 each).
Not modelled: the guard, news closes, $10k lot rounding (~-15% at $10k), commissions beyond the source ledger. In-sample EA list (picked with hindsight).
python study.py -> RESULTS.json + printed tables"""
import itertools, json, sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import numpy as np

H = Path(__file__).resolve().parent; MF = H.parent / 'Multi Firm Funded 2026-11-17'
sys.path.insert(0, str(MF)); import os; os.environ['VARIANT'] = '_N75'; import sim   # noqa: E402 (Prague midnights, TYPES)
RISKS = (0.0075, 0.010, 0.0125, 0.015, 0.020); HZ = 60; SEED = 20261120; PATHS = 2000; BLOCK = 28
DEV_END = date(2024, 10, 7)
NICE = {'nasdaq-5m-candle-momentum': 'NAS', 'overnight-bias-orb': 'ONB', 'usdjpy-london-open-momentum': 'JPY', '3-way-gold': '3WG', 'xau-rsi-vwap': 'RSI',
        'ema3': 'EMA3', 'asia-breakout': 'ASIA', 'uk100-monday-dip': 'UK', 'orb-volume-profile-volume-confirmed': 'ORBVC', 'us100-selective-orb-v3': 'SEL'}


def load():
    D = json.loads((MF / 'INPUTS_N75.json').read_text(encoding='utf-8')); t0, t1 = D['year_begin_epoch'], D['year_end_exclusive_epoch']
    d0 = date.fromisoformat(D['window'][0]); nd = (date.fromisoformat(D['window'][1]) - d0).days
    mids = np.array([sim.prague_midnight(d0 + timedelta(days=i)) for i in range(nd + 1)]); assert mids[0] == t0 and mids[-1] == t1
    ev, info = {}, {}
    for c in D['candidates']:
        ea = c['ea'].split('#')[0]
        if c['cl'] is None: c = dict(c, cl=t1 - 1)
        ur = c['unit_risk']; ec = c['entry_unit_cost']; R = (c['unit_gross'] + c['unit_commission'] + c['unit_swap']) / ur; prev = ec / ur
        e = ev.setdefault(ea, ([], [], [], []))
        e[0].append(c['op']); e[1].append(prev); e[2].append(0.0); e[3].append(0)
        for mk in c['marks']:
            if mk[0] >= c['cl']: break
            v = (mk[1] + ec) / ur; e[0].append(mk[0]); e[1].append(v - prev); e[2].append(0.0); e[3].append(0); prev = v
        e[0].append(c['cl']); e[1].append(R - prev); e[2].append(R); e[3].append(1)
        info.setdefault(ea, []).append((c['symbol'], 1 if c['side'] == 'Long' else -1, c['op'], c['cl']))
    ev = {k: tuple(np.array(x, dtype=float) for x in v) for k, v in ev.items()}
    return ev, info, mids, nd, d0


def rows_for(group, ev, mids, nd):
    """Day rows (dc, fl0, mn) in R for an EA group - same definitions as sim.build_days."""
    T = np.concatenate([ev[g][0] for g in group]); dE = np.concatenate([ev[g][1] for g in group]); dC = np.concatenate([ev[g][2] for g in group])
    o = np.argsort(T, kind='stable'); T, dE, dC = T[o], dE[o], dC[o]; E = np.cumsum(dE); C = np.cumsum(dC)
    di = np.searchsorted(mids, T, 'right') - 1
    starts = np.searchsorted(di, np.arange(nd), 'left'); ends = np.searchsorted(di, np.arange(nd), 'right')
    dc = np.zeros(nd); fl0 = np.zeros(nd); mn = np.zeros(nd); e_prev = c_prev = 0.0
    for d in range(nd):
        j, k = starts[d], ends[d]
        if k > j: m = min(e_prev, float(E[j:k].min())); e1, c1 = float(E[k - 1]), float(C[k - 1])
        else: m, e1, c1 = e_prev, e_prev, c_prev
        dc[d] = c1 - c_prev; fl0[d] = e_prev - c_prev; mn[d] = m - c_prev; e_prev, c_prev = e1, c1
    return dc, mn


def challenge(dc, mn, idx, f):
    """FTMO 1-Step first attempt, vectorised over paths. idx: [paths, HZ] day indices. Returns pass day (1-based) or 0, breach day or 0."""
    P = idx.shape[0]; b = np.ones(P); hwm = np.ones(P); best = np.zeros(P); alive = np.ones(P, bool); pd_ = np.zeros(P, int); bd = np.zeros(P, int)
    for t in range(idx.shape[1]):
        d = idx[:, t]; floor = np.minimum(hwm - 0.10, 1.0); mineq = b + f * mn[d]
        br = alive & ((mineq <= floor + 1e-12) | (b - mineq >= 0.03 - 1e-12)); bd[br] = t + 1; alive &= ~br
        x = f * dc[d]; b = np.where(alive, b + x, b); hwm = np.where(alive, np.maximum(hwm, b), hwm); best = np.where(alive, np.maximum(best, x), best)
        prof = b - 1; ok = alive & (prof >= 0.10 - 1e-12) & (best <= 0.5 * prof + 1e-12); pd_[ok] = t + 1; alive &= ~ok
    return pd_, bd


def summarise(pairs, within=(30, 60)):
    """pairs: list of (pass_day, breach_day) arrays, one per account. Returns stats for 'at least one passes'."""
    out = {}
    for w in within:
        anyp = np.zeros(len(pairs[0][0]), bool)
        for p, _ in pairs: anyp |= (p > 0) & (p <= w)
        out[f'any_pass_{w}'] = round(100 * anyp.mean(), 1)
    allbr = np.ones(len(pairs[0][0]), bool)
    for _, br in pairs: allbr &= br > 0
    out['all_breach_60'] = round(100 * allbr.mean(), 1)
    first = np.full(len(pairs[0][0]), 10**6)
    for p, _ in pairs: first = np.minimum(first, np.where(p > 0, p, 10**6))
    got = first < 10**6; out['median_days_first_pass'] = float(np.median(first[got])) if got.any() else None
    out['each_pass_30'] = [round(100 * ((p > 0) & (p <= 30)).mean(), 1) for p, _ in pairs]
    out['each_breach_60'] = [round(100 * (br > 0).mean(), 1) for _, br in pairs]
    return out


def main():
    ev, info, mids, nd, d0 = load(); eas = sorted(ev)
    days = [d0 + timedelta(days=i) for i in range(nd)]
    wk = [i for i, d in enumerate(days) if d.weekday() < 5 and i + HZ <= nd]
    dev = np.array([i for i in wk if days[i] < DEV_END - timedelta(days=HZ)]); test = np.array([i for i in wk if days[i] >= DEV_END])
    rng = np.random.default_rng(SEED); nb = nd // BLOCK
    # each 28-day block drawn independently; the same draws are used for every account (keeps their real correlation)
    mc = np.concatenate([rng.integers(0, nb, size=(PATHS, HZ // BLOCK + 1))[:, [k]] * BLOCK + np.arange(BLOCK)[None, :] for k in range(HZ // BLOCK + 1)], axis=1)[:, :HZ]
    win = {'dev': dev[:, None] + np.arange(HZ)[None, :], 'test': test[:, None] + np.arange(HZ)[None, :], 'mc': mc}

    # opposite-position overlap across accounts (FTMO forbids opposite trades across accounts): pairwise EA overlap counts
    opp = {}
    for a, b in itertools.combinations(eas, 2):
        n = 0
        for (sa, da, oa, ca) in info[a]:
            for (sb, db, ob, cb) in info[b]:
                if sa == sb and da != db and oa < cb and ob < ca: n += 1
        opp[(a, b)] = opp[(b, a)] = n
    syms = {e: {x[0] for x in info[e]} for e in eas}

    cache = {}
    def outcomes(group):
        key = tuple(sorted(group))
        if key not in cache:
            dc, mn = rows_for(key, ev, mids, nd)
            cache[key] = {r: {w: challenge(dc, mn, idx, r) for w, idx in win.items()} for r in RISKS}
        return cache[key]

    full = outcomes(eas); res = {'eas': [NICE[e] for e in eas], 'dev_starts': len(dev), 'test_starts': len(test), 'mc_paths': PATHS}
    # FULL_1 and FULL_2RISK
    best1 = max(RISKS, key=lambda r: summarise([full[r]['dev']])['any_pass_30'])
    res['FULL_1'] = {f'{r*100:g}%': {w: summarise([full[r][w]]) for w in win} for r in RISKS}; res['FULL_1_pick'] = f'{best1*100:g}%'
    best2 = max(((r1, r2) for r1 in RISKS for r2 in RISKS if r1 <= r2), key=lambda p: summarise([full[p[0]]['dev'], full[p[1]]['dev']])['any_pass_30'])
    res['FULL_2RISK_pick'] = {'risks': [f'{x*100:g}%' for x in best2], **{w: summarise([full[best2[0]][w], full[best2[1]][w]]) for w in win}}
    # SPLITS
    rank = []
    for k in range(2, len(eas) - 1):
        for A in itertools.combinations(eas, k):
            B = tuple(e for e in eas if e not in A)
            if A > B: continue
            oa, ob = outcomes(A), outcomes(B)
            bestp = max(((ra, rb) for ra in RISKS for rb in RISKS), key=lambda p: summarise([oa[p[0]]['dev'], ob[p[1]]['dev']])['any_pass_30'])
            s = summarise([oa[bestp[0]]['dev'], ob[bestp[1]]['dev']])
            hedge = sum(opp[(a, b)] for a in A for b in B); symdis = not (set().union(*[syms[e] for e in A]) & set().union(*[syms[e] for e in B]))
            rank.append((s['any_pass_30'], A, B, bestp, hedge, symdis))
    rank.sort(key=lambda x: -x[0])
    def report(item):
        _, A, B, (ra, rb), hedge, symdis = item; oa, ob = outcomes(A), outcomes(B)
        return dict(A=[NICE[e] for e in A], B=[NICE[e] for e in B], risk_A=f'{ra*100:g}%', risk_B=f'{rb*100:g}%', opposite_overlaps_across_accounts=hedge,
                    symbol_disjoint=symdis, **{w: summarise([oa[ra][w], ob[rb][w]]) for w in win})
    res['SPLIT_top5_dev'] = [report(x) for x in rank[:5]]
    sd = [x for x in rank if x[5]]; res['SPLIT_SYM_top3_dev'] = [report(x) for x in sd[:3]]
    # daily correlation of the chosen split's two groups (closed R per day)
    def corr(A, B):
        a, _ = rows_for(tuple(sorted(A)), ev, mids, nd); b, _ = rows_for(tuple(sorted(B)), ev, mids, nd); m = (a != 0) | (b != 0)
        return round(float(np.corrcoef(a[m], b[m])[0, 1]), 3)
    for key in ('SPLIT_top5_dev', 'SPLIT_SYM_top3_dev'):
        for r in res[key]: r['daily_corr'] = corr([k for k in eas if NICE[k] in r['A']], [k for k in eas if NICE[k] in r['B']])
    (H / 'RESULTS.json').write_text(json.dumps(res, indent=1), encoding='utf-8')
    def line(name, d):
        return f"{name:<44} dev {d['dev']['any_pass_30']:5.1f}/{d['dev']['any_pass_60']:5.1f}  test {d['test']['any_pass_30']:5.1f}/{d['test']['any_pass_60']:5.1f}  MC {d['mc']['any_pass_30']:5.1f}/{d['mc']['any_pass_60']:5.1f}  all-breach MC {d['mc']['all_breach_60']:5.1f}  med {d['mc']['median_days_first_pass']}"
    print('P(at least one passes) within 30 / 60 days, %')
    for r in RISKS: print(line(f'FULL_1 {r*100:g}%', res['FULL_1'][f'{r*100:g}%']))
    print(line('FULL_2RISK ' + '+'.join(res['FULL_2RISK_pick']['risks']), res['FULL_2RISK_pick']))
    for r in res['SPLIT_top5_dev']: print(line(f"SPLIT {'+'.join(r['A'])} {r['risk_A']} | {r['risk_B']}", r), 'corr', r['daily_corr'], 'opp', r['opposite_overlaps_across_accounts'])
    for r in res['SPLIT_SYM_top3_dev']: print(line(f"SYM {'+'.join(r['A'])} {r['risk_A']} | {r['risk_B']}", r), 'corr', r['daily_corr'], 'B=', '+'.join(r['B']))


if __name__ == '__main__':
    main()
