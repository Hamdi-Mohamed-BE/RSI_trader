import unittest
from types import SimpleNamespace

from backtest_news_v9_risk_1pct_1y import _drawdown, _risk_lot


class V9RiskOneYearTests(unittest.TestCase):
    @staticmethod
    def _symbol() -> SimpleNamespace:
        return SimpleNamespace(
            trade_tick_size=0.01,
            trade_tick_value=1.0,
            trade_tick_value_loss=1.0,
            volume_step=0.01,
            volume_min=0.01,
            volume_max=100.0,
        )

    def test_one_percent_of_10000_sizes_to_quarter_lot(self):
        lot, budget, nominal = _risk_lot(10_000.0, self._symbol())
        self.assertEqual(lot, 0.25)
        self.assertEqual(budget, 100.0)
        self.assertEqual(nominal, 100.0)

    def test_lot_rounds_down_without_exceeding_risk_budget(self):
        lot, budget, nominal = _risk_lot(10_050.0, self._symbol())
        self.assertEqual(lot, 0.25)
        self.assertLessEqual(nominal, budget)

    def test_drawdown_reports_amount_and_peak_percentage(self):
        amount, percent = _drawdown([10_000.0, 12_000.0, 10_800.0])
        self.assertEqual(amount, 1_200.0)
        self.assertAlmostEqual(percent, 10.0)


if __name__ == "__main__":
    unittest.main()
