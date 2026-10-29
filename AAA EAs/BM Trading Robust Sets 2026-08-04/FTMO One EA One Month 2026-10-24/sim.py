"""Can ONE EA pass FTMO 2-step in one month? (owner request 2026-10-24). Python + numba replay of frozen ledgers; no MT5.

Stream: Portfolio Long History All ORB05 2026-10-14 RISK_ROWS full-eas (36 members, same as the website / FTMO Swing study).
Rules: phase 1 +10%, phase 2 +5% on a fresh balance from the next Prague midnight, >= 4 trading days per phase,
daily loss 5% of initial from the Prague-midnight balance, max loss 10%. Breach checked on balance minus every open
position at its full stop (one EA: a fair conservative proxy). Fixed r% of balance per trade, fractional lots, recorded costs.
Pass in a month = both phases done <= 30 calendar days from the start. Selection on development only (data_split.py).
python sim.py run
"""
import importlib.util, json, math, random, statistics, sys
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
RISKS = (1.0, 2.0, 3.0, 4.0); DAY = 86400.0; H = 60; MC_N = 1000; SEED = 20261024; BLOCK = 28
NEWS = {'news-pulse-btc', 'news-pulse-eurusd', 'news-pulse-xag', 'news-pulse-xau'}


def utc_ts(d): return datetime.combine(date.fromisoformat(d) if isinstance(d, str) else d, datetime.min.time(), tzinfo=timezone.utc).timestamp()


def last_sunday(y, m):
    d = date(y, m, 31); return d - timedelta(days=(d.weekday() + 1) % 7)


DST = np.array(sorted(utc_ts(last_sunday(y, m)) + 3600 for y in range(2015, 2045) for m in (3, 10)))


def pday(t):
    k = np.searchsorted(DST, t, side='right'); return np.floor((t + np.where(k % 2 == 1, 7200.0, 3600.0)) / DAY).astype(np.int64)


@njit(cache=False)
def kernel(et, ek, ej, epd, ur, un, t0, risk):
    """Returns (both_day, p1_day, breach_day) in days from t0 (-1 = not reached)."""
    n = len(ur); lots = np.zeros(n); bal = 100000.0; anchor = bal; aday = -1; open_risk = 0.0; nactive = 0
    phase = 1; target = 110000.0; tdays = 0; last_tday = -1; stop = False; p1 = -1.0; p1pd = -1
    for e in range(len(et)):
        t = et[e]
        if t < t0: continue
        if epd[e] != aday: aday = epd[e]; anchor = bal
        j = ej[e]
        if ek[e] == 1:
            if stop: continue
            if phase == 2 and epd[e] <= p1pd: continue          # phase 2 starts at the next Prague midnight
            x = bal * risk / 100.0 / ur[j]; lots[j] = x; open_risk += x * ur[j]; nactive += 1
            if epd[e] != last_tday: last_tday = epd[e]; tdays += 1
        else:
            if lots[j] <= 0: continue
            x = lots[j]; lots[j] = 0.0; open_risk -= x * ur[j]; nactive -= 1; bal += x * un[j]
        eq = bal - open_risk
        if eq < anchor - 5000.0 or eq < 90000.0: return -1.0, p1, (t - t0) / DAY
        if bal >= target and tdays >= 4: stop = True
        if stop and nactive == 0:
            if bal >= target and tdays >= 4:
                if phase == 1:
                    p1 = (t - t0) / DAY; phase = 2; bal = 100000.0; anchor = bal; target = 105000.0
                    tdays = 0; last_tday = -1; stop = False; p1pd = epd[e]
                else:
                    return (t - t0) / DAY, p1, -1.0
            else:
                stop = False
    return -1.0, p1, -1.0


def load():
    raw = json.loads(SRC.read_text(encoding='utf-8'))['full-eas']
    by = {}
    for r in raw:
        if r['unit_risk'] > 0 and r['op'] < r['cl']:
            by.setdefault(r['key'], []).append((r['op'], r['cl'], r['unit_risk'] / r.get('risk_weight', 1.), r['unit_gross'] + r['unit_comm'] + r['unit_swap']))
    return {k: np.array(sorted(v)) for k, v in by.items()}


def build(rows, shift=None):
    op, cl = rows[:, 0] + (0 if shift is None else shift), rows[:, 1] + (0 if shift is None else shift); n = len(op)
    t = np.concatenate([op, cl]); kind = np.concatenate([np.ones(n, np.int64), np.zeros(n, np.int64)]); j = np.concatenate([np.arange(n), np.arange(n)])
    o = np.lexsort((j, kind, t)); t = t[o]
    return t, kind[o], j[o], pday(t), rows[:, 2].copy(), rows[:, 3].copy()


def attempts(rows, seg, risk, rng_seed):
    a, b = (utc_ts(x) for x in SEG[seg]); out = {'hist': [], 'mc': []}
    if not len(rows): return out
    idx = (rows[:, 0] >= a) & (rows[:, 0] < b); sub = rows[idx]
    if len(sub):
        ev = build(sub); d = date.fromisoformat(SEG[seg][0])
        while utc_ts(d) + H * DAY <= b:
            if d.weekday() < 5:
                out['hist'].append(kernel(*ev, utc_ts(d), risk))
            d += timedelta(days=1)
    m = date.fromisoformat(SEG[seg][0]); m += timedelta(days=(7 - m.weekday()) % 7); mons = []
    while utc_ts(m) + BLOCK * DAY <= b: mons.append(m); m += timedelta(days=7)
    rng = random.Random(rng_seed); t0 = utc_ts(date(2030, 1, 7))
    for _ in range(MC_N):
        parts, shifts = [], []
        for k in range(H // BLOCK + 2):
            s = mons[rng.randrange(len(mons))]; sel = (rows[:, 0] >= utc_ts(s)) & (rows[:, 0] < utc_ts(s) + BLOCK * DAY)
            parts.append(rows[sel]); shifts.append(np.full(sel.sum(), t0 + k * BLOCK * DAY - utc_ts(s)))
        pr = np.concatenate(parts) if parts else np.zeros((0, 4))
        if not len(pr): out['mc'].append((-1.0, -1.0, -1.0)); continue
        sh = np.concatenate(shifts); o = np.argsort(pr[:, 0] + sh, kind='stable')
        out['mc'].append(kernel(*build(pr[o], sh[o]), t0, risk))
    return out


def summ(res, n_trades_month):
    if not res: return None
    n = len(res); both = [r[0] for r in res if 0 <= r[0] <= H]; p1 = [r[1] for r in res if 0 <= r[1] <= H]
    return dict(n=n, both_30=round(sum(x <= 30 for x in both) / n, 4), both_60=round(len(both) / n, 4), p1_30=round(sum(x <= 30 for x in p1) / n, 4),
                breach_30=round(sum(0 <= r[2] <= 30 for r in res) / n, 4), breach_60=round(sum(0 <= r[2] <= H for r in res) / n, 4),
                median_days_both=round(statistics.median(both), 1) if both else None, trades_per_month=n_trades_month)


def one(k):
    rows = load()[k]; tpm = round(len(rows) / 60.0, 2); res_all = {}
    for risk in RISKS:
        res = {seg: attempts(rows, seg, risk, SEED) for seg in SEG}
        res_all[f'{k}|{risk}'] = dict(ea=k, risk=risk, news=k in NEWS, trades_per_month=tpm, trades_per_day=round(len(rows) / 1826, 3),
                                      **{f'{seg}_{kind}': summ(res[seg][kind], tpm) for seg in SEG for kind in ('hist', 'mc')})
    return res_all


def run():
    from concurrent.futures import ProcessPoolExecutor
    keys = sorted(load()); out = dict(split=SPLIT, results={})
    with ProcessPoolExecutor(max_workers=5) as ex:
        for res in ex.map(one, keys):
            out['results'].update(res)
            for k, r in res.items(): print(k, 'dev MC both<=30', r['dev_mc']['both_30'], 'oos', r['oos_mc']['both_30'], 'all', r['all_mc']['both_30'], flush=True)
    (R / 'RESULTS.json').write_text(json.dumps(out, indent=1), encoding='utf-8')


if __name__ == '__main__':
    run()
