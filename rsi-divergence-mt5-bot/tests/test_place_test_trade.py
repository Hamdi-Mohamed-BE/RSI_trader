import unittest
from unittest.mock import MagicMock

from rsi_divergence_bot.config import AppConfig
from rsi_divergence_bot.mt5_account_pool import Mt5AccountPool
from rsi_divergence_bot.trader import TradeExecutor


class PlaceTestTradeTests(unittest.TestCase):
    def test_executor_paper_mode(self) -> None:
        config = AppConfig.model_validate(
            {
                "bot": {"dry_run": True},
                "symbols": [{"symbol": "XAUUSD", "name": "Gold", "lot_per_leg": 0.01}],
            }
        )
        client = MagicMock()
        client.tick.return_value = {"ask": 3300.0, "bid": 3299.5}
        client.normalize_volume.return_value = 0.01
        executor = TradeExecutor(config, client, MagicMock(), MagicMock())
        result = executor.place_test_trade("XAUUSD", "buy", 0.01)
        self.assertEqual(result["status"], "paper")
        self.assertEqual(result["symbol"], "XAUUSD")
        client.send_market_bare.assert_not_called()

    def test_pool_requires_enabled_accounts(self) -> None:
        pool = Mt5AccountPool.__new__(Mt5AccountPool)
        pool.store = MagicMock()
        pool.store.enabled_accounts.return_value = []
        pool.target_accounts = MagicMock(return_value=[])
        result = pool.place_test_trade(symbol="XAUUSD", side="buy", volume=0.01)
        self.assertEqual(result["status"], "failed")
        self.assertIn("no enabled", result["reason"])


if __name__ == "__main__":
    unittest.main()
