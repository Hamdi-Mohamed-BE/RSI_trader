"""Noise Band replay engine (PLAN.md). Exness M1 bid bars + bar spread -> checkpoint bars / ATR / sigma band -> numba trade loop.
Data: ../Noise Band Raw 2026-11-11/bars/<SYM>_m1.npy (t, o, h, l, c, tick volume, spread points). Server = UTC.
Run with: uv run --with numba python <script>"""
import json, gzip
from datetime import datetime, timedelta, timezone
from pathlib import Path
import numpy as np
import numba as nb

H = Path(__file__).resolve().parent; RAW = H.parent / 'Noise Band Raw 2026-11-11'
POINT = {'USTEC': 0.01, 'US500': 0.01, 'DE30': 0.01}
CLOCK = {'USTEC': ('NY', 570, 960), 'US500': ('NY', 570, 960), 'DE30': ('FRA', 540, 1050)}   # clock, open minute, close minute
KMAX = 32


def _nth_sun(y, m, n):
    d = datetime(y, m, 1, tzinfo=timezone.utc)
    while d.weekday() != 6: d += timedelta(days=1)
    return d + timedelta(days=7 * (n - 1))


def _last_sun(y, m):
    d = datetime(y, m, 31, tzinfo=timezone.utc)
    while d.weekday() != 6: d -= timedelta(days=1)
    return d


def local_offset(t, clock):
    """seconds to ADD to UTC epochs to get the market's local clock (vectorised)."""
    yrs = np.arange(2018, 2028); off = np.zeros(len(t), np.int64)
    for y in yrs:
        if clock == 'NY':
            a = int((_nth_sun(y, 3, 2) + timedelta(hours=7)).timestamp()); b = int((_nth_sun(y, 11, 1) + timedelta(hours=6)).timestamp()); s, w = -4 * 3600, -5 * 3600
        else:
            a = int((_last_sun(y, 3) + timedelta(hours=1)).timestamp()); b = int((_last_sun(y, 10) + timedelta(hours=1)).timestamp()); s, w = 2 * 3600, 1 * 3600
        y0 = int(datetime(y, 1, 1, tzinfo=timezone.utc).timestamp()); y1 = int(datetime(y + 1, 1, 1, tzinfo=timezone.utc).timestamp())
        k = (t >= y0) & (t < y1); off[k] = np.where((t[k] >= a) & (t[k] < b), s, w)
    return off


class Data:
    """Per asset: M1 arrays + per-day checkpoint tables for one timeframe (tf minutes, anchored to the cash open)."""
    def __init__(self, sym, tf, comm_price):
        m = np.load(RAW / 'bars' / f'{sym}_m1.npy'); self.sym = sym; self.tf = tf
        self.t = m[:, 0].astype(np.int64); self.o = m[:, 1].copy(); self.h = m[:, 2].copy(); self.l = m[:, 3].copy(); self.c = m[:, 4].copy()
        self.spr = m[:, 6] * POINT[sym]; self.comm = comm_price
        clock, om, cm = CLOCK[sym]; self.open_min, self.close_min = om, cm
        loc = self.t + local_offset(self.t, clock); self.loc = loc
        lday = loc // 86400; lmin = (loc % 86400) // 60
        # ATR(14) = SMA of true range on clock bars anchored so that the open is a boundary
        anchor = (om * 60) % (tf * 60)
        key = (loc - anchor) // (tf * 60)
        first = np.r_[True, key[1:] != key[:-1]]; idx = np.flatnonzero(first); end = np.r_[idx[1:], len(key)]
        bo = self.o[idx]; bh = np.maximum.reduceat(self.h, idx); bl = np.minimum.reduceat(self.l, idx); bc = self.c[end - 1]
        pc = np.r_[bc[0], bc[:-1]]; tr = np.maximum(bh, pc) - np.minimum(bl, pc)
        atr = np.convolve(tr, np.ones(14) / 14, 'full')[:len(tr)]; atr[:13] = np.nan
        bar_end_loc = (key[idx] + 1) * tf * 60 + anchor          # local epoch at which each bar closes
        # daily tables
        days = np.unique(lday); D = len(days); self.days = days
        self.O = np.full(D, np.nan); self.PC = np.full(D, np.nan); self.C = np.full((D, KMAX), np.nan); self.ATR = np.full((D, KMAX), np.nan)
        self.EI = np.full((D, KMAX), -1, np.int64); self.FLAT = np.full((D, 4), -1, np.int64); self.LAST = np.full(D, -1, np.int64)
        self.DOW = np.array([datetime.fromtimestamp(int(d) * 86400, timezone.utc).weekday() for d in days]); self.DATE = [datetime.fromtimestamp(int(d) * 86400, timezone.utc).strftime('%Y-%m-%d') for d in days]
        di = np.searchsorted(days, lday); starts = np.searchsorted(lday, days); ends = np.r_[starts[1:], len(lday)]
        bar_pos = np.searchsorted(bar_end_loc, loc, 'right')    # index of the clock bar containing each M1 (bars are sorted)
        for d in range(D):
            a, b = starts[d], ends[d]; mm = lmin[a:b]
            if self.DOW[d] >= 5: continue
            j = np.searchsorted(mm, om)
            if j >= len(mm) or mm[j] != om: continue
            i0 = a + j; self.O[d] = self.o[i0]
            k = np.searchsorted(mm, cm) - 1                     # last M1 before the cash close
            if k >= 0: self.LAST[d] = a + k
            for K in range(1, KMAX):
                tmin = om + K * tf
                if tmin > cm: break
                e = np.searchsorted(mm, tmin)
                if e == 0: continue
                ci = a + e - 1                                    # last M1 before the checkpoint
                if lmin[ci] < tmin - tf: continue                  # no data inside that checkpoint bar
                self.C[d, K] = self.c[ci]
                bi = bar_pos[ci]                                   # the clock bar that closes at the checkpoint
                if bi < len(atr): self.ATR[d, K] = atr[bi]
                if e < len(mm): self.EI[d, K] = a + e
            for f, fm in enumerate((cm - 5, cm - 60, cm - 120, cm - 240)):
                e = np.searchsorted(mm, fm)
                self.FLAT[d, f] = a + e if e < len(mm) else (self.LAST[d] if self.LAST[d] >= 0 else -1)
        ok = ~np.isnan(self.O)
        prev = np.flatnonzero(ok)
        for n in range(1, len(prev)):
            d, p = prev[n], prev[n - 1]
            if self.LAST[p] >= 0: self.PC[d] = self.c[self.LAST[p]]
        # sigma band (paper): 14-day mean of |C_K / O - 1| over previous valid days
        mv = np.abs(self.C / self.O[:, None] - 1.0); self.SIG = np.full((D, KMAX), np.nan)
        hist = []
        for d in prev:
            if len(hist) >= 14: self.SIG[d] = np.nanmean(np.array(hist[-14:]), axis=0)
            hist.append(mv[d])
        # daily filters: SMA20 of daily closes (prev day known at the open), D1 ATR14 vs its 100-day median
        dc = np.array([self.c[self.LAST[d]] if self.LAST[d] >= 0 else np.nan for d in range(D)])
        self.TREND = np.zeros(D, np.int64); self.VOLHI = np.zeros(D, np.int64)
        closes = []; trs = []; atrs = []
        for n, d in enumerate(prev):
            if len(closes) >= 20:
                sma = np.mean(closes[-20:]); self.TREND[d] = 1 if closes[-1] > sma else -1
            if len(atrs) >= 100:
                self.VOLHI[d] = 1 if atrs[-1] > np.median(atrs[-100:]) else -1
            if self.LAST[d] >= 0:
                lo_ = self.l[starts[d]:self.LAST[d] + 1].min(); hi_ = self.h[starts[d]:self.LAST[d] + 1].max()
                tr_ = hi_ - lo_ if not closes else max(hi_, closes[-1]) - min(lo_, closes[-1])
                closes.append(dc[d]); trs.append(tr_)
                if len(trs) >= 14: atrs.append(np.mean(trs[-14:]))
        self.VALID = ok


@nb.njit(cache=True)
def _run(o, h, l, spr, comm, O, PC, C, ATR, SIG, EI, FLAT, band, k, Kfirst, Klast, confirm, stop_mode, stop_mult, be_trig, trail_mult, trail_start, target_r,
         time_bars, flat_col, max_trades, dir_mask, day_ok, trend, use_trend, out):
    n = 0; D = O.shape[0]
    for d in range(D):
        if not day_ok[d] or np.isnan(O[d]): continue
        trades = 0; K = Kfirst; last_dir = 0; streak = 0
        fl = FLAT[d, flat_col]
        if fl < 0: continue
        while K <= Klast and trades < max_trades:
            c = C[d, K]; a = ATR[d, K]
            if np.isnan(c) or np.isnan(a) or a <= 0 or EI[d, K] < 0 or EI[d, K] >= fl:
                K += 1; continue
            if band == 0:
                up = O[d] + k * np.sqrt(K) * a; lo = O[d] - k * np.sqrt(K) * a
            else:
                s = SIG[d, K]
                if np.isnan(s) or np.isnan(PC[d]): K += 1; continue
                up = max(O[d], PC[d]) * (1 + k * s); lo = min(O[d], PC[d]) * (1 - k * s)
            sgn = 1 if c > up else (-1 if c < lo else 0)
            if sgn != 0 and sgn == last_dir: streak += 1
            elif sgn != 0: streak = 1
            else: streak = 0
            last_dir = sgn
            if sgn == 0 or streak < confirm: K += 1; continue
            if (sgn > 0 and (dir_mask & 1) == 0) or (sgn < 0 and (dir_mask & 2) == 0): K += 1; continue
            if use_trend and trend[d] != sgn: K += 1; continue
            ei = EI[d, K]
            entry = o[ei] + (spr[ei] if sgn > 0 else 0.0)
            if stop_mode == 0: dist = stop_mult * a
            else: dist = max(abs(entry - (up if sgn > 0 else lo)), 0.25 * a)
            stop = entry - sgn * dist; best = entry
            tgt = entry + sgn * target_r * dist if target_r > 0 else 0.0
            end = fl if time_bars <= 0 else min(fl, ei + time_bars)
            ex = np.nan; xi = end
            for i in range(ei, end):
                if sgn > 0:
                    if l[i] <= stop: ex = min(stop, o[i]) if i > ei else stop; xi = i; break
                    if target_r > 0 and h[i] >= tgt: ex = max(tgt, o[i]) if i > ei else tgt; xi = i; break
                    if h[i] > best: best = h[i]
                    prof = best - entry
                else:
                    ah = h[i] + spr[i]; al = l[i] + spr[i]; ao = o[i] + spr[i]
                    if ah >= stop: ex = max(stop, ao) if i > ei else stop; xi = i; break
                    if target_r > 0 and al <= tgt: ex = min(tgt, ao) if i > ei else tgt; xi = i; break
                    if al < best: best = al
                    prof = entry - best
                if be_trig > 0 and prof >= be_trig * dist:
                    if sgn > 0 and entry > stop: stop = entry
                    if sgn < 0 and entry < stop: stop = entry
                if trail_mult > 0 and prof >= trail_start * dist:
                    want = best - sgn * trail_mult * a
                    if sgn > 0 and want > stop: stop = want
                    if sgn < 0 and want < stop: stop = want
            if np.isnan(ex):
                ex = o[end] + (spr[end] if sgn < 0 else 0.0) if end < len(o) else entry
            r = (ex - entry) * sgn / dist - comm / dist
            out[n, 0] = d; out[n, 1] = K; out[n, 2] = sgn; out[n, 3] = r; out[n, 4] = ei; out[n, 5] = xi; out[n, 6] = dist
            n += 1; trades += 1
            # next checkpoint after the exit
            nk = K + 1
            while nk <= Klast and EI[d, nk] >= 0 and EI[d, nk] <= xi: nk += 1
            K = nk; last_dir = 0; streak = 0
    return n


DEFAULT = dict(band=0, k=1.4, first_min=30, last_off=330, confirm=1, stop_mode=0, stop_mult=2.0, be=0.0, trail=2.0, trail_start=1.0, target=0.0, time_h=0.0, flat=0,
               direction='both', trend=False, vol='any', dow='none', max_trades=1)


def run(D, cfg):
    p = dict(DEFAULT, **cfg); tf = D.tf
    Kfirst = max(1, -(-int(p['first_min']) // tf)); Klast = int(p['last_off']) // tf   # last checkpoint = open + last_off minutes (US 330 = 15:00 NY)
    dm = {'both': 3, 'long': 1, 'short': 2}[p['direction']]
    ok = D.VALID.copy()
    if p['vol'] == 'high': ok &= D.VOLHI == 1
    if p['vol'] == 'low': ok &= D.VOLHI == -1
    if p['dow'] in ('mon', 'monfri'): ok &= D.DOW != 0
    if p['dow'] in ('fri', 'monfri'): ok &= D.DOW != 4
    out = np.zeros((len(D.O) * max(1, p['max_trades']), 7))
    n = _run(D.o, D.h, D.l, D.spr, D.comm, D.O, D.PC, D.C, D.ATR, D.SIG, D.EI, D.FLAT, int(p['band']), float(p['k']), Kfirst, int(Klast), int(p['confirm']),
             int(p['stop_mode']), float(p['stop_mult']), float(p['be']), float(p['trail']), float(p['trail_start']), float(p['target']), int(p['time_h'] * 60),
             int(p['flat']), int(p['max_trades']), dm, ok, D.TREND, bool(p['trend']), out)
    return out[:n]
