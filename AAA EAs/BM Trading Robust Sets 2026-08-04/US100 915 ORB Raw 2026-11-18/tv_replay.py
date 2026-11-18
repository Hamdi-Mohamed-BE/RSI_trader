"""Addendum 2 (owner 2026-11-18: "try the TradingView-style fills to see if we match 72%").
Python replay of MAIN's day logic on the exported USTEC bars (bars/, server time = UTC), signals and EMA 200 on M15 closes, one trade a day,
hold to SL / TP, one position at a time. Versions:
  M1_SPREAD   entry at the next M15 open + recorded spread (buy at ask), exits on bid / ask through M1 bars  -> must look like the native MAIN (check)
  TV_MAG      no spread, exits through M1 bars (TradingView with bar magnifier)                                 -> spread effect
  TV          no spread, exits on the M15 bar with TradingView's OHLC rule (open nearer the high -> O-H-L-C, else O-L-H-C), entry bar included
  TV_FIRST    TV + only the day's FIRST breakout counts (if it fails the EMA filter, no trade that day)
  *_CLOSE     stop / target set at signal time from the signal bar CLOSE (typical Pine strategy.exit), not from the fill
R = net / initial risk (fill to stop); no commission / swap anywhere (TradingView default). python tv_replay.py -> TV_RESULTS.json"""
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

H = Path(__file__).resolve().parent; POINT = 0.01


def nth_sunday(y, m, n):
    d = datetime(y, m, 1, tzinfo=timezone.utc); d += timedelta(days=(6 - d.weekday()) % 7); return d + timedelta(days=7 * (n - 1))


DST = {}


def ny(ts):
    u = datetime.fromtimestamp(int(ts), timezone.utc)
    if u.year not in DST: DST[u.year] = (nth_sunday(u.year, 3, 2) + timedelta(hours=7), nth_sunday(u.year, 11, 1) + timedelta(hours=6))
    on, off = DST[u.year]; return u - timedelta(hours=5) + (timedelta(hours=1) if on <= u < off else timedelta(0))


def load(name):
    z = np.load(H / 'bars' / f'USTEC_{name}.npz'); return {k: z[k] for k in z.files}


def ema(c, n=200):
    out = np.empty_like(c); a = 2 / (n + 1); out[0] = c[0]
    for i in range(1, len(c)): out[i] = a * c[i] + (1 - a) * out[i - 1]
    return out


def tv_bar(o, h, l, side, sl, tp):
    """TradingView broker emulator on one bar for an open position. Returns exit price or None."""
    if side > 0:
        if o <= sl: return sl if False else o
        if o >= tp: return o
        first_high = (h - o) < (o - l)
        seq = (('h', h), ('l', l)) if first_high else (('l', l), ('h', h))
        for k, v in seq:
            if k == 'h' and v >= tp: return tp
            if k == 'l' and v <= sl: return sl
    else:
        if o >= sl: return o
        if o <= tp: return o
        first_high = (h - o) < (o - l)
        seq = (('h', h), ('l', l)) if first_high else (('l', l), ('h', h))
        for k, v in seq:
            if k == 'l' and v <= tp: return tp
            if k == 'h' and v >= sl: return sl
    return None


def run(m15, m1, version):
    t, o, h, l, c = m15['time'], m15['open'], m15['high'], m15['low'], m15['close']; e = ema(c)
    sp15 = m15['spread'] * POINT
    i1 = {int(x): k for k, x in enumerate(m1['time'])}
    t1, o1, h1, l1, sp1 = m1['time'], m1['open'], m1['high'], m1['low'], m1['spread'] * POINT
    spread = version.startswith('M1_SPREAD'); magnifier = version.startswith(('M1_SPREAD', 'TV_MAG')); first_only = version.startswith('TV_FIRST'); from_close = version.endswith('_CLOSE')
    nyt = [ny(x) for x in t]; trades = []; day = None; done = False; rng = None; first_seen = False; pos = None
    i = 0; n = len(t)
    while i < n - 1:
        d = nyt[i]; key = d.date(); mins = d.hour * 60 + d.minute
        if key != day: day = key; done = False; rng = None; first_seen = False
        # manage an open position on bar i (exits evaluated bar by bar)
        if pos is not None:
            side, sl, tp, entry, risk, opened = pos
            if magnifier:
                k0 = i1.get(int(t[i])); xp = None
                if k0 is not None:
                    k = k0
                    while k < len(t1) and t1[k] < t[i] + 900:
                        bo, bh, bl = o1[k], h1[k], l1[k]
                        if spread and side < 0: bo, bh, bl = bo + sp1[k], bh + sp1[k], bl + sp1[k]   # short exits on ask
                        xp = tv_bar(bo, bh, bl, side, sl, tp)
                        if xp is not None: break
                        k += 1
            else:
                xp = tv_bar(o[i], h[i], l[i], side, sl, tp)
            if xp is not None:
                trades.append(dict(o=opened, c=nyt[i].isoformat(), side=side, r=side * (xp - entry) / risk)); pos = None
        if mins == 555:                                                     # the 09:15 NY bar closes at i: range
            rng = (h[i], l[i]) if h[i] - l[i] >= 1.0 else None
            i += 1; continue
        if rng is None or done or pos is not None or mins < 570 or mins > 930 or nyt[i + 1].date() != key:
            i += 1; continue
        hi, lo = rng; up, dn = c[i] > hi, c[i] < lo
        if not (up or dn): i += 1; continue
        side = 1 if up else -1
        if first_only and first_seen: i += 1; continue
        first_seen = True
        if (side > 0 and c[i] <= e[i]) or (side < 0 and c[i] >= e[i]): i += 1; continue
        stop = l[i] if side > 0 else h[i]
        entry = o[i + 1] + (sp15[i + 1] if (spread and side > 0) else 0.0)        # next bar open; buy at ask with spread
        base = c[i] if from_close else entry
        if (side > 0 and stop >= (entry if not spread else o[i + 1])) or (side < 0 and stop <= entry): i += 1; continue
        risk = abs(base - stop); tp = base + side * 0.5 * risk; risk_fill = abs(entry - stop)
        pos = (side, stop, tp, entry, risk_fill, nyt[i + 1].isoformat()); done = True
        i += 1                                                               # exits start on the entry bar (i+1)
    return trades


def stats(x, a, b):
    x = [r for r in x if a <= r['o'][:10] < b]
    if not x: return {}
    gw = sum(r['r'] for r in x if r['r'] > 0); gl = -sum(r['r'] for r in x if r['r'] < 0)
    months = (datetime.fromisoformat(b) - datetime.fromisoformat(a)).days / 30.4375
    return dict(trades=len(x), per_month=round(len(x) / months, 1), per_day=round(len(x) / months / 21, 2), win=round(100 * sum(1 for r in x if r['r'] > 0) / len(x), 1),
                pf=round(gw / gl, 2) if gl else None, total_r=round(sum(r['r'] for r in x), 1), avg_r=round(sum(r['r'] for r in x) / len(x), 3))


def main():
    m15, m1 = load('M15'), load('M1'); out = {}
    for v in ('M1_SPREAD', 'TV_MAG', 'TV', 'TV_FIRST', 'TV_CLOSE', 'TV_FIRST_CLOSE'):
        tr = run(m15, m1, v)
        out[v] = dict(since_2023=stats(tr, '2023-01-01', '2026-11-17'), y2026=stats(tr, '2026-01-01', '2026-11-17'),
                      y2023=stats(tr, '2023-01-01', '2024-01-01'), y2024=stats(tr, '2024-01-01', '2025-01-01'), y2025=stats(tr, '2025-01-01', '2026-01-01'))
        print(v, out[v]['since_2023'], '| 2026', out[v]['y2026'], flush=True)
    (H / 'TV_RESULTS.json').write_text(json.dumps(out, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
