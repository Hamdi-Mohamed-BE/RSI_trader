from __future__ import annotations

import numpy as np
import pandas as pd


def enrich_structure(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    previous_close = result["close"].shift(1)
    true_range = pd.concat(
        [
            result["high"] - result["low"],
            (result["high"] - previous_close).abs(),
            (result["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    result["atr"] = true_range.rolling(14, min_periods=14).mean()
    result["ema20"] = result["close"].ewm(span=20, adjust=False).mean()
    result["ema50"] = result["close"].ewm(span=50, adjust=False).mean()
    result["prior_high_20"] = result["high"].rolling(20).max().shift(1)
    result["prior_low_20"] = result["low"].rolling(20).min().shift(1)
    result["median_range_20"] = (
        (result["high"] - result["low"]).rolling(20).median().shift(1)
    )
    result["trend"] = np.select(
        [
            (result["ema20"] > result["ema50"])
            & (result["ema20"].diff() > 0),
            (result["ema20"] < result["ema50"])
            & (result["ema20"].diff() < 0),
        ],
        ["bullish", "bearish"],
        default="balanced",
    )
    result["structure_break"] = np.select(
        [
            result["close"] > result["prior_high_20"],
            result["close"] < result["prior_low_20"],
        ],
        ["bullish", "bearish"],
        default="none",
    )
    return result


def candle_parts(row: pd.Series) -> tuple[float, float, float]:
    body = abs(float(row["close"]) - float(row["open"]))
    upper = float(row["high"]) - max(float(row["open"]), float(row["close"]))
    lower = min(float(row["open"]), float(row["close"])) - float(row["low"])
    return body, max(upper, 0.0), max(lower, 0.0)


def direction_bias(row: pd.Series) -> str:
    return str(row.get("trend", "balanced"))

