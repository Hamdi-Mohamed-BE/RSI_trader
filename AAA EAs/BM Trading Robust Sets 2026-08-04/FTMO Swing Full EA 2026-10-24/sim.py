"""FTMO Swing replay of the Full EA portfolio · Recommended Adaptive (PLAN.md + Addendum 1). Python + numba; no MT5.

python sim.py parity | run
"""
import bisect, json, math, random, statistics, sys, time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import numpy as np
from numba import njit

R = Path(__file__).resolve().parent; B = R.parent; STORE = B.parent / 'EA store'
SRC = B / 'Portfolio Long History All ORB05 2026-10-14/RISK_ROWS.json'
DAY = 86400.0; INITIAL = 10000.0
RISKS = (0.5, 0.75, 1.0); NEWS_RATIO = 0.75; SEED = 20261024; MC_N = 2000; BLOCK = 28
P1, P2 = 0.10, 0.05; DAILY, TOTAL = 0.05, 0.10; SPLIT = 0.80; PAYOUT_DAYS = 14
CH_DAYS = 365; FUND_DAYS = 3 * 364; HIST_FIRST, HIST_LAST = date(2021, 10, 6), date(2025, 10, 5)
VARIANTS = ('NO_NEWS', 'ALL36')


def load(variant):
    raw = json.loads(SRC.read_text(encoding='utf-8'))['full-eas']
    rows = [(f, r) for f, r in enumerate(raw) if r['unit_risk'] > 0 and r['op'] < r['cl'] and not (variant == 'NO_NEWS' and r.get('news'))]
    rows.sort(key=lambda x: x[1]['op'])                     # stable: equal opens keep file order, as allocation_replay
    lanes = {}
    A = dict(op=np.array([r['op'] for _, r in rows]), cl=np.array([r['cl'] for _, r in rows]), f=np.array([f for f, _ in rows], np.int64),
             lane=np.array([lanes.setdefault(r.get('lane', r['key']), len(lanes)) for _, r in rows], np.int64),
             news=np.array([bool(r.get('news')) for _, r in rows]), nas=np.array([r['key'] == 'nasdaq-5m-candle-momentum' for _, r in rows]),
             ur=np.array([r['unit_risk'] for _, r in rows]), un=np.array([r['unit_gross'] + r['unit_comm'] + r['unit_swap'] for _, r in rows]),
             w=np.array([r.get('risk_weight', 1.) for _, r in rows]), key=[r['key'] for _, r in rows])
    return A, len(lanes)


def utc_ts(d): return datetime.combine(d, datetime.min.time(), tzinfo=timezone.utc).timestamp()


def last_sunday(y, m):
    d = date(y, m, 31)
    return d - timedelta(days=(d.weekday() + 1) % 7)


DST = np.array(sorted(utc_ts(last_sunday(y, m)) + 3600 for y in range(2015, 2045) for m in (3, 10)))


def prague_day(t):
    """CET/CEST day index (EU DST changes at 01:00 UTC on the last Sundays of March and October)."""
    k = np.searchsorted(DST, t, side='right'); off = np.where(k % 2 == 1, 7200.0, 3600.0)
    return np.floor((t + off) / DAY).astype(np.int64)


def events(op, cl, f):
    n = len(op); t = np.concatenate([op, cl]); kind = np.concatenate([np.ones(n, np.int64), np.zeros(n, np.int64)])
    ff = np.concatenate([f, f]); j = np.concatenate([np.arange(n), np.arange(n)])
    o = np.lexsort((ff, kind, t)); t = t[o]
    return t, kind[o], j[o], np.floor(t / DAY).astype(np.int64), prague_day(t)


@njit(cache=False)
def kernel(et, ek, ej, eud, epd, lane, news, nas, ur, un, w, nlanes, t_start, t_end, risk, news_ratio, target, ftmo, pess, payout, pay_days):
    """Returns (code, day, trades, paid, balance). code 0 open, 1 pass, 2 breach. Sizing = allocation_replay(adaptive)."""
    n = len(ur); lots = np.zeros(n); lossruns = np.zeros(nlanes, np.int64)
    dmin = eud[0] if len(eud) else 0; dspan = (eud[-1] - dmin + 2) if len(eud) else 1
    daily = np.zeros(dspan)
    bal = 10000.0; peak = bal; anchor = bal; aday = -1; open_risk = 0.0; trades = 0; stop = False; nactive = 0
    paid = 0.0; next_pay = t_start + pay_days * 86400.0; tgt = 10000.0 * (1.0 + target)
    for e in range(len(et)):
        t = et[e]
        if t < t_start: continue
        if t >= t_end: break
        j = ej[e]
        if ftmo and epd[e] != aday: aday = epd[e]; anchor = bal
        if payout and t >= next_pay:
            while next_pay <= t: next_pay += pay_days * 86400.0
            if bal > 10000.0:
                x = bal - 10000.0; bal -= x; anchor -= x; peak = bal; paid += 0.8 * x
        if ek[e] == 1:
            if bal <= 0 or stop: continue
            budget = bal * risk / 100.0 * w[j]
            if news[j]:
                budget = bal * risk * news_ratio / 100.0
            else:
                if daily[eud[e] - dmin] <= -10000.0 * 0.05: continue
                dd = (peak - bal) / peak * 100.0
                budget *= 0.25 if dd >= 7 else (0.5 if dd >= 4 else 1.0)
                budget *= 0.25 if lossruns[lane[j]] >= 5 else (0.5 if lossruns[lane[j]] >= 3 else 1.0)
                if nas[j]: budget *= 0.25
            lots[j] = budget / ur[j]; open_risk += lots[j] * ur[j]; nactive += 1
        else:
            if lots[j] <= 0: continue
            x = lots[j]; lots[j] = 0.0; open_risk -= x * ur[j]; nactive -= 1
            net = x * un[j]; bal += net
            if bal > peak: peak = bal
            daily[eud[e] - dmin] += net; trades += 1
            lossruns[lane[j]] = lossruns[lane[j]] + 1 if net < -0.005 else 0
        if ftmo:
            eq = bal - open_risk if pess else bal
            if eq < anchor - 0.05 * 10000.0 or eq < 10000.0 * 0.9:
                return 2, (t - t_start) / 86400.0, trades, paid, bal
        if target > 0:
            if bal >= tgt: stop = True
            if stop and nactive == 0:
                if bal >= tgt: return 1, (t - t_start) / 86400.0, trades, paid, bal
                stop = False
    return 0, -1.0, trades, paid, bal


class Path_:
    def __init__(self, A, nl, idx, shift):
        self.ev = events(A['op'][idx] + shift, A['cl'][idx] + shift, A['f'][idx])
        self.arr = (A['lane'][idx], A['news'][idx], A['nas'][idx], A['ur'][idx], A['un'][idx], A['w'][idx], nl)

    def run(self, t_start, days, risk, target=0.0, ftmo=True, pess=False, payout=False):
        c, d, n, paid, bal = kernel(*self.ev, *self.arr, t_start, t_start + days * DAY, risk, NEWS_RATIO, target, ftmo, pess, payout, PAYOUT_DAYS)
        return dict(code=int(c), day=None if d < 0 else d, trades=int(n), paid=paid, balance=bal)


def challenge(p, t0, risk, pess, data_end):
    a = p.run(t0, CH_DAYS, risk, P1, pess=pess)
    out = dict(p1=a['code'], p1_day=a['day'], p1_trades=a['trades'])
    if a['code'] == 1:
        t1 = t0 + a['day'] * DAY; b = p.run(t1, CH_DAYS, risk, P2, pess=pess)
        out.update(p2=b['code'], p2_day=b['day'], p2_trades=b['trades'], p2_censored=b['code'] == 0 and t1 + CH_DAYS * DAY > data_end)
        if b['code'] == 1: out['funded_day'] = a['day'] + b['day']
    return out


def summarise_ch(res):
    n = len(res); q = lambda v, p: sorted(v)[min(len(v) - 1, int(p * len(v)))] if v else None  # noqa: E731
    p1 = [r for r in res if r['p1'] == 1]; p2 = [r for r in p1 if r.get('p2') == 1]; fd = [r['funded_day'] for r in p2]
    md = lambda v: round(statistics.median(v), 1) if v else None  # noqa: E731
    return dict(n=n, p1_pass=len(p1) / n, p1_breach=sum(r['p1'] == 2 for r in res) / n, p1_open=sum(r['p1'] == 0 for r in res) / n,
                p1_pass_30=sum(r['p1_day'] <= 30 for r in p1) / n, p1_pass_90=sum(r['p1_day'] <= 90 for r in p1) / n, p1_pass_180=sum(r['p1_day'] <= 180 for r in p1) / n,
                p1_days_median=md([r['p1_day'] for r in p1]),
                p2_pass_given_p1=len(p2) / len(p1) if p1 else None, p2_breach_given_p1=sum(r.get('p2') == 2 for r in p1) / len(p1) if p1 else None,
                p2_days_median=md([r['p2_day'] for r in p2]), p2_censored=sum(bool(r.get('p2_censored')) for r in p1),
                funded=len(p2) / n, funded_90=sum(d <= 90 for d in fd) / n, funded_180=sum(d <= 180 for d in fd) / n,
                funded_days_median=md(fd), funded_days_p25=q(fd, .25), funded_days_p75=q(fd, .75),
                trades_per_day_p1=md([r['p1_trades'] / max(r['p1_day'], 1.0) for r in p1]))


def summarise_f(res):
    n = len(res); br = [r for r in res if r['code'] == 2]
    life = [r['day'] if r['code'] == 2 else FUND_DAYS for r in res]
    monthly = [r['paid'] / (l / 30.4375) for r, l in zip(res, life) if l > 0]
    md = lambda v: round(statistics.median(v), 1) if v else None  # noqa: E731
    return dict(n=n, breach_3y=len(br) / n, breach_1y=sum(r['day'] <= 365 for r in br) / n, breach_180=sum(r['day'] <= 180 for r in br) / n,
                breach_90=sum(r['day'] <= 90 for r in br) / n,
                days_alive_median=md(life), days_to_breach_median_breached=md([r['day'] for r in br]),
                monthly_median=round(statistics.median(monthly), 2), monthly_mean=round(statistics.fmean(monthly), 2),
                total_paid_median=round(statistics.median(r['paid'] for r in res), 2), total_paid_mean=round(statistics.fmean(r['paid'] for r in res), 2),
                no_payout=sum(r['paid'] <= 0 for r in res) / n,
                trades_per_day=md([r['trades'] / max(l, 1.0) for r, l in zip(res, life)]))


def mc_paths(A, nl, n, days, seed):
    first, last = date(2021, 10, 6), date(2026, 10, 5)
    m = first + timedelta(days=(7 - first.weekday()) % 7); mons = []
    while m + timedelta(days=BLOCK) <= last: mons.append(m); m += timedelta(days=7)
    idx = {m: np.searchsorted(A['op'], [utc_ts(m), utc_ts(m) + BLOCK * DAY]) for m in mons}
    rng = random.Random(seed); t0 = utc_ts(date(2030, 1, 7))
    for _ in range(n):
        ids, sh = [], []
        for k in range(math.ceil(days / BLOCK) + 2):
            s = mons[rng.randrange(len(mons))]; lo, hi = idx[s]
            ids.append(np.arange(lo, hi)); sh.append(np.full(hi - lo, t0 + k * BLOCK * DAY - utc_ts(s)))
        idx_ = np.concatenate(ids); yield t0, Path_(A, nl, idx_, np.concatenate(sh))


def run():
    began = time.time(); out = dict(source=str(SRC.name), results={})
    for variant in VARIANTS:
        A, nl = load(variant); whole = Path_(A, nl, np.arange(len(A['op'])), 0.0); data_end = float(A['cl'].max())
        out.setdefault('positions', {})[variant] = len(A['op'])
        for risk in RISKS:
            for pess in (False, True):
                tag = f"{variant}|{risk:.2f}|{'pessimistic' if pess else 'optimistic'}"
                hist = []; d = HIST_FIRST
                while d <= HIST_LAST:
                    if d.weekday() < 5: hist.append(challenge(whole, utc_ts(d), risk, pess, data_end))
                    d += timedelta(days=1)
                mc = [challenge(p, t0, risk, pess, 1e18) for t0, p in mc_paths(A, nl, MC_N, 2 * CH_DAYS + 30, SEED)]
                fmc = [p.run(t0, FUND_DAYS, risk, pess=pess, payout=True) for t0, p in mc_paths(A, nl, MC_N // 2, FUND_DAYS, SEED + 1)]
                fh = []; d = HIST_FIRST
                while d <= date(2023, 10, 5):
                    if d.weekday() == 0: fh.append(whole.run(utc_ts(d), FUND_DAYS, risk, pess=pess, payout=True))
                    d += timedelta(days=1)
                r = out['results'][tag] = dict(challenge_hist=summarise_ch(hist), challenge_mc=summarise_ch(mc), funded_mc=summarise_f(fmc), funded_hist=summarise_f(fh))
                print(tag, 'P1', round(r['challenge_mc']['p1_pass'], 3), 'P2|P1', r['challenge_mc']['p2_pass_given_p1'] and round(r['challenge_mc']['p2_pass_given_p1'], 3),
                      'funded', round(r['challenge_mc']['funded'], 3), r['challenge_mc']['funded_days_median'], '| F breach3y', round(r['funded_mc']['breach_3y'], 3),
                      'monthly', r['funded_mc']['monthly_median'], f'{time.time() - began:.0f}s', flush=True)
    (R / 'RESULTS.json').write_text(json.dumps(out, indent=1), encoding='utf-8')


def parity():
    sys.path.insert(0, str(STORE)); from app.portfolio_analytics import allocation_replay  # noqa: E402
    raw = json.loads(SRC.read_text(encoding='utf-8'))['full-eas']; A, nl = load('ALL36'); checks = {}
    for start, end in (('2024-01-01', '2025-01-01'), ('2022-01-01', '2023-01-01'), ('2025-10-05', '2026-10-05')):
        closed, _ = allocation_replay(raw, start, end, 'pct', 1.0, INITIAL, adaptive=True, news_percent=0.75)
        web = INITIAL + sum(t['net_profit'] for t in closed)
        a, b = utc_ts(date.fromisoformat(start)), utc_ts(date.fromisoformat(end))
        idx = np.nonzero((A['op'] >= a) & (A['cl'] < b))[0]
        m = Path_(A, nl, idx, 0.0).run(a, (b - a) / DAY, 1.0, ftmo=False)
        checks[f'{start}..{end}'] = dict(web_final=round(web, 2), sim_final=round(m['balance'], 2), web_trades=len(closed), sim_trades=m['trades'],
                                         exact=abs(web - m['balance']) <= max(.01, 1e-9 * abs(web)) and len(closed) == m['trades'])
    print(json.dumps(checks, indent=1)); (R / 'PARITY.json').write_text(json.dumps(checks, indent=1), encoding='utf-8')


if __name__ == '__main__':
    dict(run=run, parity=parity)[sys.argv[1]]()
