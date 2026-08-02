from __future__ import annotations

import unittest

from backtest_news_pulse_offset import OffsetConfig, _performance


class NewsPulseOffsetTests(unittest.TestCase):
    def test_performance_counts_reversal_metrics(self) -> None:
        trades = [
            {
                "entry_time": "2026-01-01T00:00:00+00:00",
                "result_r": 3.0,
                "outcome": "TP",
                "reached_1r": True,
                "snapback": False,
            },
            {
                "entry_time": "2026-01-02T00:00:00+00:00",
                "result_r": -1.0,
                "outcome": "SL",
                "reached_1r": False,
                "snapback": True,
            },
        ]
        result = _performance(trades)
        self.assertEqual(result["profit_factor"], 3.0)
        self.assertEqual(result["net_r"], 2.0)
        self.assertEqual(result["one_r_continuation_pct"], 50.0)
        self.assertEqual(result["snapback_rate_pct"], 50.0)

    def test_offset_config_is_explicit(self) -> None:
        config = OffsetConfig(fixed_offset_pips=2.0, spread_multiplier=1.0)
        self.assertEqual(
            max(config.fixed_offset_pips, 3.5 * config.spread_multiplier),
            3.5,
        )


if __name__ == "__main__":
    unittest.main()
