from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import unittest

from profit_hacker_bot.mt5_client import BrokerError
from profit_hacker_bot.parser import SignalParser
from profit_hacker_bot.telegram_service import TelegramSignalService
from profit_hacker_bot.trade_manager import TradeManager


SIGNAL_TEXT = "CADJPY SELL NOW\nSTOPOSS @ 114.260\nTP @ 113.900\nTP @ 113.760\nTP @ 113.600"


class FakeStorage:
    def __init__(self, existing: dict | None) -> None:
        self.existing = existing
        self.deleted = False
        self.records: list[dict] = []

    def message_record(self, source_id: str, message_id: int):
        return self.existing

    def delete_message(self, source_id: str, message_id: int) -> None:
        self.deleted = True
        self.existing = None

    def record_message(self, source_id: str, message_id: int, **values) -> None:
        self.records.append(values)


def service(storage: FakeStorage, handled: list) -> TelegramSignalService:
    instance = TelegramSignalService.__new__(TelegramSignalService)
    instance.settings = SimpleNamespace(
        telegram_channel=-1001303328644,
        max_signal_age_seconds=180,
        rescan_max_age_seconds=43200,
    )
    instance.storage = storage
    instance.parser = SignalParser(max_age_seconds=180)
    instance.handle_signal = handled.append
    return instance


class RecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_reprocesses_previously_ignored_message_once(self) -> None:
        storage = FakeStorage({"status": "ignored", "reason": "missing stop loss"})
        handled: list = []
        telegram = service(storage, handled)
        message = SimpleNamespace(
            id=29404,
            date=datetime.now(timezone.utc) - timedelta(minutes=10),
            raw_text=SIGNAL_TEXT,
            fwd_from=None,
            forward=None,
        )

        await telegram._process_message(message, recovery=True, verbose=False)

        self.assertTrue(storage.deleted)
        self.assertEqual(len(handled), 1)
        self.assertTrue(handled[0].recovered)

    async def test_does_not_reprocess_accepted_message(self) -> None:
        storage = FakeStorage({"status": "accepted", "reason": None})
        handled: list = []
        telegram = service(storage, handled)
        message = SimpleNamespace(
            id=29404,
            date=datetime.now(timezone.utc) - timedelta(minutes=10),
            raw_text=SIGNAL_TEXT,
        )

        await telegram._process_message(message, recovery=True, verbose=False)

        self.assertFalse(storage.deleted)
        self.assertEqual(handled, [])


class ActiveGeometryTests(unittest.TestCase):
    def setUp(self) -> None:
        outcome = SignalParser().parse(
            SIGNAL_TEXT,
            source_id="-1001303328644",
            message_id=29404,
            created_at=datetime.now(timezone.utc),
        )
        assert outcome.signal is not None
        self.signal = outcome.signal
        self.manager = TradeManager.__new__(TradeManager)

    def test_sell_is_active_between_stop_and_tp1(self) -> None:
        self.manager._validate_active_geometry(self.signal, 114.100)

    def test_sell_is_inactive_after_tp1(self) -> None:
        with self.assertRaises(BrokerError):
            self.manager._validate_active_geometry(self.signal, 113.850)


if __name__ == "__main__":
    unittest.main()
