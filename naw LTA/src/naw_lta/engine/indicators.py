import numpy as np
import pandas as pd


def atr(frame: pd.DataFrame, period: int = 14) -> pd.Series:
    previous_close = frame["close"].shift(1)
    true_range = pd.concat(
        [
            frame["high"] - frame["low"],
            (frame["high"] - previous_close).abs(),
            (frame["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.ewm(alpha=1 / period, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    change = series.diff()
    gain = change.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-change.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    relative_strength = gain / loss.replace(0, np.nan)
    return (100 - (100 / (1 + relative_strength))).fillna(50.0)


def adx(frame: pd.DataFrame, period: int = 14) -> pd.Series:
    up = frame["high"].diff()
    down = -frame["low"].diff()
    plus_dm = up.where((up > down) & (up > 0), 0.0)
    minus_dm = down.where((down > up) & (down > 0), 0.0)
    average_range = atr(frame, period).replace(0, np.nan)
    plus_di = 100 * plus_dm.ewm(alpha=1 / period, adjust=False).mean() / average_range
    minus_di = 100 * minus_dm.ewm(alpha=1 / period, adjust=False).mean() / average_range
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return dx.ewm(alpha=1 / period, adjust=False).mean().fillna(0.0)


def resample_ohlcv(frame: pd.DataFrame, minutes: int) -> pd.DataFrame:
    rules = {
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }
    available = {key: value for key, value in rules.items() if key in frame.columns}
    result = frame.resample(f"{minutes}min", label="right", closed="right").agg(available)
    return result.dropna(subset=["open", "high", "low", "close"])

