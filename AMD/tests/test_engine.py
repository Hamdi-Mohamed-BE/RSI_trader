from datetime import date, datetime, time, timezone

import pandas as pd

from amd_bot.config import Config
from amd_bot.engine import combine, resample_ohlc


def test_combine_uses_utc() -> None:
    value = combine(date(2026, 7, 30), time(13, 30))
    assert value == datetime(2026, 7, 30, 13, 30, tzinfo=timezone.utc)


def test_resample_ohlc() -> None:
    frame = pd.DataFrame(
        {
            "time": pd.date_range(
                "2026-07-30T13:30:00Z", periods=5, freq="min"
            ),
            "open": [1, 2, 3, 4, 5],
            "high": [2, 3, 4, 5, 6],
            "low": [0, 1, 2, 3, 4],
            "close": [1.5, 2.5, 3.5, 4.5, 5.5],
            "spread": [1, 1, 1, 1, 1],
            "tick_volume": [2, 2, 2, 2, 2],
        }
    )
    result = resample_ohlc(frame, "5min")
    assert len(result) == 1
    assert result.iloc[0]["high"] == 6
    assert result.iloc[0]["low"] == 0
