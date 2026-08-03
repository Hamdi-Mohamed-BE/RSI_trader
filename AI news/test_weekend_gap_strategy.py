from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from weekend_gap_strategy import StrategyConfig, backtest, find_weekend_windows


def row(moment: datetime, open_: float, high: float, low: float, close: float, spread: int = 2) -> dict:
    return {
        "time": int(moment.timestamp()),
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "spread": spread,
    }


class WeekendGapStrategyTests(unittest.TestCase):
    def test_reopen_gap_triggers_buy_and_cancels_other_side(self) -> None:
        friday = datetime(2026, 7, 31, 20, 57, tzinfo=timezone.utc)
        monday = datetime(2026, 8, 2, 22, 0, tzinfo=timezone.utc)
        rows = [
            row(friday, 100, 101, 99, 100),
            row(friday + timedelta(minutes=1), 100, 101, 99, 100),
            row(friday + timedelta(minutes=2), 100, 101, 99, 100),
            row(monday, 105, 109, 104, 108),
            row(monday + timedelta(minutes=1), 108, 109, 107, 108),
        ]
        config = StrategyConfig(3, 2, 2, 2, 2)
        result = backtest(rows, 0.01, config)
        self.assertEqual(len(find_weekend_windows(rows)), 1)
        self.assertEqual(result.metrics["trades"], 1)
        self.assertEqual(result.trades[0].side, "BUY")
        self.assertEqual(result.trades[0].source, "reopen")

    def test_unhit_orders_expire_at_reopen_without_using_monday_wick(self) -> None:
        friday = datetime(2026, 7, 31, 20, 57, tzinfo=timezone.utc)
        monday = datetime(2026, 8, 2, 22, 0, tzinfo=timezone.utc)
        rows = [
            row(friday, 100, 101, 99, 100),
            row(friday + timedelta(minutes=1), 100, 101, 99, 100),
            row(friday + timedelta(minutes=2), 100, 101, 99, 100),
            row(monday, 100, 110, 90, 100),
        ]
        result = backtest(rows, 0.01, StrategyConfig(3, 2, 2, 2, 2))
        self.assertEqual(result.metrics["trades"], 0)
        self.assertEqual(result.expired, 1)

    def test_friday_trigger_is_allowed_before_close(self) -> None:
        friday = datetime(2026, 7, 31, 20, 57, tzinfo=timezone.utc)
        monday = datetime(2026, 8, 2, 22, 0, tzinfo=timezone.utc)
        rows = [
            row(friday, 100, 101, 99, 100),
            row(friday + timedelta(minutes=1), 100, 105, 100, 104),
            row(friday + timedelta(minutes=2), 104, 108, 103, 107),
            row(monday, 107, 107, 107, 107),
        ]
        result = backtest(rows, 0.01, StrategyConfig(3, 2, 2, 1, 3))
        self.assertEqual(result.metrics["trades"], 1)
        self.assertEqual(result.trades[0].source, "friday")


if __name__ == "__main__":
    unittest.main()
