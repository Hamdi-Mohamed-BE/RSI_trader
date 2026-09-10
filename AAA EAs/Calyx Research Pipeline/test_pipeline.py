from __future__ import annotations

import unittest
from datetime import datetime, timezone

from calyx_pipeline import bootstrap, profit_factor, sharpe_statistics, streaks, wilson_interval
from fxmacrodata import high_impact_calendar, known_at_rows


class PipelineStatisticsTests(unittest.TestCase):
    def test_wilson_interval_is_reasonable(self) -> None:
        lower, upper = wilson_interval(50, 100)
        self.assertLess(lower, 0.5)
        self.assertGreater(upper, 0.5)
        self.assertAlmostEqual(lower, 0.4038, places=3)
        self.assertAlmostEqual(upper, 0.5962, places=3)

    def test_profit_factor_and_streaks(self) -> None:
        values = [2.0, 1.0, -1.0, -2.0, -1.0, 3.0]
        self.assertAlmostEqual(profit_factor(values), 1.5)
        self.assertEqual(streaks(values), (2, 3))

    def test_block_bootstrap_is_deterministic(self) -> None:
        kwargs = dict(
            trade_pnl=[100.0, -50.0, 80.0, -20.0, 40.0],
            returns=[0.01, -0.005, 0.008, -0.002, 0.004],
            paths=200,
            block=2,
            daily_loss_limit_pct=5.0,
            total_loss_limit_pct=10.0,
            seed=42,
        )
        self.assertEqual(bootstrap(**kwargs), bootstrap(**kwargs))

    def test_deflated_sharpe_penalizes_many_trials(self) -> None:
        returns = [0.004, -0.001, 0.003, 0.0, 0.002, -0.001] * 30
        one = sharpe_statistics(returns, 1, 252.0)
        many = sharpe_statistics(returns, 100, 252.0)
        self.assertLess(many["deflated_sharpe_pct"], one["deflated_sharpe_pct"])


class FXMacroDataSafetyTests(unittest.TestCase):
    def test_known_at_filter_blocks_future_release(self) -> None:
        rows = [
            {"val": 1, "announcement_datetime": 100},
            {"val": 2, "announcement_datetime": 200},
            {"val": 3},
        ]
        decision = datetime.fromtimestamp(150, tz=timezone.utc)
        self.assertEqual([row["val"] for row in known_at_rows(rows, decision)], [1])

    def test_high_impact_calendar(self) -> None:
        payload = {
            "currency": "USD",
            "data": [
                {"release": "cpi", "event_importance": "high"},
                {"release": "minor", "event_importance": "low", "market_tier": 3},
            ],
        }
        selected = high_impact_calendar(payload)
        self.assertEqual([row["release"] for row in selected["data"]], ["cpi"])


if __name__ == "__main__":
    unittest.main()
