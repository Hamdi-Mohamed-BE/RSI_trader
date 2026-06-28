from __future__ import annotations

from datetime import datetime, timedelta
import unittest

import pandas as pd

from scripts.rr_sweep_backtest import simulate_trade


def candles(*bars: tuple[float, float, float]) -> pd.DataFrame:
    start = datetime(2026, 1, 1)
    return pd.DataFrame(
        [
            {
                "time": start + timedelta(minutes=15 * index),
                "open": close,
                "high": high,
                "low": low,
                "close": close,
            }
            for index, (high, low, close) in enumerate(bars)
        ]
    )


class ManagedRRSweepTests(unittest.TestCase):
    def test_tp1_moves_stop_to_break_even(self) -> None:
        data = candles((100.2, 99.8, 100.0), (101.2, 100.2, 100.8), (100.4, 99.9, 100.1))
        result = simulate_trade(data, 0, {"direction": "BUY", "entry": 100.0, "stop_loss": 99.0}, 4, 10)
        self.assertEqual(result[2], "break_even")
        self.assertEqual(result[4], 1)
        self.assertEqual(result[5], 0.0)

    def test_tp3_moves_stop_to_tp2(self) -> None:
        data = candles((100.2, 99.8, 100.0), (103.2, 100.2, 102.8), (102.4, 101.8, 102.0))
        result = simulate_trade(data, 0, {"direction": "BUY", "entry": 100.0, "stop_loss": 99.0}, 6, 10)
        self.assertEqual(result[2], "trail_stop")
        self.assertEqual(result[4], 3)
        self.assertEqual(result[5], 2.0)
        self.assertAlmostEqual(result[1], 102.0)

    def test_final_target_closes_trade(self) -> None:
        data = candles((100.2, 99.8, 100.0), (106.2, 100.2, 105.8))
        result = simulate_trade(data, 0, {"direction": "BUY", "entry": 100.0, "stop_loss": 99.0}, 6, 10)
        self.assertEqual(result[2], "win")
        self.assertEqual(result[4], 6)
        self.assertEqual(result[5], 6.0)


if __name__ == "__main__":
    unittest.main()
