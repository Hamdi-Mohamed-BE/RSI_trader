from __future__ import annotations

import unittest

from news_v8_move_range import (
    RangeConfig,
    predict_magnitude_range,
    signed_range,
    weighted_quantile,
)


class MoveRangeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.history = [
            {
                "release_utc": f"2025-{month:02d}-01T12:30:00+00:00",
                "event": "CPI",
                "absolute_move_usd": float(month),
                "atr_30m": 1.0,
                "spread_usd": 0.05,
            }
            for month in range(1, 13)
        ]

    def test_weighted_quantile_favors_recent_values(self) -> None:
        unweighted = weighted_quantile([1, 2, 10], 0.5)
        weighted = weighted_quantile([1, 2, 10], 0.5, [1, 1, 10])
        self.assertGreater(weighted, unweighted)

    def test_forecast_uses_only_requested_event_history(self) -> None:
        history = self.history + [
            {
                "release_utc": "2025-12-02T12:30:00+00:00",
                "event": "NFP",
                "absolute_move_usd": 1000.0,
                "atr_30m": 1.0,
                "spread_usd": 0.05,
            }
        ]
        result = predict_magnitude_range(
            history,
            event="CPI",
            current_atr=1.0,
            current_spread=0.05,
            config=RangeConfig("usd", None, None),
        )
        self.assertLess(result["maximum_usd"], 20)

    def test_negative_signed_range_is_ordered(self) -> None:
        result = signed_range(
            "NEGATIVE",
            {
                "minimum_usd": 10.0,
                "median_usd": 20.0,
                "maximum_usd": 30.0,
            },
        )
        self.assertEqual(result["range_low_usd"], -30.0)
        self.assertEqual(result["point_estimate_usd"], -20.0)
        self.assertEqual(result["range_high_usd"], -10.0)


if __name__ == "__main__":
    unittest.main()
