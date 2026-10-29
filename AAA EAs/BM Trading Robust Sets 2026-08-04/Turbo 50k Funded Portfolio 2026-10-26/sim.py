"""Turbo $50k funded portfolio (PLAN.md). Python + numba replay of frozen ledgers; no MT5.

python sim.py select | grid | validate | oos | final | table
"""
import importlib.util, json, math, random, statistics, sys, time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import numpy as np
from numba import njit

R = Path(__file__).resolve().parent; B = R.parent
SRC = B / 'Portfolio Long History All ORB05 2026-10-14/RISK_ROWS.json'
ds = importlib.util.spec_from_file_location('ds', B.parent / 'Calyx Research Pipeline/data_split.py'); D = importlib.util.module_from_spec(ds); ds.loader.exec_module(D)
SPLIT = D.research_split('2021-10-06', '2026-10-05')
SEG = {'dev': (SPLIT['development']['start'], SPLIT['development']['end_exclusive']), 'val': (SPLIT['validation']['start'], SPLIT['validation']['end_exclusive']),
       'oos': (SPLIT['oos']['start'], SPLIT['oos']['end_exclusive']), 'all': ('2021-10-06', '2026-10-05')}
EXCLUDE = {'news-pulse-btc', 'news-pulse-eurusd', 'news-pulse-xag', 'news-pulse-xau', 'us30-hourly-profiles', 'us100-hourly-profiles'}
INITIAL = 50000.0; DAY = 86400.0; BLOCK = 28; SEED = 20261026; MC_N = 1000
RISKS = (0.3, 0.5, 0.6, 0.75, 1.0)
REF = dict(maxopen=2.0, persym=2.0, dstop=2.0, buffer=1.0, taper=0.0)
GRID = [dict(maxopen=o, persym=p, dstop=d, buffer=b, taper=t) for o in (1.0, 1.5, 2.0, 2.5) for p in (1.0, 2.0) for d in (1.0, 1.5, 2.0, 2.5)
        for b in (0.5, 1.0, 1.5) for t in (0.0, 0.10, 0.20)]


def utc_ts(d): return datetime.combine(date.fromisoformat(d) if isinstance(d, str) else d, datetime.min.time(), tzinfo=timezone.utc).timestamp()


def last_sunday(y, m):
    d = date(y, m, 31); return d - timedelta(days=(d.weekday() + 1) % 7)


DST = np.array(sorted(utc_ts(last_sunday(y, m)) + 3600 for y in range(2015, 2045) for m in (3, 10)))


def server_day(t):
    """Broker server day, UTC+2 winter / UTC+3 summer (EU DST)."""
    k = np.searchsorted(DST, t, side='right'); return np.floor((t + np.where(k % 2 == 1, 10800.0, 7200.0)) / DAY).astype(np.int64)


def load():
    raw = json.loads(SRC.read_text(encoding='utf-8'))['full-eas']
    rows = sorted([r for r in raw if r['unit_risk'] > 0 and r['op'] < r['cl'] and r['key'] not in EXCLUDE], key=lambda r: (r['op'], r['cl']))
    keys = sorted({r['key'] for r in rows}); syms = sorted({r['symbol'] for r in rows})
    A = dict(op=np.array([r['op'] for r in rows]), cl=np.array([r['cl'] for r in rows]), lane=np.array([keys.index(r['key']) for r in rows], np.int64),
             sym=np.array([syms.index(r['symbol']) for r in rows], np.int64), ur=np.array([r['unit_risk'] for r in rows]),
             un=np.array([r['unit_gross'] + r['unit_comm'] + r['unit_swap'] for r in rows]), w=np.array([r.get('risk_weight', 1.) for r in rows]))
    return A, keys, syms


A, KEYS, SYMS = load(); NL, NS = len(KEYS), len(SYMS)


def events(idx, shift):
    op = A['op'][idx] + shift; cl = A['cl'][idx] + shift; n = len(idx)
    t = np.concatenate([op, cl]); k = np.concatenate([np.ones(n, np.int64), np.zeros(n, np.int64)]); j = np.concatenate([np.arange(n), np.arange(n)])
    o = np.lexsort((j, k, t)); t = t[o]
    return (t, k[o], j[o], server_day(t), A['lane'][idx], A['sym'][idx], A['ur'][idx], A['un'][idx], A['w'][idx])


@njit(cache=False)
def kernel(et, ek, ej, epd, lane, sym, ur, un, w, on, nsym, t0, t_end, rdol, maxopen, persym, dstop, buffer, taper, mode, pess, cycle, payshare, trail, dcap):
    """mode 0 funded with rewards, 1 evaluation (+6% target), 2 funded without rewards. Returns metrics array."""
    n = len(ur); lots = np.zeros(n); rk = np.zeros(n); sym_open = np.zeros(nsym)
    initial = 50000.0; bal = initial; peak = initial; floor = initial - 0.06 * initial
    anchor = bal; aday = -1; awk = -1; open_total = 0.0; nactive = 0; code = 0; end_t = t_end
    paid = 0.0; npay = 0; first_pay = -1.0; last_pay_pd = -1; prof_days = 0; max_day = 0.0; day_pnl = 0.0; week_pnl = 0.0
    worst_day = 0.0; worst_week = 0.0; cum = 0.0; cpeak = 0.0; dd_c = 0.0; dd_s = 0.0; trades = 0
    cur = 0; clen = 0; maxw = 0; maxl = 0; sw = 0; cw = 0; sl = 0; cl_ = 0; stop_entries = False
    target = initial * 1.06
    for e in range(len(et)):
        t = et[e]
        if t < t0: continue
        if t >= t_end: break
        pd = epd[e]
        if pd != aday:
            if aday != -1:
                if day_pnl < worst_day: worst_day = day_pnl
                if day_pnl >= 0.005 * initial: prof_days += 1
                if day_pnl > max_day: max_day = day_pnl
            wk = (pd + 3) // 7
            if wk != awk:
                if awk != -1 and week_pnl < worst_week: worst_week = week_pnl
                week_pnl = 0.0; awk = wk
            day_pnl = 0.0; aday = pd; anchor = bal
            if last_pay_pd < 0: last_pay_pd = pd
            if mode == 0 and pd - last_pay_pd >= cycle:
                prof = bal - initial
                if prof > 0 and prof_days >= 3 and max_day <= 0.2 * prof:
                    paid += payshare * prof; bal = initial; peak = initial; floor = initial - 0.06 * initial; anchor = bal
                    last_pay_pd = pd; prof_days = 0; max_day = 0.0; npay += 1
                    if first_pay < 0: first_pay = (t - t0) / 86400.0
            if mode != 1 and nactive == 0:                      # v2: a flat account that can never admit another entry is frozen
                room = bal - floor
                if room - buffer < 25.0:
                    code = 2; end_t = t; break
        j = ej[e]
        if ek[e] == 1:
            if stop_entries or not on[lane[j]]: continue
            if dcap > 0 and day_pnl >= dcap: continue          # daily profit cap (consistency rule helper); 0 = off
            room = bal - open_total - floor
            risk = rdol * w[j]
            if taper > 0 and taper * room < risk: risk = taper * room
            # v3: cut the trade down to fit every limit (never skip a trade that fits smaller)
            fit = min(maxopen - open_total, persym - sym_open[sym[j]], dstop - (anchor - (bal - open_total)), room - buffer)
            if fit < risk: risk = fit
            if risk < 25.0: continue
            lots[j] = risk / ur[j]; rk[j] = risk; open_total += risk; sym_open[sym[j]] += risk; nactive += 1
        else:
            if lots[j] <= 0: continue
            pnl = lots[j] * un[j]; lots[j] = 0.0; open_total -= rk[j]; sym_open[sym[j]] -= rk[j]; nactive -= 1
            bal += pnl; day_pnl += pnl; week_pnl += pnl; cum += pnl; trades += 1
            s = 1 if pnl > 0.005 else (-1 if pnl < -0.005 else 0)
            if s != 0:
                if s == cur: clen += 1
                else:
                    if cur == 1: sw += clen; cw += 1
                    elif cur == -1: sl += clen; cl_ += 1
                    cur = s; clen = 1
                if cur == 1 and clen > maxw: maxw = clen
                if cur == -1 and clen > maxl: maxl = clen
            if bal > peak:
                peak = bal
                if trail: floor = peak - 0.06 * initial      # trail=0: static floor (sensitivity)
            if cum > cpeak: cpeak = cum
            if cpeak - cum > dd_c: dd_c = cpeak - cum
        if cpeak - (cum - open_total) > dd_s: dd_s = cpeak - (cum - open_total)
        eq = bal - open_total if pess else bal
        if eq < floor or eq < anchor * 0.97:
            code = 1; end_t = t; break
        if mode == 1:
            if bal >= target: stop_entries = True
            if stop_entries and nactive == 0:
                if bal >= target:
                    code = 3; end_t = t; break
                stop_entries = False
        if mode != 1 and nactive == 0:
            room = bal - floor
            if room - buffer < 25.0:
                code = 2; end_t = t; break
    if day_pnl < worst_day: worst_day = day_pnl
    if week_pnl < worst_week: worst_week = week_pnl
    if cur == 1: sw += clen; cw += 1
    elif cur == -1: sl += clen; cl_ += 1
    out = np.zeros(17)
    out[0] = code; out[1] = (end_t - t0) / 86400.0; out[2] = paid; out[3] = npay; out[4] = first_pay; out[5] = trades; out[6] = cum
    out[7] = dd_c; out[8] = dd_s; out[9] = worst_day; out[10] = worst_week; out[11] = maxw; out[12] = maxl
    out[13] = sw / cw if cw > 0 else 0.0; out[14] = sl / cl_ if cl_ > 0 else 0.0; out[15] = bal; out[16] = (end_t - t0) / 86400.0
    return out


def mc_paths(seg, n, days, seed):
    a, b = SEG[seg]; m = date.fromisoformat(a); m += timedelta(days=(7 - m.weekday()) % 7); end = date.fromisoformat(b); mons = []
    while m + timedelta(days=BLOCK) <= end: mons.append(m); m += timedelta(days=7)
    idx = {m: np.searchsorted(A['op'], [utc_ts(m), utc_ts(m) + BLOCK * DAY]) for m in mons}
    rng = random.Random(seed); t0 = utc_ts(date(2030, 1, 7)); out = []
    for _ in range(n):
        ids, sh = [], []
        for k in range(math.ceil(days / BLOCK) + 1):
            s = mons[rng.randrange(len(mons))]; lo, hi = idx[s]; ids.append(np.arange(lo, hi)); sh.append(np.full(hi - lo, t0 + k * BLOCK * DAY - utc_ts(s)))
        out.append((t0, events(np.concatenate(ids), np.concatenate(sh))))
    return out


def hist_paths(seg, days):
    a, b = SEG[seg]; ev = events(np.nonzero((A['op'] >= utc_ts(a)) & (A['op'] < utc_ts(b)))[0], 0.0); out = []; d = date.fromisoformat(a)
    while utc_ts(d) + days * DAY <= utc_ts(b):
        if d.weekday() < 5: out.append((utc_ts(d), ev))
        d += timedelta(days=1)
    return out


def simulate(paths, members, r, g, days, mode=0, pess=True, cycle=14, share=0.8, trail=True):
    dcap = g.get('dcap', 0.0) / 100 * INITIAL
    on = np.array([k in members for k in KEYS])
    res = [kernel(*ev, on, NS, t0, t0 + days * DAY, r / 100 * INITIAL, g['maxopen'] / 100 * INITIAL, g['persym'] * r / 100 * INITIAL,
                  g['dstop'] / 100 * INITIAL, g['buffer'] / 100 * INITIAL, g['taper'], mode, pess, cycle, share, trail, dcap) for t0, ev in paths]
    return np.array(res)


def summary(o, days):
    n = len(o); q = lambda v, p: float(np.percentile(v, p)) if len(v) else None  # noqa: E731
    alive = o[:, 16]; months = alive / 30.4375; br = o[:, 0] == 1; fr = o[:, 0] == 2
    inc_m = o[:, 2] / np.maximum(months, 1e-9); gross_d = o[:, 6] / np.maximum(alive, 1e-9)
    return dict(n=n, horizon_days=days,
                breach=round(float(br.mean()), 4), freeze=round(float(fr.mean()), 4),
                breach_90=round(float((br & (o[:, 1] <= 91)).mean()), 4), breach_180=round(float((br & (o[:, 1] <= 182)).mean()), 4),
                breach_365=round(float((br & (o[:, 1] <= 365)).mean()), 4),
                ended_365=round(float(((br | fr) & (o[:, 1] <= 365)).mean()), 4),
                days_to_breach_median=round(float(np.median(o[br, 1])), 1) if br.any() else None,
                days_alive_median=round(float(np.median(alive)), 1),
                income_total_median=round(float(np.median(o[:, 2])), 2), income_total_mean=round(float(o[:, 2].mean()), 2),
                income_12m_median=None,
                income_month_median=round(float(np.median(inc_m)), 2), income_month_mean=round(float(inc_m.mean()), 2),
                income_week_median=round(float(np.median(inc_m)) * 7 / 30.4375, 2), income_day_median=round(float(np.median(inc_m)) / 30.4375, 2),
                gross_day_mean=round(float(gross_d.mean()), 2), gross_week_mean=round(float(gross_d.mean()) * 7, 2), gross_month_mean=round(float(gross_d.mean()) * 30.4375, 2),
                payouts_median=float(np.median(o[:, 3])), no_payout=round(float((o[:, 3] == 0).mean()), 4),
                first_payout_day_median=round(float(np.median(o[o[:, 4] >= 0, 4])), 1) if (o[:, 4] >= 0).any() else None,
                trades_per_month=round(float(np.median(o[:, 5] / np.maximum(months, 1e-9))), 2), trades_per_day=round(float(np.median(o[:, 5] / np.maximum(alive, 1e-9))), 3),
                dd_closed_median=round(float(np.median(o[:, 7])), 0), dd_closed_p95=round(q(o[:, 7], 95), 0), dd_closed_worst=round(float(o[:, 7].max()), 0),
                dd_stop_median=round(float(np.median(o[:, 8])), 0), dd_stop_p95=round(q(o[:, 8], 95), 0), dd_stop_worst=round(float(o[:, 8].max()), 0),
                worst_day=round(float(o[:, 9].min()), 0), worst_day_p5=round(q(o[:, 9], 5), 0), worst_week=round(float(o[:, 10].min()), 0), worst_week_p5=round(q(o[:, 10], 5), 0),
                win_streak_avg=round(float(np.median(o[:, 13])), 2), win_streak_max_median=float(np.median(o[:, 11])), win_streak_max=float(o[:, 11].max()),
                loss_streak_avg=round(float(np.median(o[:, 14])), 2), loss_streak_max_median=float(np.median(o[:, 12])), loss_streak_max=float(o[:, 12].max()))


def objective(s): return (s['income_total_mean'], -(s['breach'] + s['freeze']))   # PLAN Addendum 1


def save(name, obj): (R / name).write_text(json.dumps(obj, indent=1, default=float), encoding='utf-8')


def load_json(name): return json.loads((R / name).read_text(encoding='utf-8'))


def select():
    t = time.time(); paths = mc_paths('dev', MC_N, 365, SEED); members = list(KEYS); log = []
    base = summary(simulate(paths, members, 0.5, REF, 365), 365); log.append(dict(step=0, removed=None, income_mean=base['income_total_mean'], breach=base['breach'], freeze=base['freeze']))
    print('start', len(members), base['income_total_mean'], base['breach'], base['freeze'], f'{time.time() - t:.0f}s', flush=True)
    while len(members) > 3:
        best = None
        for k in members:
            s = summary(simulate(paths, [m for m in members if m != k], 0.5, REF, 365), 365)
            if best is None or objective(s) > objective(best[1]): best = (k, s)
        gain = best[1]['income_total_mean'] - base['income_total_mean']
        if gain < max(1.0, 0.01 * abs(base['income_total_mean'])): break
        members.remove(best[0]); base = best[1]; log.append(dict(step=len(log), removed=best[0], income_mean=base['income_total_mean'], breach=base['breach'], freeze=base['freeze']))
        print('removed', best[0], base['income_total_mean'], base['breach'], base['freeze'], f'{time.time() - t:.0f}s', flush=True)
    save('SELECT.json', dict(members=members, log=log, reference=REF, universe=KEYS)); print('kept', len(members), members)


def grid():
    t = time.time(); members = load_json('SELECT.json')['members']; paths = mc_paths('dev', MC_N, 365, SEED); out = {}
    for r in RISKS:
        rows = []
        for g in GRID:
            if g['maxopen'] < r: continue
            s = summary(simulate(paths, members, r, g, 365), 365); rows.append(dict(guard=g, dev=s))
        ok = [x for x in rows if x['dev']['breach_365'] <= 0.10]   # PLAN Addendum 4: freeze constraint dropped
        chosen = max(ok, key=lambda x: objective(x['dev'])) if ok else min(rows, key=lambda x: (x['dev']['breach'] + x['dev']['freeze'], -x['dev']['income_total_mean']))
        out[str(r)] = dict(chosen=chosen, n=len(rows), qualified=len(ok), top5=sorted(rows, key=lambda x: objective(x['dev']), reverse=True)[:5])
        print(r, 'chosen', chosen['guard'], 'income mean', chosen['dev']['income_total_mean'], 'median', chosen['dev']['income_total_median'], 'breach', chosen['dev']['breach'], 'freeze', chosen['dev']['freeze'], 'qualified', len(ok), f'{time.time() - t:.0f}s', flush=True)
    save('GRID.json', out)


def evaluate(seg, days, hist_days=None, n=MC_N, seed=SEED):
    members = load_json('SELECT.json')['members']; g = load_json('GRID.json'); mc = mc_paths(seg, n, days, seed)
    hp = hist_paths(seg, hist_days) if hist_days else []; out = {}
    for r in RISKS:
        gd = g[str(r)]['chosen']['guard']
        out[str(r)] = dict(guard=gd, mc=summary(simulate(mc, members, r, gd, days), days),
                           mc_optimistic=summary(simulate(mc, members, r, gd, days, pess=False), days),
                           hist=summary(simulate(hp, members, r, gd, hist_days), hist_days) if hp else None)
    return out


def validate():
    v = evaluate('val', 365, 182); save('VALIDATION.json', v)
    ok = [r for r in v if v[r]['mc']['breach_365'] <= 0.10]
    rec = max(ok, key=lambda r: v[r]['mc']['income_total_mean']) if ok else min(v, key=lambda r: v[r]['mc']['breach'])
    save('RECOMMENDED.json', dict(risk=float(rec), rule='highest validation mean 12-month income with validation breach <= 10% (PLAN Addendum 1)'))
    for r, x in v.items(): print(r, 'val income', x['mc']['income_total_median'], 'breach', x['mc']['breach'], 'hist', x['hist'] and x['hist']['income_total_median'])
    print('recommended', rec)


def oos():
    assert not (R / 'OOS.json').exists(), 'OOS already run once'
    o = evaluate('oos', 365, 365); save('OOS.json', o)
    for r, x in o.items(): print(r, 'oos income', x['mc']['income_total_median'], 'breach', x['mc']['breach'], 'hist', x['hist']['income_total_median'], x['hist']['breach'])


def final():
    members = load_json('SELECT.json')['members']; g = load_json('GRID.json')
    mc3 = mc_paths('all', MC_N, 3 * 364, SEED + 1); mc1 = mc_paths('all', MC_N, 365, SEED + 2); hp = hist_paths('all', 365); out = {}
    for r in RISKS:
        gd = g[str(r)]['chosen']['guard']
        out[str(r)] = dict(guard=gd,
                           funded_3y=summary(simulate(mc3, members, r, gd, 3 * 364), 3 * 364),
                           funded_3y_optimistic=summary(simulate(mc3, members, r, gd, 3 * 364, pess=False), 3 * 364),
                           funded_1y=summary(simulate(mc1, members, r, gd, 365), 365),
                           funded_1y_hist=summary(simulate(hp, members, r, gd, 365), 365),
                           funded_1y_5day=summary(simulate(mc1, members, r, gd, 365, cycle=5), 365),
                           funded_1y_95=summary(simulate(mc1, members, r, gd, 365, share=0.95), 365),
                           survival_no_rewards_3y=summary(simulate(mc3, members, r, gd, 3 * 364, mode=2), 3 * 364),
                           funded_3y_static_floor=summary(simulate(mc3, members, r, gd, 3 * 364, trail=False), 3 * 364),
                           funded_1y_hist_static_floor=summary(simulate(hp, members, r, gd, 365, trail=False), 365),
                           evaluation=eval_summary(simulate(mc1, members, r, gd, 365, mode=1)), evaluation_hist=eval_summary(simulate(hp, members, r, gd, 365, mode=1)))
        f = out[str(r)]['funded_3y']; print(r, 'income/month', f['income_month_median'], 'breach3y', f['breach'], 'freeze', f['freeze'], flush=True)
    save('FINAL.json', out)


def eval_summary(o):
    n = len(o); p = o[:, 0] == 3; days = o[p, 1]
    return dict(n=n, pass_rate=round(float(p.mean()), 4), breach=round(float((o[:, 0] == 1).mean()), 4), freeze=round(float((o[:, 0] == 2).mean()), 4),
                pass_30=round(float((p & (o[:, 1] <= 30)).mean()), 4), pass_60=round(float((p & (o[:, 1] <= 60)).mean()), 4), pass_90=round(float((p & (o[:, 1] <= 90)).mean()), 4),
                median_days=round(float(np.median(days)), 1) if p.any() else None)


if __name__ == '__main__':
    dict(select=select, grid=grid, validate=validate, oos=oos, final=final)[sys.argv[1]]()
