import unittest
from types import SimpleNamespace

from backtest_news_v8_dynamic_compounding_3m import _dynamic_lot


class DynamicLotTests(unittest.TestCase):
    def setUp(self):
        self.info = SimpleNamespace(
            volume_step=0.01,
            volume_min=0.01,
            volume_max=200.0,
        )

    def test_balance_below_one_hundred_does_not_trade(self):
        self.assertEqual(_dynamic_lot(99.99, self.info), (0, 0.0))

    def test_one_hundred_uses_point_zero_six(self):
        self.assertEqual(_dynamic_lot(100.0, self.info), (1, 0.06))

    def test_partial_hundred_is_not_rounded_up(self):
        self.assertEqual(_dynamic_lot(599.99, self.info), (5, 0.30))

    def test_broker_maximum_caps_the_result(self):
        self.assertEqual(_dynamic_lot(1_000_000.0, self.info), (10_000, 200.0))


if __name__ == "__main__":
    unittest.main()
