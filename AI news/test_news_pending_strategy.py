from __future__ import annotations

import unittest

from news_pending_strategy import performance


class PendingStrategyMetricsTests(unittest.TestCase):
    def test_performance_uses_compounded_risk_and_drawdown(self) -> None:
        trades = [
            {
                "entry_time": "2026-01-01T00:00:00+00:00",
                "leg": "breakout",
                "result_r": 2.0,
            },
            {
                "entry_time": "2026-01-02T00:00:00+00:00",
                "leg": "breakout",
                "result_r": -1.0,
            },
        ]
        result = performance(trades, risk_pct=1.0, start_balance=10_000.0)
        self.assertEqual(result["trades"], 2)
        self.assertEqual(result["wins"], 1)
        self.assertEqual(result["profit_factor"], 2.0)
        self.assertEqual(round(result["ending_balance"], 2), 10_098.0)
        self.assertEqual(round(result["max_drawdown_pct"], 2), 1.0)

    def test_performance_profit_factor_is_none_without_losses(self) -> None:
        result = performance(
            [
                {
                    "entry_time": "2026-01-01T00:00:00+00:00",
                    "leg": "breakout",
                    "result_r": 1.0,
                }
            ]
        )
        self.assertIsNone(result["profit_factor"])
        self.assertEqual(result["win_rate_pct"], 100.0)


if __name__ == "__main__":
    unittest.main()
