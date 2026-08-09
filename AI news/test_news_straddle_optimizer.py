from __future__ import annotations

import unittest
from datetime import datetime, timezone

import numpy as np

from optimize_news_straddle_5y import EntryConfig, EventData, _event_matrix, _resolve_entry


def market(times: list[int], bids: list[float], asks: list[float]) -> EventData:
    release = datetime.fromtimestamp(100, timezone.utc)
    return EventData(
        event="NFP",
        released=release,
        release_ms=100_000,
        times=np.asarray(times, dtype=np.int64),
        bid=np.asarray(bids, dtype=np.float64),
        ask=np.asarray(asks, dtype=np.float64),
        m1_bid={},
        m1_ask={},
    )


class NewsStraddleOptimizerTests(unittest.TestCase):
    def test_opposite_stop_can_fill_inside_cancel_latency(self) -> None:
        data = market(
            [89_900, 90_000, 100_000, 100_100, 105_000],
            [99.5, 99.5, 100.8, 98.8, 100.0],
            [100.0, 100.0, 101.3, 99.3, 100.5],
        )
        config = EntryConfig(10, 0.5, 0.5, 1.0, 30, cancel_latency_ms=250)
        outcome = _resolve_entry(data, config)
        self.assertEqual(outcome["status"], "traded")
        self.assertTrue(outcome["dual_fill"])
        self.assertEqual([fill["side"] for fill in outcome["fills"]], ["buy", "sell"])

    def test_target_requires_post_fill_quote(self) -> None:
        data = market(
            [89_900, 90_000, 100_000, 100_100, 105_000],
            [99.5, 99.5, 100.8, 103.0, 103.5],
            [100.0, 100.0, 101.3, 103.5, 104.0],
        )
        config = EntryConfig(10, 0.5, 4.0, 1.0, 30, cancel_latency_ms=250)
        result = _event_matrix(data, config)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(int(result["target_hits"][0, 0]), 1)
        self.assertGreater(float(result["matrix"][0, 0]), 0.0)


if __name__ == "__main__":
    unittest.main()
