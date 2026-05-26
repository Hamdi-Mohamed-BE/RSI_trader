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


def adx(df: pd.DataFrame, length: int = 14) -> tuple[pd.Series, pd.Series, pd.Series]:
    high = df["high"]
    low = df["low"]
    close = df["close"]
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)
    tr = pd.concat(
        [
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr_val = tr.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1 / length, adjust=False, min_periods=length).mean() / atr_val
    minus_di = 100 * minus_dm.ewm(alpha=1 / length, adjust=False, min_periods=length).mean() / atr_val
    dx = ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, float("nan"))) * 100
    adx_val = dx.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()
    return plus_di.astype(float), minus_di.astype(float), adx_val.astype(float)


def crossed_over(fast: pd.Series, slow: pd.Series | float, index: int) -> bool:
    if index < 1:
        return False
    prev_fast = float(fast.iloc[index - 1])
    curr_fast = float(fast.iloc[index])
    if isinstance(slow, (int, float)):
        prev_slow = curr_slow = float(slow)
    else:
        prev_slow = float(slow.iloc[index - 1])
        curr_slow = float(slow.iloc[index])
    return prev_fast <= prev_slow and curr_fast > curr_slow


def crossed_under(fast: pd.Series, slow: pd.Series | float, index: int) -> bool:
    if index < 1:
        return False
    prev_fast = float(fast.iloc[index - 1])
    curr_fast = float(fast.iloc[index])
    if isinstance(slow, (int, float)):
        prev_slow = curr_slow = float(slow)
    else:
        prev_slow = float(slow.iloc[index - 1])
        curr_slow = float(slow.iloc[index])
    return prev_fast >= prev_slow and curr_fast < curr_slow


def pivot_low(series: pd.Series, pivot_len: int) -> pd.Series:
    window = pivot_len * 2 + 1
    lows = series.rolling(window=window, center=True).min()
    return series.eq(lows) & series.notna()


def pivot_high(series: pd.Series, pivot_len: int) -> pd.Series:
    window = pivot_len * 2 + 1
    highs = series.rolling(window=window, center=True).max()
    return series.eq(highs) & series.notna()
