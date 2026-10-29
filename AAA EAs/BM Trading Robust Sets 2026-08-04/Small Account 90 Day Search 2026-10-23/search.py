"""Small Account 90 Day Search (PLAN.md). Python + numba replay of frozen native ledgers; no MT5.

python search.py dev | validate | oos | final | table
"""
import json, math, random, statistics, sys, time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import numpy as np
from numba import njit, prange

R = Path(__file__).resolve().parent; B = R.parent
SPLIT = json.loads((R / 'SPLIT.json').read_text(encoding='utf-8'))
SPECS = json.loads((B / 'Small Account Challenge 2026-10-23/SPECS.json').read_text(encoding='utf-8'))['symbols']
DAY = 86400.0; START = 100.0; GOAL = 10000.0; BUST = 10.0; H = 90; SEED = 20261023; MC_N = 2000; BLOCK = 28
SEG = {k: (SPLIT[k]['start'], SPLIT[k]['end_exclusive']) for k in ('development', 'validation', 'oos')}
SEG['all'] = (SPLIT['development']['start'], SPLIT['oos']['end_exclusive'])
DI_ON, DI_OFF = 'nasdaq-5m-candle-momentum', 'nasdaq-5m-di-off'
PR9 = ('nasdaq-5m-candle-momentum', 'usdjpy-london-open-momentum', 'us100-h1-orb-13utc', 'xau-rsi-vwap', 'us100-month-end-flow',
       'xau-orb-london-ny-overlap-m30', 'xau-orb-new-york-m30', 'us100-orb-new-york-m30', 'us100-selective-orb-v3')
ORB5 = ('us100-h1-orb-13utc', 'xau-orb-london-ny-overlap-m30', 'xau-orb-new-york-m30', 'us100-orb-new-york-m30', 'us100-selective-orb-v3')
FIXED = (.03, .05, .075, .10, .125, .15, .20, .25, .30, .40, .50, .75, 1.0)  # 50-100%: addendum 1
KELLY_C = (.5, .75, 1., 1.5, 2., 3.)
DEADLINE = [(k, lo, hi) for k in (1.5, 2., 3., 4., 6.) for lo in (.02, .05) for hi in (.20, .30, .50)]
CAPS = (math.inf, .30, .60)
GREEDY_POLICIES = [('FIXED', f) for f in FIXED[:10]] + [('DL', k, .05, hi) for k in (2., 3., 4.) for hi in (.30, .50)]
BASELINES = [('PR9', ('FIXED', .05)), ('FTMO17', ('FIXED', .03)), ('FTMO17', ('FIXED', .10)), ('FTMO17', ('FIXED', .20))]


def utc(d): return datetime.combine(date.fromisoformat(d), datetime.min.time(), tzinfo=timezone.utc).timestamp()


def load():
    rows = []
    for c in json.loads((B / 'Portfolio Prop Comparison 2026-10-22/INPUTS-FTMO17.json').read_text(encoding='utf-8'))['candidates']:
        if not c['end_censored']: rows.append((c['op'], c['cl'], c['ea'], c['symbol'], c['unit_risk'], c['unit_gross'] + c['unit_commission'] + c['unit_swap']))
    for c in json.loads((B / 'Best Prop Portfolio Retest 2026-10-20/INPUTS-DI_OFF.json').read_text(encoding='utf-8'))['candidates']:
        if c['ea'] == DI_ON and not c['end_censored']: rows.append((c['op'], c['cl'], DI_OFF, c['symbol'], c['unit_risk'], c['unit_gross'] + c['unit_commission'] + c['unit_swap']))
    rows.sort()
    lanes = sorted({r[2] for r in rows}); li = {n: i for i, n in enumerate(lanes)}
    T = dict(op=np.array([r[0] for r in rows], float), cl=np.array([r[1] for r in rows], float), lane=np.array([li[r[2]] for r in rows], np.int32),
             ur=np.array([r[4] for r in rows], float), un=np.array([r[5] for r in rows], float),
             mn=np.array([SPECS[r[3]]['min'] for r in rows]), st=np.array([SPECS[r[3]]['step'] for r in rows]), mx=np.array([SPECS[r[3]]['max'] for r in rows]))
    return lanes, T


LANES, T = load(); L = len(LANES)
BASKETS0 = {'NAS5M': (DI_ON,), 'PR9': PR9, 'FTMO17': tuple(n for n in LANES if n != DI_OFF),
            'FTMO17-DIOFF': tuple(n for n in LANES if n != DI_ON), 'ORB5': ORB5, 'RSI_VWAP': ('xau-rsi-vwap',)}  # RSI_VWAP: addendum 1


def lane_stats(seg):
    a, b = (utc(x) for x in SEG[seg]); days = (b - a) / DAY; out = {}
    for i, n in enumerate(LANES):
        m = (T['lane'] == i) & (T['op'] >= a) & (T['op'] < b); r = T['un'][m] / T['ur'][m]
        if not len(r): out[n] = dict(trades=0); continue
        mu = float(r.mean()); m2 = float((r * r).mean()); k = mu / m2 if mu > 0 else 0.
        out[n] = dict(trades=int(len(r)), per_month=round(len(r) / days * 30.4375, 2), per_day=round(len(r) / days, 3), mean_r=round(mu, 4),
                      win=round(float((r > 0).mean()), 4), kelly=round(k, 4), score=round(len(r) / days * mu * k / 2, 6))
    return out


# ---------------------------------------------------------------- paths -> sorted event arrays (config independent)
def build(paths):
    """paths: list of (t0, trade_idx array, shift array). Returns flat event arrays; closes sort before opens at equal time."""
    ev_ptr = [0]; occ_ptr = [0]; times, kinds, occs, otr = [], [], [], []
    for t0, idx, sh in paths:
        n = len(idx); o = T['op'][idx] + sh; c = T['cl'][idx] + sh
        t = np.concatenate([o, c]); k = np.concatenate([np.ones(n, np.int8), np.zeros(n, np.int8)]); j = np.concatenate([np.arange(n), np.arange(n)])
        order = np.lexsort((k, t)); times.append(t[order]); kinds.append(k[order]); occs.append(j[order].astype(np.int32)); otr.append(idx.astype(np.int32))
        ev_ptr.append(ev_ptr[-1] + 2 * n); occ_ptr.append(occ_ptr[-1] + n)
    cat = lambda v, dt: np.concatenate(v).astype(dt) if v else np.zeros(0, dt)  # noqa: E731
    return dict(ev_ptr=np.array(ev_ptr, np.int64), t=cat(times, float), kind=cat(kinds, np.int8), occ=cat(occs, np.int32),
                occ_ptr=np.array(occ_ptr, np.int64), otr=cat(otr, np.int32), t0=np.array([p[0] for p in paths], float))


def hist_paths(seg, horizon=H):
    a, b = SEG[seg]; d = date.fromisoformat(a); end = date.fromisoformat(b); out = []
    while d + timedelta(days=horizon) <= end:
        if d.weekday() < 5:
            t0 = utc(d.isoformat()); lo, hi = np.searchsorted(T['op'], [t0, t0 + horizon * DAY])
            out.append((t0, np.arange(lo, hi), np.zeros(hi - lo)))
        d += timedelta(days=1)
    return out


def mc_paths(seg, n=MC_N, horizon=H, seed=SEED):
    a, b = SEG[seg]; m = date.fromisoformat(a); end = date.fromisoformat(b)
    while m.weekday() != 0: m += timedelta(days=1)
    mondays = []
    while m + timedelta(days=BLOCK) <= end: mondays.append(m); m += timedelta(days=7)
    idx = {m: np.searchsorted(T['op'], [utc(m.isoformat()), utc(m.isoformat()) + BLOCK * DAY]) for m in mondays}
    rng = random.Random(seed); t0 = utc('2030-01-07'); out = []
    for _ in range(n):
        ids, shs = [], []
        for k in range(math.ceil(horizon / BLOCK)):
            src = mondays[rng.randrange(len(mondays))]; lo, hi = idx[src]
            ids.append(np.arange(lo, hi)); shs.append(np.full(hi - lo, t0 + k * BLOCK * DAY - utc(src.isoformat())))
        out.append((t0, np.concatenate(ids), np.concatenate(shs)))
    return out


# ---------------------------------------------------------------- kernel
@njit(parallel=True)
def kernel(ev_ptr, et, ek, eo, occ_ptr, otr, t0s, lane, ur, un, mn, st, mx, on, lane_f, ptype, f_fixed, kk, fmin, fmax, cap, horizon, reloads, out):
    P = len(t0s); nl = len(on)
    for p in prange(P):
        t0 = t0s[p]; o0 = occ_ptr[p]; noc = occ_ptr[p + 1] - o0
        lots = np.zeros(noc); busy = np.zeros(nl, np.bool_)
        bal = START; dep = START; left = reloads; busts = 0; open_risk = 0.0; peak = bal; mdd = 0.0
        t1 = -1.0; t5 = -1.0; t10 = -1.0; tb = -1.0; taken = 0; closed = 0; skipped = 0; over = 0.0
        for e in range(ev_ptr[p], ev_ptr[p + 1]):
            day = (et[e] - t0) / 86400.0
            if day >= horizon: break
            j = eo[e]; tr = otr[o0 + j]; ln = lane[tr]
            if ek[e] == 0:
                if lots[j] <= 0.0: continue
                bal = max(np.round(bal + lots[j] * un[tr], 2), 0.0); open_risk -= lots[j] * ur[tr]; busy[ln] = False; lots[j] = 0.0; closed += 1
                if bal > peak: peak = bal
                if peak > 0 and (peak - bal) / peak > mdd: mdd = (peak - bal) / peak
                if t1 < 0 and bal >= 1000.0: t1 = day
                if t5 < 0 and bal >= 5000.0: t5 = day
                if t10 < 0 and bal >= GOAL: t10 = day
                if bal < BUST:
                    if tb < 0: tb = day
                    busts += 1
                    if left > 0:
                        left -= 1; bal += START; dep += START; peak = bal
                    else:
                        break
            else:
                if not on[ln] or busy[ln]: continue
                if ptype == 0: f = f_fixed
                elif ptype == 1: f = lane_f[ln]
                else:
                    rem = max(horizon - day, 1.0)
                    f = fmin if bal >= GOAL else min(max(kk * math.log(GOAL / bal) / rem, fmin), fmax)
                if f <= 0.0: continue
                budget = f * bal; u = ur[tr]
                x = math.floor(budget / u / st[tr] + 1e-9) * st[tr]
                if x < mn[tr] - 1e-9:
                    if mn[tr] * u <= 3.0 * budget + 1e-9: x = mn[tr]
                    else:
                        skipped += 1; continue
                x = min(x, mx[tr])
                if cap < 1e9:
                    room = cap * bal - open_risk
                    if x * u > room:
                        x = math.floor(max(room, 0.0) / u / st[tr] + 1e-9) * st[tr]
                        if x < mn[tr] - 1e-9:
                            skipped += 1; continue
                lots[j] = x; busy[ln] = True; open_risk += x * u; taken += 1
                if bal > 0 and open_risk / bal > over: over = open_risk / bal
        out[p, 0] = t1; out[p, 1] = t5; out[p, 2] = t10; out[p, 3] = tb; out[p, 4] = bal; out[p, 5] = dep
        out[p, 6] = taken; out[p, 7] = skipped; out[p, 8] = mdd; out[p, 9] = over; out[p, 10] = busts; out[p, 11] = closed


def policy_args(pol, kelly):
    lf = np.zeros(L)
    if pol[0] == 'FIXED': return 0, pol[1], 0., 0., 0., lf
    if pol[0] == 'KELLY':
        for i, n in enumerate(LANES): lf[i] = min(pol[1] * kelly.get(n, 0.), .40)
        return 1, 0., 0., 0., 0., lf
    return 2, 0., pol[1], pol[2], pol[3], lf


def simulate(ev, basket, pol, cap, kelly, horizon=H, reloads=0, un=None):
    on = np.array([n in basket for n in LANES]); pt, ff, kk, lo, hi, lf = policy_args(pol, kelly)
    out = np.zeros((len(ev['t0']), 12))
    kernel(ev['ev_ptr'], ev['t'], ev['kind'], ev['occ'], ev['occ_ptr'], ev['otr'], ev['t0'], T['lane'], T['ur'], T['un'] if un is None else un, T['mn'], T['st'], T['mx'],
           on, lf, pt, ff, kk, lo, hi, cap if math.isfinite(cap) else 1e18, float(horizon), reloads, out)
    return out


def summary(o, horizon=H):
    n = len(o); hit = o[:, 2] >= 0; med = lambda v: round(float(np.median(v)), 1) if len(v) else None  # noqa: E731
    alive = o[:, 3] < 0; months = horizon / 30.4375
    return dict(n=n, p10k=round(float(hit.mean()), 4), p5k=round(float((o[:, 1] >= 0).mean()), 4), p1k=round(float((o[:, 0] >= 0).mean()), 4),
                bust=round(float((o[:, 3] >= 0).mean()), 4), days_10k_median=med(o[hit, 2]), days_bust_median=med(o[o[:, 3] >= 0, 3]),
                bal_end_median=round(float(np.median(o[:, 4])), 2), ended_below_100=round(float((o[:, 4] < START).mean()), 4),
                maxdd_median=round(float(np.median(o[:, 8])), 4), max_open_risk_median=round(float(np.median(o[:, 9])), 3),
                trades_per_month=round(float(np.median(o[alive, 6])) / months, 2) if alive.any() else round(float(np.median(o[:, 6])) / months, 2),
                trades_per_day=round((float(np.median(o[alive, 6])) if alive.any() else float(np.median(o[:, 6]))) / horizon, 3),
                skipped_median=float(np.median(o[:, 7])), deposits_mean=round(float(o[:, 5].mean()), 2),
                deposit_per_success=round(float(o[:, 5].mean()) / float(hit.mean()), 2) if hit.any() else None)


def pname(p):
    if p[0] == 'FIXED': return f'FIXED {100 * p[1]:g}%'
    if p[0] == 'KELLY': return f'KELLY x{p[1]:g}'
    return f'DEADLINE k{p[1]:g} {100 * p[2]:g}-{100 * p[3]:g}%'


def cname(c): return 'none' if not math.isfinite(c) else f'{100 * c:g}%'


def save(name, obj): (R / name).write_text(json.dumps(obj, indent=1, allow_nan=False), encoding='utf-8')


def load_json(name): return json.loads((R / name).read_text(encoding='utf-8'))


def all_policies(): return [('FIXED', f) for f in FIXED] + [('KELLY', c) for c in KELLY_C] + [('DL',) + x for x in DEADLINE]


def key(basket, pol, cap): return json.dumps([sorted(basket), list(pol), cname(cap)])


# ---------------------------------------------------------------- stages
def dev():
    began = time.time(); stats = lane_stats('development'); kelly = {n: s.get('kelly', 0.) for n, s in stats.items()}
    evm = build(mc_paths('development')); evh = build(hist_paths('development'))
    print('dev paths: MC', len(evm['t0']), 'history', len(evh['t0']), f'{time.time() - began:.0f}s', flush=True)
    simulate(evm, BASKETS0['PR9'], ('FIXED', .05), math.inf, kelly)  # compile
    baskets = dict(BASKETS0)
    ranked = [n for n, s in sorted(stats.items(), key=lambda x: -x[1].get('score', 0)) if s.get('score', 0) > 0]
    top = []
    for n in ranked:
        if (n == DI_ON and DI_OFF in top) or (n == DI_OFF and DI_ON in top): continue
        top.append(n)
    for k in (1, 2, 3, 4, 5, 6, 8, 10, 12, 15):
        if k <= len(top): baskets[f'TOP{k}'] = tuple(top[:k])
    # greedy forward selection
    chosen, best_prev, steps = [], 0., []
    while len(chosen) < 12:
        cands = []
        for n in LANES:
            if n in chosen or (n == DI_ON and DI_OFF in chosen) or (n == DI_OFF and DI_ON in chosen): continue
            b = tuple(chosen + [n]); best = max((summary(simulate(evm, b, p, math.inf, kelly))['p10k'], -i) for i, p in enumerate(GREEDY_POLICIES))
            cands.append((best[0], n, GREEDY_POLICIES[-best[1]]))
        p10, n, pol = max(cands, key=lambda x: (x[0], x[1]))
        if chosen and p10 - best_prev < .0025: break
        chosen.append(n); best_prev = p10; steps.append(dict(lanes=list(chosen), p10k=p10, policy=pname(pol)))
        baskets[f'GREEDY{len(chosen)}'] = tuple(chosen); print('greedy', len(chosen), n, p10, pname(pol), f'{time.time() - began:.0f}s', flush=True)
    rows = []
    for bn, b in baskets.items():
        for pol in all_policies():
            for cap in CAPS:
                m = summary(simulate(evm, b, pol, cap, kelly)); h = summary(simulate(evh, b, pol, cap, kelly))
                rows.append(dict(basket=bn, lanes=list(b), policy=list(pol), policy_name=pname(pol), cap=cname(cap), mc=m, hist=h))
        print('grid', bn, len(rows), f'{time.time() - began:.0f}s', flush=True)
    rows.sort(key=lambda r: (-r['mc']['p10k'], r['mc']['bust'], -r['mc']['p5k']))
    seen, top20 = set(), []
    for r in rows:
        k = key(r['lanes'], r['policy'], math.inf if r['cap'] == 'none' else float(r['cap'][:-1]) / 100)
        if k in seen: continue
        seen.add(k); top20.append(r)
        if len(top20) == 20: break
    rsi = next(r for r in rows if r['basket'] == 'RSI_VWAP')
    save('DEV.json', dict(split=SPLIT, lane_stats=stats, top_ranked=top, greedy=steps, baskets={k: list(v) for k, v in baskets.items()}, configs=len(rows), top20=top20, rsi_vwap_best=rsi, rows=rows))
    print('DEV done', len(rows), 'configs', f'{time.time() - began:.0f}s')


def cap_of(r): return math.inf if r['cap'] == 'none' else float(r['cap'][:-1]) / 100


def baseline_rows():
    return [dict(basket=b, lanes=list(BASKETS0[b]), policy=list(p), policy_name=pname(p), cap='none') for b, p in BASELINES]


def evaluate(seg, rows, kelly, n=MC_N, horizon=H):
    evm = build(mc_paths(seg, n=n, horizon=horizon)); evh = build(hist_paths(seg, horizon=horizon)); out = []
    for r in rows:
        pol = tuple(r['policy'])
        out.append(dict(basket=r['basket'], lanes=r['lanes'], policy=r['policy'], policy_name=r['policy_name'], cap=r['cap'],
                        mc=summary(simulate(evm, r['lanes'], pol, cap_of(r), kelly, horizon), horizon),
                        hist=summary(simulate(evh, r['lanes'], pol, cap_of(r), kelly, horizon), horizon) if len(evh['t0']) else None))
    return out


def validate():
    d = load_json('DEV.json'); kelly = {n: s.get('kelly', 0.) for n, s in d['lane_stats'].items()}
    val = evaluate('validation', d['top20'] + baseline_rows() + [d['rsi_vwap_best']], kelly)
    for i, r in enumerate(val[:20]): r['dev_rank'] = i + 1
    chosen = max(val[:20], key=lambda r: (r['mc']['p10k'], -r['dev_rank']))
    save('VALIDATION.json', dict(rows=val, chosen=chosen)); print('chosen', chosen['basket'], chosen['policy_name'], chosen['cap'], chosen['mc']['p10k'])


def oos():
    d = load_json('DEV.json'); v = load_json('VALIDATION.json'); kelly = {n: s.get('kelly', 0.) for n, s in d['lane_stats'].items()}
    assert not (R / 'OOS.json').exists(), 'OOS already run once; do not rerun'
    rows = [dict(v['chosen'], role='chosen'), dict(d['top20'][0], role='development #1')] + [dict(r, role='baseline') for r in baseline_rows()] + [dict(d['rsi_vwap_best'], role='owner comparison: RSI VWAP alone')]
    res = evaluate('oos', rows, kelly)
    for a, b in zip(res, rows): a['role'] = b['role']
    save('OOS.json', dict(rows=res, lane_stats_validation=lane_stats('validation'), lane_stats_oos=lane_stats('oos')))
    for r in res: print(r['role'], r['basket'], r['policy_name'], r['cap'], 'MC', r['mc']['p10k'], 'hist', r['hist']['p10k'])


def final():
    d = load_json('DEV.json'); v = load_json('VALIDATION.json'); kelly = {n: s.get('kelly', 0.) for n, s in d['lane_stats'].items()}
    targets = [dict(v['chosen'], role='chosen'), dict(d['top20'][0], role='development #1'), dict(d['rsi_vwap_best'], role='owner comparison: RSI VWAP alone')]
    targets += [dict(r, role='baseline (added after OOS, reporting only)') for r in baseline_rows() if r['basket'] == 'FTMO17' and r['policy'][1] >= .10]
    stress = T['un'] - .05 * T['ur']; stress = np.where(stress > 0, stress * .9, stress); out = []
    for horizon in (90, 180, 365):
        evm = build(mc_paths('all', n=5000, horizon=horizon)); evh = build(hist_paths('all', horizon=horizon))
        for r in targets:
            b, pol, cap = r['lanes'], tuple(r['policy']), cap_of(r)
            row = dict(role=r['role'], basket=r['basket'], policy_name=r['policy_name'], cap=r['cap'], horizon=horizon,
                       mc=summary(simulate(evm, b, pol, cap, kelly, horizon), horizon), hist=summary(simulate(evh, b, pol, cap, kelly, horizon), horizon),
                       stress_mc=summary(simulate(evm, b, pol, cap, kelly, horizon, un=stress), horizon))
            if horizon == 90:
                row['reloads'] = {str(k): summary(simulate(evm, b, pol, cap, kelly, horizon, reloads=k), horizon) for k in (0, 1, 2, 4, 9)}
            out.append(row); print(r['role'], horizon, row['mc']['p10k'], row['hist']['p10k'], row['stress_mc']['p10k'], flush=True)
    save('FINAL.json', dict(rows=out))


def table():
    pct = lambda v: '-' if v is None else f'{100 * v:.1f}%'; usd = lambda v: '-' if v is None else f'${v:,.0f}'  # noqa: E731
    d = load_json('DEV.json'); out = ['# Small Account 90 Day Search — results (generated by `search.py table`)', '',
                                      f"Split: development {SEG['development'][0]} → {SEG['development'][1]}, validation {SEG['validation'][0]} → {SEG['validation'][1]}, "
                                      f"OOS {SEG['oos'][0]} → {SEG['oos'][1]} (end exclusive). {d['configs']} development configurations. Start $100, goal $10,000, bust < $10.", '']
    head = '| P($10k ≤ 90 d) MC / hist | P($5k) MC / hist | P($1k) MC | Bust MC / hist | Median days to $10k (MC) | Median end balance MC / hist | Trades / month | / day |'

    def cells(r):
        m, h = r['mc'], r['hist'] or {}
        return (f"{pct(m['p10k'])} / {pct(h.get('p10k'))} | {pct(m['p5k'])} / {pct(h.get('p5k'))} | {pct(m['p1k'])} | "
                f"{pct(m['bust'])} / {pct(h.get('bust'))} | {m['days_10k_median'] or '-'} | {usd(m['bal_end_median'])} / {usd(h.get('bal_end_median'))} | "
                f"{m['trades_per_month']} | {m['trades_per_day']} |")
    out += ['## Lanes (development statistics; ranking input for TOP-k)', '', '| Lane | Trades | / month | / day | Mean net R | Win | Kelly f | Kelly growth / day |', '|---|---:|---:|---:|---:|---:|---:|---:|']
    for n, s in sorted(d['lane_stats'].items(), key=lambda x: -x[1].get('score', 0)):
        if s['trades']: out.append(f"| {n} | {s['trades']} | {s['per_month']} | {s['per_day']} | {s['mean_r']:+.3f} | {pct(s['win'])} | {s['kelly']:.3f} | {s['score']:.5f} |")
    out += ['', '## Greedy forward selection (development MC)', '', '| Step | Added lane | P($10k ≤ 90 d) | Best policy |', '|---:|---|---:|---|']
    for i, g in enumerate(d['greedy']): out.append(f"| {i + 1} | {g['lanes'][-1]} | {pct(g['p10k'])} | {g['policy']} |")
    out += ['', '## Development top 20 (ranked by MC P($10k ≤ 90 d))', '', '| # | Basket | Policy | Open-risk cap ' + head, '|---:|---|---|---|' + '---:|' * 8]
    for i, r in enumerate(d['top20']): out.append(f"| {i + 1} | {r['basket']} | {r['policy_name']} | {r['cap']} | " + cells(r))
    out += ['', '## Best development row per declared basket', '', '| Basket | Policy | Cap ' + head, '|---|---|---|' + '---:|' * 8]
    for bn in BASKETS0:
        r = next(x for x in d['rows'] if x['basket'] == bn); out.append(f"| {bn} | {r['policy_name']} | {r['cap']} | " + cells(r))
    out += ['', '## RSI VWAP alone (owner request), development, fixed risk, no cap', '', '| Policy ' + head, '|---|' + '---:|' * 8]
    for r in sorted((x for x in d['rows'] if x['basket'] == 'RSI_VWAP' and x['policy'][0] == 'FIXED' and x['cap'] == 'none'), key=lambda x: x['policy'][1]):
        out.append(f"| {r['policy_name']} | " + cells(r))
    if (R / 'VALIDATION.json').exists():
        v = load_json('VALIDATION.json'); out += ['', '## Validation', '', f"Chosen: **{v['chosen']['basket']} · {v['chosen']['policy_name']} · cap {v['chosen']['cap']}**", '',
                                                  '| Dev rank | Basket | Policy | Cap ' + head, '|---|---|---|---|' + '---:|' * 8]
        for r in v['rows']: out.append(f"| {r.get('dev_rank', 'baseline/comparison')} | {r['basket']} | {r['policy_name']} | {r['cap']} | " + cells(r))
    if (R / 'OOS.json').exists():
        o = load_json('OOS.json'); out += ['', '## OOS (run once)', '', '| Role | Basket | Policy | Cap ' + head, '|---|---|---|---|' + '---:|' * 8]
        for r in o['rows']: out.append(f"| {r['role']} | {r['basket']} | {r['policy_name']} | {r['cap']} | " + cells(r))
        out += ['', '### Lane statistics by segment (reporting only)', '', '| Lane | Dev mean R | Val mean R | OOS mean R | OOS trades / month |', '|---|---:|---:|---:|---:|']
        for n in d['lane_stats']:
            a, b, c = d['lane_stats'][n], o['lane_stats_validation'][n], o['lane_stats_oos'][n]
            out.append(f"| {n} | {a.get('mean_r', 0):+.3f} | {b.get('mean_r', 0):+.3f} | {c.get('mean_r', 0):+.3f} | {c.get('per_month', 0)} |")
    if (R / 'FINAL.json').exists():
        f = load_json('FINAL.json'); out += ['', '## Mandatory Monte Carlo (all-period blocks, 5,000 paths) + all-period history + stress', '',
                                             '| Role | Config | Horizon | P($10k) MC / hist / stress | P($5k) MC | Bust MC / hist / stress | Median days to $10k | Median end balance | Trades / month | / day |',
                                             '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
        for r in f['rows']:
            m, h, s = r['mc'], r['hist'], r['stress_mc']
            out.append(f"| {r['role']} | {r['basket']} · {r['policy_name']} · cap {r['cap']} | {r['horizon']} d | {pct(m['p10k'])} / {pct(h['p10k'])} / {pct(s['p10k'])} | {pct(m['p5k'])} | "
                       f"{pct(m['bust'])} / {pct(h['bust'])} / {pct(s['bust'])} | {m['days_10k_median'] or '-'} | {usd(m['bal_end_median'])} | {m['trades_per_month']} | {m['trades_per_day']} |")
        out += ['', '### Reloads within 90 days (re-deposit $100 after each bust; all-period MC)', '', '| Role | Config | Max reloads | P($10k ≤ 90 d) | Mean money deposited | Deposited per success |', '|---|---|---:|---:|---:|---:|']
        for r in f['rows']:
            for k, s in r.get('reloads', {}).items(): out.append(f"| {r['role']} | {r['basket']} · {r['policy_name']} | {k} | {pct(s['p10k'])} | {usd(s['deposits_mean'])} | {usd(s['deposit_per_success'])} |")
    (R / 'RESULTS.md').write_text('\n'.join(out) + '\n', encoding='utf-8'); print('RESULTS.md')


if __name__ == '__main__':
    dict(dev=dev, validate=validate, oos=oos, final=final, table=table)[sys.argv[1]]()
