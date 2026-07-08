import asyncio
from datetime import datetime
from unittest.mock import MagicMock, patch

from app.core.signal_hash import signal_content_hash
from app.db.models import OrderAttempt, TelegramMessage
from app.services.copier_service import CopierService


def test_signal_content_hash_normalizes_spacing_and_case():
    first = "XAUUSD BUY NOW\nSL @ 2400\nTP @ 2410"
    second = "  xauusd   buy now SL @ 2400   TP @ 2410  "

    assert signal_content_hash(first) == signal_content_hash(second)


@patch("app.services.copier_service.parse_signal")
@patch("app.services.copier_service.SystemEventRepository")
@patch("app.services.copier_service.TelegramMessageRepository")
@patch("app.services.copier_service.OrderAttemptRepository")
def test_process_message_skips_already_placed_signal_hash(mock_attempts, mock_messages, mock_events, mock_parse):
    existing_attempt = OrderAttempt(
        id=7,
        telegram_message_db_id=1,
        signal_hash=signal_content_hash("XAUUSD BUY NOW SL 2400 TP 2410"),
        symbol_raw="XAUUSD",
        broker_symbol="XAUUSDm",
        side="buy",
        order_type="market",
        lot=0.01,
        risk_mode="fixed_lot",
        risk_amount=0.01,
        status="placed",
    )
    mock_attempts.get_placed_by_signal_hash.return_value = existing_attempt
    msg = TelegramMessage(
        id=2,
        chat_id=123,
        message_id=456,
        message_date=datetime.utcnow(),
        raw_text="xauusd buy now sl 2400 tp 2410",
    )

    asyncio.run(CopierService()._process_message(MagicMock(), msg))

    assert msg.processed is True
    assert msg.ignored is True
    assert "Duplicate signal content" in msg.ignore_reason
    mock_parse.assert_not_called()
    mock_messages.save.assert_called_once()
