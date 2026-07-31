from __future__ import annotations

import pandas as pd

from lta_system.profiles import (
    build_completed_profile_maps,
    profiles_for_row,
    volume_profile,
)
from lta_system.sessions import resample_ohlcv


def _m1(start: str, periods: int) -> pd.DataFrame:
    time = pd.date_range(start, periods=periods, freq="1min", tz="UTC")
    base = pd.Series(range(periods), dtype=float) * 0.01 + 100.0
    return pd.DataFrame(
        {
            "time": time,
            "open": base,
            "high": base + 0.10,
            "low": base - 0.10,
            "close": base + 0.02,
            "tick_volume": 10,
            "real_volume": 0,
            "spread": 2,
        }
    )


def test_profile_orders_value_area() -> None:
    profile = volume_profile(_m1("2026-01-01", 120), "TEST", rows=32)
    assert profile.low < profile.val <= profile.poc <= profile.vah < profile.high
    assert profile.source == "TICK_VOLUME_APPROX"


def test_current_day_data_is_not_used_for_previous_day_profile() -> None:
    frame = _m1("2026-01-01", 60 * 72)
    daily, weekly = build_completed_profile_maps(frame, 32, 70)
    h1 = resample_ohlcv(frame, "1h")
    row = h1.iloc[-2]
    profiles = profiles_for_row(row, daily, weekly)
    assert profiles
    assert all(profile.end < row["time"] for profile in profiles)

