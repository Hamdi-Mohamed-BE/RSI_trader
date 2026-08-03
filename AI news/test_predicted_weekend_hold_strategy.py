from __future__ import annotations

import unittest

import numpy as np

from predicted_weekend_hold_strategy import DirectionSignal, HoldConfig, entry_index_for_lead, simulate_trade
from weekend_direction_model import MarketSeries


def series(reopen: float) -> MarketSeries:
    friday = np.arange(100, dtype=np.int64) * 60 + 1_700_000_000
    monday = friday[-1] + 3 * 24 * 60 * 60 + np.arange(20, dtype=np.int64) * 60
    time = np.concatenate((friday, monday))
    prices = np.full(len(time), 100.0)
    prices[100:] = reopen
    return MarketSeries(
        symbol="XAUUSD",
        point=0.01,
        timeframe_seconds=60,
        time=time,
        open=prices.copy(),
        high=prices.copy(),
        low=prices.copy(),
        close=prices.copy(),
        tick_volume=np.ones(len(time)),
        spread=np.zeros(len(time)),
    )


class PredictedWeekendHoldTests(unittest.TestCase):
    def test_lead_minutes_map_to_expected_bar(self) -> None:
        self.assertEqual(entry_index_for_lead(99, 1), 99)
        self.assertEqual(entry_index_for_lead(99, 5), 95)

    def test_stop_gap_can_lose_more_than_one_r(self) -> None:
        trade = simulate_trade(
            series(80.0),
            DirectionSignal(1, "2026-01-05T00:00:00+00:00", "BUY"),
            99,
            HoldConfig("test", 1, "fixed_5", 3.0, 20),
        )
        self.assertEqual(trade.outcome, "SL_GAP")
        self.assertAlmostEqual(trade.result_r, -4.0)

    def test_positive_gap_is_capped_at_target(self) -> None:
        trade = simulate_trade(
            series(130.0),
            DirectionSignal(1, "2026-01-05T00:00:00+00:00", "BUY"),
            99,
            HoldConfig("test", 1, "fixed_5", 3.0, 20),
        )
        self.assertEqual(trade.outcome, "TP_GAP")
        self.assertAlmostEqual(trade.result_r, 3.0)

    def test_zero_hold_exits_at_reopen_price(self) -> None:
        trade = simulate_trade(
            series(102.0),
            DirectionSignal(1, "2026-01-05T00:00:00+00:00", "BUY"),
            99,
            HoldConfig("test", 1, "fixed_5", 3.0, 0),
        )
        self.assertEqual(trade.outcome, "REOPEN")
        self.assertAlmostEqual(trade.result_r, 0.4)


if __name__ == "__main__":
    unittest.main()
