from __future__ import annotations

from zoneinfo import ZoneInfo

import pandas as pd


NEW_YORK = ZoneInfo("America/New_York")


def with_session_keys(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    utc = pd.to_datetime(result["time"], utc=True)
    ny = utc.dt.tz_convert(NEW_YORK)
    shifted = ny + pd.Timedelta(hours=6)
    result["session_day"] = shifted.dt.date
    iso = shifted.dt.isocalendar()
    result["session_week"] = (
        iso["year"].astype(str) + "-W" + iso["week"].astype(str).str.zfill(2)
    )
    result["ny_hour"] = ny.dt.hour
    return result


def resample_ohlcv(frame: pd.DataFrame, rule: str = "1h") -> pd.DataFrame:
    indexed = frame.copy().set_index(pd.to_datetime(frame["time"], utc=True))
    volume_column = "real_volume"
    if volume_column not in indexed or indexed[volume_column].sum() <= 0:
        volume_column = "tick_volume"
    aggregation = {
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        volume_column: "sum",
        "spread": "median",
    }
    result = indexed.resample(rule, label="right", closed="left").agg(aggregation)
    result = result.dropna(subset=["open", "high", "low", "close"])
    result = result.rename(columns={volume_column: "volume"}).reset_index()
    if result.columns[0] != "time":
        result = result.rename(columns={result.columns[0]: "time"})
    return with_session_keys(result)


def timeframe_rule(timeframe: str) -> str:
    mapping = {
        "M5": "5min",
        "M10": "10min",
        "M15": "15min",
        "M30": "30min",
        "H1": "1h",
        "H2": "2h",
        "H4": "4h",
    }
    try:
        return mapping[timeframe.upper()]
    except KeyError as exc:
        raise ValueError(f"Unsupported timeframe {timeframe}") from exc
