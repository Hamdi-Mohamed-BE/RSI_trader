from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

import numpy as np

from weekend_direction_model import (
    MarketSeries,
    build_weekend_dataset,
    expanding_folds,
    feature_vector_at,
    find_weekend_windows,
)


def synthetic_series(days: int = 24) -> MarketSeries:
    start = datetime(2026, 1, 5, tzinfo=timezone.utc)
    times = []
    moment = start
    while len(times) < days * 24 * 60:
        if moment.weekday() < 5:
            times.append(int(moment.timestamp()))
        moment += timedelta(minutes=1)
    time = np.asarray(times, dtype=np.int64)
    close = 2000.0 + np.arange(len(time), dtype=float) * 0.001
    return MarketSeries(
        symbol="XAUUSD",
        point=0.01,
        timeframe_seconds=60,
        time=time,
        open=close - 0.01,
        high=close + 0.05,
        low=close - 0.05,
        close=close,
        tick_volume=np.full(len(time), 100.0),
        spread=np.full(len(time), 10.0),
    )


class WeekendDirectionTests(unittest.TestCase):
    def test_weekend_windows_are_detected(self) -> None:
        series = synthetic_series()
        windows = find_weekend_windows(series.time)
        self.assertGreaterEqual(len(windows), 3)
        for close_index, reopen_index in windows:
            before = datetime.fromtimestamp(int(series.time[close_index]), timezone.utc)
            after = datetime.fromtimestamp(int(series.time[reopen_index]), timezone.utc)
            self.assertEqual(before.weekday(), 4)
            self.assertEqual(after.weekday(), 0)

    def test_features_do_not_use_bars_after_cutoff(self) -> None:
        original = synthetic_series()
        cutoff = 10_000
        expected = feature_vector_at(original, cutoff, {}, [])
        changed_close = original.close.copy()
        changed_high = original.high.copy()
        changed_close[cutoff + 1 :] += 500.0
        changed_high[cutoff + 1 :] += 500.0
        changed = MarketSeries(
            symbol=original.symbol,
            point=original.point,
            timeframe_seconds=original.timeframe_seconds,
            time=original.time,
            open=original.open,
            high=changed_high,
            low=original.low,
            close=changed_close,
            tick_volume=original.tick_volume,
            spread=original.spread,
        )
        actual = feature_vector_at(changed, cutoff, {}, [])
        np.testing.assert_allclose(expected, actual, equal_nan=True)

    def test_dataset_feature_time_precedes_friday_close(self) -> None:
        records = build_weekend_dataset(synthetic_series(), {}, placement_lead_minutes=5)
        self.assertTrue(records)
        for record in records:
            feature_time = datetime.fromisoformat(record.feature_time_utc)
            friday_close = datetime.fromisoformat(record.friday_close_utc)
            self.assertLess(feature_time, friday_close)

    def test_expanding_folds_are_chronological_and_embargoed(self) -> None:
        folds = expanding_folds(200, initial_train=100, splits=4, embargo=1)
        self.assertEqual(len(folds), 4)
        for train, test in folds:
            self.assertLess(int(train[-1]), int(test[0]) - 1)
            self.assertTrue(np.all(np.diff(train) == 1))
            self.assertTrue(np.all(np.diff(test) == 1))


if __name__ == "__main__":
    unittest.main()
