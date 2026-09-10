import unittest
from types import SimpleNamespace

from backtest_news_v9_execution_v2_1y import (
    candidate_configs,
    risk_lot,
    wilson_lower_bound,
)


class V9ExecutionV2Tests(unittest.TestCase):
    @staticmethod
    def symbol() -> SimpleNamespace:
        return SimpleNamespace(
            trade_tick_size=0.001,
            trade_tick_value=0.1,
            trade_tick_value_loss=0.1,
            volume_step=0.01,
            volume_min=0.01,
            volume_max=200.0,
        )

    def test_candidate_grid_is_fixed(self):
        self.assertEqual(len(candidate_configs()), 1568)

    def test_one_percent_risk_with_twenty_dollar_stop(self):
        lot, budget, nominal = risk_lot(10_000.0, 20.0, self.symbol())
        self.assertEqual(lot, 0.05)
        self.assertEqual(budget, 100.0)
        self.assertEqual(nominal, 100.0)

    def test_wilson_score_rewards_more_wins_at_same_sample_size(self):
        self.assertGreater(wilson_lower_bound(19, 20), wilson_lower_bound(18, 20))


if __name__ == "__main__":
    unittest.main()
