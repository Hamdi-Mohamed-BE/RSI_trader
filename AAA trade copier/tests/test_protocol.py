from decimal import Decimal
from uuid import uuid4

import pytest

from trade_copier.domain.enums import Side, TradeAction
from trade_copier.domain.messages import SourceTradeMessage
from trade_copier.transport.protocol import ProtocolError, decode_message, encode_message


def source_message() -> SourceTradeMessage:
    return SourceTradeMessage(
        sequence=1,
        source_account_id=uuid4(),
        source_order_id="1",
        action=TradeAction.MARKET_OPEN,
        side=Side.BUY,
        symbol="EURUSD",
        volume=Decimal("1"),
        entry_price=Decimal("1.1000"),
        stop_loss=Decimal("1.0900"),
    )


def test_protocol_round_trip() -> None:
    original = source_message()
    decoded = decode_message(encode_message(original))
    assert isinstance(decoded, SourceTradeMessage)
    assert decoded.event_uid == original.event_uid


def test_protocol_rejects_unknown_message() -> None:
    with pytest.raises(ProtocolError):
        decode_message(b'{"message_type":"unknown"}\n')


def test_new_entry_without_stop_is_valid_protocol_input() -> None:
    message = SourceTradeMessage(
        sequence=1,
        source_account_id=uuid4(),
        source_order_id="1",
        action=TradeAction.MARKET_OPEN,
        side=Side.BUY,
        symbol="EURUSD",
        volume=Decimal("1"),
        entry_price=Decimal("1.1000"),
    )

    assert message.stop_loss is None
