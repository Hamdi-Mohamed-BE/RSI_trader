"""Causal features for Nasdaq 5M Candle Momentum signals (USTEC, Exness demo bars).

Every feature uses only bars fully closed at the moment the EA decides (open of
the 09:35 NY M5 bar). ADX follows MetaTrader 5's built-in iADX (ADX.mq5):
+DI/-DI and ADX are exponential moving averages with alpha = 2/(period+1).
"""
import numpy as np
import pandas as pd
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")


def mt5_adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    h, l, c = df.high.values, df.low.values, df.close.values
    n = len(df)
    pdm = np.zeros(n); mdm = np.zeros(n); trr = np.zeros(n)
    for i in range(1, n):
        up = h[i] - h[i - 1]
        dn = l[i - 1] - l[i]
        if up < 0: up = 0.0
        if dn < 0: dn = 0.0
        if up > dn: dn = 0.0
        elif dn > up: up = 0.0
        else: up = dn = 0.0
        tr = max(h[i], c[i - 1]) - min(l[i], c[i - 1])
        trr[i] = tr
        if tr > 0:
            pdm[i] = 100.0 * up / tr
            mdm[i] = 100.0 * dn / tr
    a = 2.0 / (period + 1)
    pdi = pd.Series(pdm).ewm(alpha=a, adjust=False).mean().values
    mdi = pd.Series(mdm).ewm(alpha=a, adjust=False).mean().values
    s = pdi + mdi
    dx = np.where(s > 0, 100.0 * np.abs(pdi - mdi) / np.where(s > 0, s, 1), 0.0)
    adx = pd.Series(dx).ewm(alpha=a, adjust=False).mean().values
    return pd.DataFrame({"adx": adx, "pdi": pdi, "mdi": mdi}, index=df.index)


def last_closed(df: pd.DataFrame, bar_seconds: int, decision_utc: pd.Timestamp) -> int:
    """Index of the last bar whose close time <= decision time."""
    closes = df.time + pd.to_timedelta(bar_seconds, unit="s")
    idx = np.searchsorted(closes.values, decision_utc.to_datetime64(), side="right") - 1
    return int(idx)


def build(m5, h1, d1, trades):
    for df in (m5, h1, d1):
        df[["adx", "pdi", "mdi"]] = mt5_adx(df)
    rows = []
    for _, t in trades.iterrows():
        decision = t.entry_time.floor("5min")  # open of the 09:35 bar == close of 09:30 signal bar
        r = {"date": t.date}
        for name, df, sec in (("m5", m5, 300), ("h1", h1, 3600), ("d1", d1, 86400)):
            i = last_closed(df, sec, decision)
            r[f"adx_{name}"] = df.adx.iloc[i]
            r[f"adx_{name}_slope3"] = df.adx.iloc[i] - df.adx.iloc[i - 3]
            r[f"di_{name}"] = np.sign(df.pdi.iloc[i] - df.mdi.iloc[i])
            r[f"bar_{name}_close_time"] = df.time.iloc[i] + pd.to_timedelta(sec, unit="s")
        rows.append(r)
    return pd.DataFrame(rows)
