from __future__ import annotations

import pandas as pd


def ema(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(span=length, adjust=False).mean()


def rsi(close: pd.Series, length: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()
    avg_loss = loss.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()
    rs = avg_gain / avg_loss.mask(avg_loss == 0, float("nan"))
    return (100 - (100 / (1 + rs))).astype(float)


def atr(df: pd.DataFrame, length: int = 14) -> pd.Series:
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return true_range.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()


def pivot_low(series: pd.Series, pivot_len: int) -> pd.Series:
    window = pivot_len * 2 + 1
    lows = series.rolling(window=window, center=True).min()
    return series.eq(lows) & series.notna()


def pivot_high(series: pd.Series, pivot_len: int) -> pd.Series:
    window = pivot_len * 2 + 1
    highs = series.rolling(window=window, center=True).max()
    return series.eq(highs) & series.notna()
