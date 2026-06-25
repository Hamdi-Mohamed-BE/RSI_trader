from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from profit_hacker_bot.models import Direction, EntryType
from profit_hacker_bot.parser import SignalParser


class SignalParserTest(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = SignalParser(max_age_seconds=180)
        self.now = datetime(2026, 6, 25, 12, 0, tzinfo=timezone.utc)

    def parse(self, text: str, **kwargs):
        return self.parser.parse(
            text,
            source_id="-1001303328644",
            message_id=10,
            created_at=self.now - timedelta(seconds=10),
            now=self.now,
            **kwargs,
        )

    def test_parses_buy_now_with_comma_prices(self) -> None:
        outcome = self.parse(
            """
            NAS100 BUY NOW
            STOPLOSS @ 29,235

            TP @ 29,650
            TP @ 29,810
            TP @ 30,020
            """
        )

        self.assertTrue(outcome.accepted)
        signal = outcome.signal
        assert signal is not None
        self.assertEqual(signal.symbol, "NAS100")
        self.assertEqual(signal.direction, Direction.BUY)
        self.assertEqual(signal.entry_type, EntryType.MARKET)
        self.assertEqual(signal.stop_loss, 29235.0)
        self.assertEqual(signal.take_profits, (29650.0, 29810.0, 30020.0))

    def test_parses_sell_now(self) -> None:
        outcome = self.parse(
            """
            GBPUSD SELL NOW
            STOPLOSS @ 1.32850

            TP @ 1.32050
            TP @ 1.31800
            TP @ 1.31450
            """
        )

        self.assertTrue(outcome.accepted)
        signal = outcome.signal
        assert signal is not None
        self.assertEqual(signal.symbol, "GBPUSD")
        self.assertEqual(signal.direction, Direction.SELL)
        self.assertEqual(signal.stop_loss, 1.32850)
        self.assertEqual(signal.final_tp, 1.31450)

    def test_rejects_forwarded_message(self) -> None:
        outcome = self.parse(
            """
            GBPUSD SELL NOW
            STOPLOSS @ 1.32850
            TP @ 1.32050
            """,
            forwarded=True,
        )

        self.assertFalse(outcome.accepted)
        self.assertEqual(outcome.ignored_reason, "forwarded message")

    def test_rejects_old_message(self) -> None:
        outcome = self.parser.parse(
            "NAS100 BUY NOW\nSL @ 29235\nTP @ 29650",
            source_id="-1001303328644",
            message_id=11,
            created_at=self.now - timedelta(seconds=181),
            now=self.now,
        )

        self.assertFalse(outcome.accepted)
        self.assertIn("older", outcome.ignored_reason or "")

    def test_parses_pending_limit(self) -> None:
        outcome = self.parse(
            """
            XAUUSD BUY LIMIT @ 3330
            SL @ 3310
            TP @ 3350
            TP @ 3375
            """
        )

        self.assertTrue(outcome.accepted)
        signal = outcome.signal
        assert signal is not None
        self.assertEqual(signal.entry_type, EntryType.LIMIT)
        self.assertEqual(signal.entry_price, 3330.0)

    def test_entry_without_limit_or_stop_is_auto_pending(self) -> None:
        outcome = self.parse(
            """
            XAUUSD BUY @ 3330
            SL @ 3310
            TP @ 3350
            """
        )

        self.assertTrue(outcome.accepted)
        signal = outcome.signal
        assert signal is not None
        self.assertEqual(signal.entry_type, EntryType.AUTO)


if __name__ == "__main__":
    unittest.main()
