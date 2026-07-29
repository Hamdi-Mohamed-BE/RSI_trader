from datetime import datetime
from types import SimpleNamespace
import unittest

from orb.backtest import _metrics
from orb.config import load_config
from orb.live import _normalize_volume
from orb.strategy import Trade


class CoreTests(unittest.TestCase):
    def test_new_york_timezone_handles_dst(self):
        zone = load_config().timezone
        winter = datetime(2026, 1, 15, 8, 20, tzinfo=zone)
        summer = datetime(2026, 7, 15, 8, 20, tzinfo=zone)
        self.assertNotEqual(winter.utcoffset(), summer.utcoffset())

    def test_volume_is_rounded_down_to_broker_step(self):
        info = SimpleNamespace(volume_min=0.01, volume_max=100.0, volume_step=0.01)
        self.assertEqual(_normalize_volume(0.678, info), 0.67)

    def test_profit_factor_uses_gross_profit_over_gross_loss(self):
        common = {
            "session_date": "2026-01-01",
            "direction": "buy",
            "entry_time": "2026-01-01T10:00:00+00:00",
            "exit_time": "2026-01-01T11:00:00+00:00",
            "entry": 1.0,
            "stop": 0.0,
            "tp1": 2.0,
            "tp2": 3.0,
            "outcome": "test",
            "risk_amount": 10.0,
            "spread_points": 0,
        }
        trades = [
            Trade(**common, r_multiple=2.0, pnl=20.0, balance_after=120.0),
            Trade(**common, r_multiple=-1.0, pnl=-10.0, balance_after=110.0),
        ]
        metrics = _metrics(trades, 100.0)
        self.assertEqual(metrics["profit_factor"], 2.0)
        self.assertEqual(metrics["win_rate"], 50.0)


if __name__ == "__main__":
    unittest.main()
