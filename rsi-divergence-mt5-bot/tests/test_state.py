from datetime import datetime, timezone

from telegram_mt5_copier.models import TelegramMessage
from telegram_mt5_copier.state import StateStore


def test_message_dedup_and_edit_retry(tmp_path):
    store = StateStore(tmp_path / "state.sqlite")
    message = TelegramMessage("-1001", 7, datetime.now(timezone.utc), "EURUSD BUY")
    assert store.is_processed(message) is False
    store.record_message(message, "IGNORED")
    assert store.is_processed(message) is True
    edited = TelegramMessage("-1001", 7, message.date, "EURUSD BUY NOW SL 1 TP 2", edited=True)
    assert store.is_processed(edited) is False


def test_error_message_can_retry(tmp_path):
    store = StateStore(tmp_path / "state.sqlite")
    message = TelegramMessage("-1001", 8, datetime.now(timezone.utc), "CADJPY SELL")
    store.record_message(message, "ERROR", error="MT5 offline")
    assert store.is_processed(message) is False
