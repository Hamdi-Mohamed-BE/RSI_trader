import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from rsi_divergence_bot.live_summary import build_live_summary


class LiveSummaryDealFilterTests(unittest.TestCase):
    def test_excludes_balance_and_withdrawal_from_trade_count(self) -> None:
        client = MagicMock()
        start = datetime(2026, 5, 31, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 5, 31, 23, 59, tzinfo=timezone.utc)
        client.deals_range.return_value = [
            {
                "ticket": 1,
                "position_id": 0,
                "symbol": "",
                "side": "2",
                "type": 2,
                "volume": 0.0,
                "price": 0.0,
                "profit": 10000.0,
                "commission": 0.0,
                "swap": 0.0,
                "fee": 0.0,
                "comment": "D-trial-USD",
                "time": "2026-05-31T14:00:00+00:00",
            },
            {
                "ticket": 2,
                "position_id": 0,
                "symbol": "",
                "side": "2",
                "type": 2,
                "volume": 0.0,
                "price": 0.0,
                "profit": -9700.0,
                "commission": 0.0,
                "swap": 0.0,
                "fee": 0.0,
                "comment": "W-trial-USD",
                "time": "2026-05-31T14:05:00+00:00",
            },
            {
                "ticket": 3,
                "position_id": 100,
                "symbol": "EURUSD",
                "side": "buy",
                "type": 0,
                "volume": 0.01,
                "price": 1.1,
                "profit": 5.0,
                "commission": 0.0,
                "swap": 0.0,
                "fee": 0.0,
                "comment": "rsi test",
                "time": "2026-05-31T15:00:00+00:00",
            },
            {
                "ticket": 4,
                "position_id": 100,
                "symbol": "EURUSD",
                "side": "sell",
                "type": 1,
                "volume": 0.01,
                "price": 1.1005,
                "profit": 0.0,
                "commission": 0.0,
                "swap": 0.0,
                "fee": 0.0,
                "comment": "rsi test",
                "time": "2026-05-31T15:30:00+00:00",
            },
        ]

        result = build_live_summary(client, start, end)

        self.assertEqual(result["overall"]["trades"], 1)
        self.assertEqual(len(result["trades"]), 1)
        self.assertEqual(result["trades"][0]["symbol"], "EURUSD")
        self.assertEqual(result["trades"][0]["pnl"], 5.0)


if __name__ == "__main__":
    unittest.main()
