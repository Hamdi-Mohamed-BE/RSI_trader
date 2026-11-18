"""Addendum 3 (owner 2026-11-18: "make your best to make it as close as possible the shown results").
REVERSE-ENGINEERING FIT, not evidence: 576 plausible readings of the prompt, TradingView-style fills (tv_replay.tv_bar, no spread / costs), stop at the breakout
candle, 0.5R from the signal close, one trade a day, one position at a time. Fitted on the reel's own window (2023 ->) to the reel's claims:
since 2023 714 trades / 72% win; 2026 80% win / PF 2.06. The closest settings are then shown on 2019-07 -> 2022 (never used in the fit) and with the recorded
CFD spread. Bars: bars/USTEC_M15LONG.npz (server time = UTC; timing check in TIMING_CHECK.json). python fit.py -> FIT.json"""
import itertools, json
from datetime import datetime
from pathlib import Path

import numpy as np

import tv_replay as T

H = Path(__file__).resolve().parent; POINT = 0.01
TARGET = dict(n23=714, win23=72.0, win26=80.0, pf26=2.06)
GRID = dict(range_start=(555, 615), last=(585, 615, 660, 720, 840, 930), first_only=(False, True), body=(0, 1), entry=('open', 'close'), ema=('m15', 'h1', 'none'), flat=(None, 960))


def prep():
    z = T.load('M15LONG'); t = z['time'].astype(np.int64)
    ny = [T.ny(x) for x in t]; mins = np.array([d.hour * 60 + d.minute for d in ny]); dates = np.array([d.date().toordinal() for d in ny]); iso = [d.date().isoformat() for d in ny]
    c = z['close']; e15 = T.ema(c)
    hs = t // 3600 * 3600; ends = np.r_[np.nonzero(np.diff(hs))[0], len(t) - 1]          # last M15 bar of each UTC hour
    hstart = hs[ends]; e1h = T.ema(c[ends])
    k = np.searchsorted(hstart, t + 900 - 3600, side='right') - 1                         # latest COMPLETED hour at the signal bar's close
    eh = np.where(k >= 0, e1h[np.clip(k, 0, None)], np.nan)
    hh, ll = z['high'], z['low']; pc = np.r_[c[0], c[:-1]]; tr = np.maximum(hh - ll, np.maximum(np.abs(hh - pc), np.abs(ll - pc)))
    atr = np.empty_like(tr); atr[:14] = np.nan; atr[13] = tr[:14].mean()                       # Wilder ATR(14) (Pine ta.atr / MT5 iATR style seed)
    for i in range(14, len(tr)): atr[i] = (atr[i - 1] * 13 + tr[i]) / 14
    return dict(t=t, o=z['open'], h=hh, l=ll, c=c, sp=z['spread'] * POINT, mins=mins, dates=dates, iso=iso, e15=e15, eh=eh, atr=atr)


def sim(D, p, spread=False, cost_pts=0.0):   # cost_pts: flat round-trip cost in index points, charged in R (Addendum 3 futures-like check)
    o, h, l, c, mins, dates, iso, sp = D['o'], D['h'], D['l'], D['c'], D['mins'], D['dates'], D['iso'], D['sp']
    ema = D['e15'] if p['ema'] == 'm15' else (D['eh'] if p['ema'] == 'h1' else None)
    n = len(o); out = []; day = None; done = False; rng = None; seen = False; pos = None
    for i in range(n - 1):
        if dates[i] != day: day = dates[i]; done = False; rng = None; seen = False
        if pos is not None and i >= pos[6]:
            side, sl, tp, entry, risk, opened, start, oday = pos
            if p['flat'] is not None and (dates[i] != oday or mins[i] >= p['flat']):
                xp = o[i] - (sp[i] if (spread and side > 0) else 0.0) if side > 0 else o[i] + (sp[i] if spread else 0.0)
            else:
                bo, bh, bl = (o[i], h[i], l[i]) if not (spread and side < 0) else (o[i] + sp[i], h[i] + sp[i], l[i] + sp[i])
                xp = T.tv_bar(bo, bh, bl, side, sl, tp)
            if xp is not None: out.append((opened, side * (xp - entry) / risk - (cost_pts / risk if cost_pts else 0.0))); pos = None
        if mins[i] == p['range_start']:
            rng = (h[i], l[i]) if h[i] - l[i] >= 1.0 else None
            if rng and p.get('atr') and (np.isnan(D['atr'][i]) or h[i] - l[i] > p['atr'] * D['atr'][i]): rng = None   # Addendum 4 volatility filter
            continue
        if rng is None or done or pos is not None or mins[i] < p['range_start'] + 15 or mins[i] > p['last'] or dates[i + 1] != day: continue
        hi, lo = rng
        up = (min(o[i], c[i]) > hi) if p['body'] else (c[i] > hi); dn = (max(o[i], c[i]) < lo) if p['body'] else (c[i] < lo)
        if not (up or dn): continue
        if p['first_only'] and seen: continue
        seen = True; side = 1 if up else -1
        if ema is not None and (np.isnan(ema[i]) or (side > 0 and c[i] <= ema[i]) or (side < 0 and c[i] >= ema[i])): continue
        stop = l[i] if side > 0 else h[i]
        if p['entry'] == 'close': entry = c[i] + (sp[i] if (spread and side > 0) else 0.0); start = i + 1
        else: entry = o[i + 1] + (sp[i + 1] if (spread and side > 0) else 0.0); start = i + 1
        if (side > 0 and entry <= stop) or (side < 0 and entry >= stop): continue
        tp = c[i] + side * 0.5 * abs(c[i] - stop); risk = abs(entry - stop)
        pos = (side, stop, tp, entry, risk, iso[i], start, day); done = True
    return out


def stats(x, a, b):
    x = [r for d, r in x if a <= d < b]
    if not x: return dict(trades=0)
    gw = sum(r for r in x if r > 0); gl = -sum(r for r in x if r < 0); eq = pk = dd = 0.0
    for r in x: eq += r; pk = max(pk, eq); dd = max(dd, pk - eq)
    months = (datetime.fromisoformat(b) - datetime.fromisoformat(a)).days / 30.4375
    return dict(trades=len(x), per_month=round(len(x) / months, 1), per_day=round(len(x) / months / 21, 2), win=round(100 * sum(1 for r in x if r > 0) / len(x), 1),
                pf=round(gw / gl, 2) if gl else None, total_r=round(sum(x), 1), avg_r=round(sum(x) / len(x), 3), max_dd_r=round(dd, 1))


def score(s23, s26):
    if not s23.get('trades') or not s26.get('trades') or not s26.get('pf'): return 1e9
    return abs(s23['win'] - TARGET['win23']) + abs(s26['win'] - TARGET['win26']) + 10 * abs(s23['trades'] - TARGET['n23']) / TARGET['n23'] + 5 * abs(s26['pf'] - TARGET['pf26'])


def main():
    D = prep(); rows = []; END = '2026-11-17'
    keys = list(GRID)
    for vals in itertools.product(*GRID.values()):
        p = dict(zip(keys, vals)); tr = sim(D, p)
        s23, s26 = stats(tr, '2023-01-01', END), stats(tr, '2026-01-01', END)
        rows.append(dict(p=p, score=round(score(s23, s26), 2), since_2023=s23, y2026=s26))
    rows.sort(key=lambda r: r['score'])
    for r in rows[:10]:
        tr = sim(D, r['p']); r['pre_2023_unseen'] = stats(tr, '2019-07-16', '2023-01-01'); r['all'] = stats(tr, '2019-07-16', END)
        trs = sim(D, r['p'], spread=True); r['with_spread'] = dict(since_2023=stats(trs, '2023-01-01', END), pre_2023=stats(trs, '2019-07-16', '2023-01-01'))
    best_win = max(rows, key=lambda r: r['since_2023'].get('win', 0) if r['since_2023'].get('trades', 0) >= 300 else 0)
    out = dict(target=TARGET, grid=GRID, combos=len(rows), top10=rows[:10], highest_win_since_2023_min300=best_win,
               reel_literal=next(r for r in rows if r['p'] == dict(range_start=555, last=930, first_only=False, body=0, entry='open', ema='m15', flat=None)))
    (H / 'FIT.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8')
    for r in rows[:10]:
        print(r['score'], r['p'], '\n   2023+', r['since_2023'], '\n   2026 ', r['y2026'], '\n   2019-22', r['pre_2023_unseen'], '\n   spread 2023+', r['with_spread']['since_2023'], flush=True)
    print('HIGHEST WIN (>=300 trades since 2023):', best_win['p'], best_win['since_2023'], best_win['y2026'])


if __name__ == '__main__':
    main()
