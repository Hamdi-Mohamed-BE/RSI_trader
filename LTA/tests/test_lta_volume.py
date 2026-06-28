from __future__ import annotations

from datetime import datetime, timedelta
import os
import unittest

import numpy as np
import pandas as pd

from app.strategy_engine import (
    _candidate_levels,
    _fixed_range_segment,
    _profile_clock,
    _swing_segment,
    _volume_profile,
    detect_entry_confirmation,
)


def candles(
    start: datetime,
    count: int,
    minutes: int = 15,
    base: float = 100.0,
) -> pd.DataFrame:
    times = [start + timedelta(minutes=minutes * index) for index in range(count)]
    values = np.linspace(base, base + 1.0, count)
    return pd.DataFrame(
        {
            "time": times,
            "open": values,
            "high": values + 0.5,
            "low": values - 0.5,
            "close": values + 0.1,
            "volume": np.full(count, 100.0),
            "volume_source": ["tick_volume_proxy"] * count,
        }
    )


class LTAVolumeTests(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["MARKET_DATA_TIMEZONE"] = "UTC"
        os.environ["LTA_PROFILE_TIMEZONE"] = "America/New_York"

    def test_profile_distributes_bar_volume_across_range(self) -> None:
        frame = candles(datetime(2026, 6, 1), 12)
        frame["low"] = 90.0
        frame["high"] = 110.0
        frame["close"] = 109.5
        profile = _volume_profile(frame, bins=20)
        self.assertIsNotNone(profile)
        assert profile is not None
        self.assertLess(profile.poc, 109.5)
        self.assertLessEqual(profile.val, profile.poc)
        self.assertGreaterEqual(profile.vah, profile.poc)

    def test_value_area_is_contiguous_around_poc(self) -> None:
        frame = candles(datetime(2026, 6, 1), 30)
        frame.loc[:19, ["low", "high", "close", "volume"]] = [99.9, 100.1, 100.0, 300.0]
        frame.loc[20:, ["low", "high", "close", "volume"]] = [109.9, 110.1, 110.0, 40.0]
        profile = _volume_profile(frame, bins=40)
        self.assertIsNotNone(profile)
        assert profile is not None
        self.assertAlmostEqual(profile.poc, 100.0, delta=0.5)
        self.assertLess(profile.vah, 105.0)

    def test_futures_day_rolls_at_1800_new_york(self) -> None:
        frame = candles(datetime(2026, 6, 1, 21, 45), 3)
        clocked = _profile_clock(frame)
        self.assertEqual(str(clocked["_trading_day"].iloc[0]), "2026-06-01")
        self.assertEqual(str(clocked["_trading_day"].iloc[1]), "2026-06-02")

    def test_fixed_range_requires_consolidation_then_breakout(self) -> None:
        frame = candles(datetime(2026, 6, 1), 60)
        cycle = np.array([100.0, 101.0, 100.4, 99.6, 100.2, 100.8])
        closes = np.resize(cycle, 48)
        frame.loc[:47, "close"] = closes
        frame.loc[:47, "open"] = closes
        frame.loc[:47, "high"] = closes + 0.25
        frame.loc[:47, "low"] = closes - 0.25
        breakout = np.linspace(103.0, 108.0, 12)
        frame.loc[48:, "open"] = breakout
        frame.loc[48:, "close"] = breakout
        frame.loc[48:, "high"] = breakout + 0.3
        frame.loc[48:, "low"] = breakout - 0.3
        detected = _fixed_range_segment(frame)
        self.assertIsNotNone(detected)
        assert detected is not None
        segment, metadata = detected
        self.assertLess(float(segment["high"].max()), 103.0)
        self.assertEqual(metadata["breakout_direction"], "BUY")

    def test_swing_profile_uses_wick_extremes(self) -> None:
        frame = candles(datetime(2026, 6, 1), 80)
        frame["open"] = 100.0
        frame["close"] = 100.0
        frame["high"] = 100.5
        frame["low"] = 99.5
        frame.loc[20, "low"] = 94.0
        frame.loc[50, "high"] = 112.0
        detected = _swing_segment(frame)
        self.assertIsNotNone(detected)
        assert detected is not None
        _, metadata = detected
        self.assertEqual(metadata["swing_low"], 94.0)
        self.assertEqual(metadata["swing_high"], 112.0)

    def test_calendar_profiles_include_book_week_and_day_levels(self) -> None:
        frame = candles(datetime(2026, 5, 3, 22, 0), 24 * 4 * 26, base=100.0)
        levels = _candidate_levels(frame)
        prefixes = {str(level["key_level"]).split()[0] for level in levels}
        self.assertTrue({"PD", "EPD", "PW", "EPW", "CW"}.issubset(prefixes))

    def test_em4_requires_high_volume_three_candle_continuation(self) -> None:
        frame = candles(datetime(2026, 6, 1), 50)
        frame["open"] = 101.0
        frame["close"] = 101.1
        frame["high"] = 101.3
        frame["low"] = 100.8
        frame["volume"] = 100.0
        frame.loc[47, ["open", "high", "low", "close", "volume"]] = [100.2, 100.6, 99.7, 100.4, 400.0]
        frame.loc[48, ["open", "high", "low", "close", "volume"]] = [100.4, 100.7, 100.1, 100.35, 450.0]
        frame.loc[49, ["open", "high", "low", "close", "volume"]] = [100.3, 101.2, 100.2, 101.1, 500.0]
        level = {"price": 100.0, "tolerance": 0.35}
        result = detect_entry_confirmation(frame, level=level, direction="BUY")
        self.assertTrue(result["confirmed"])
        self.assertIn("Entry Model 4", str(result["model"]))


if __name__ == "__main__":
    unittest.main()
