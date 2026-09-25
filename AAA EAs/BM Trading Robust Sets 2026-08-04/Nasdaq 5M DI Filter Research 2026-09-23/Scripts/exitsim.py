"""M5 bar exit simulator for Nasdaq 5M Candle Momentum.

Entry price/time/side come from the native MT5 ledger. Bars are Exness USTEC bid
bars from the connected demo account; shorts exit at ask = bid + bar spread.
If a bar touches both stop and target, the stop is assumed first (conservative).
"""
import numpy as np
import pandas as pd
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
POINT = 0.01
COMMISSION_R = 0.006  # native locked-year commission ≈ $192 / 256 trades ≈ 0.006R per trade


def prepare(m5):
    m5 = m5.copy()
    tr = np.maximum(m5.high - m5.low, np.maximum((m5.high - m5.close.shift()).abs(), (m5.low - m5.close.shift()).abs()))
    m5["atr14"] = tr.rolling(14).mean()
    m5["ny"] = m5.time.dt.tz_localize("UTC").dt.tz_convert(NY)
    m5["spr"] = m5.spread * POINT
    return m5.reset_index(drop=True)


def simulate(trade, m5, mode, rr=2.5, stop_atr=4.0, trail_after_r=0.0):
    """mode: 'fixed' (current), 'trail_tp' (candle trail + fixed TP), 'trail' (candle trail, no TP)."""
    d = 1 if trade.side == "buy" else -1
    entry = trade.entry_price
    ebar_open = trade.entry_time.floor("5min")
    i = int(np.searchsorted(m5.time.values, ebar_open.to_datetime64()))
    if i >= len(m5) or m5.time.iloc[i] != ebar_open:
        return None
    atr = m5.atr14.iloc[i - 1]  # signal bar (09:30) ATR, as the EA reads shift 1 at 09:35
    risk = stop_atr * atr
    sl = entry - d * risk
    tp = entry + d * rr * risk if mode in ("fixed", "trail_tp") else None
    day = m5.ny.iloc[i].date()
    j = i
    while j < len(m5):
        b = m5.iloc[j]
        ny = b.ny
        if ny.date() != day or (ny.hour * 60 + ny.minute) >= 15 * 60 + 55:
            px = b.open if d > 0 else b.open + b.spr  # flat at 15:55 NY (first bar at/after)
            if ny.date() != day:
                px = m5.close.iloc[j - 1] if d > 0 else m5.close.iloc[j - 1] + m5.spr.iloc[j - 1]
            return (d * (px - entry)) / risk, "session", j
        lo = b.low if d > 0 else b.low + b.spr
        hi = b.high if d > 0 else b.high + b.spr
        # stop check (gap-through fills at open)
        if d > 0 and lo <= sl:
            px = min(sl, b.open)
            return (px - entry) / risk, "stop", j
        if d < 0 and hi >= sl:
            px = max(sl, b.open + b.spr)
            return (entry - px) / risk, "stop", j
        if tp is not None:
            if d > 0 and hi >= tp:
                return (max(tp, b.open) - entry) / risk if b.open > tp and j > i else rr, "target", j
            if d < 0 and lo <= tp:
                return rr if not (b.open + b.spr < tp and j > i) else (entry - (b.open + b.spr)) / risk, "target", j
        # bar closed without exit: trail to this candle's extreme
        if mode in ("trail", "trail_tp"):
            fav = d * ((b.close if d > 0 else b.close + b.spr) - entry)
            if fav >= trail_after_r * risk:
                cand = b.low if d > 0 else b.high
                if d > 0 and cand > sl:
                    sl = cand
                if d < 0 and cand < sl:
                    sl = cand
        j += 1
    return None
