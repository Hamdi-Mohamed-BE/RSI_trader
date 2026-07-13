import asyncio
from datetime import datetime, timedelta
from types import SimpleNamespace
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


def _message(minutes_old: int):
    return TelegramMessage(
        id=3,
        chat_id=123,
        message_id=789,
        message_date=datetime.utcnow() - timedelta(minutes=minutes_old),
        raw_text="XAUUSD BUY LIMIT @ 2400 SL 2390 TP 2410",
    )


def _stale_settings(session, key):
    values = {
        "stale_signal_max_age_minutes": 5,
        "stale_signal_max_entry_distance_points": 50,
    }
    return values[key]


@patch("app.services.copier_service.SettingsService.get", side_effect=_stale_settings)
def test_stale_signal_without_explicit_entry_is_rejected(mock_get):
    parsed = SimpleNamespace(side="buy", entry_price=None, stop_loss=2390.0)

    error = CopierService()._validate_stale_signal(
        MagicMock(),
        _message(minutes_old=10),
        parsed,
        {"ask": 2400.0, "bid": 2399.8},
        {"point": 0.01},
    )

    assert "no explicit entry price" in error


@patch("app.services.copier_service.SettingsService.get", side_effect=_stale_settings)
def test_stale_signal_far_from_entry_is_rejected(mock_get):
    parsed = SimpleNamespace(side="buy", order_type="market", pending_type=None, entry_price=2400.0, stop_loss=2390.0)

    error = CopierService()._validate_stale_signal(
        MagicMock(),
        _message(minutes_old=10),
        parsed,
        {"ask": 2403.0, "bid": 2402.8},
        {"point": 0.01},
    )

    assert "current price" in error
    assert "from entry" in error


@patch("app.services.copier_service.SettingsService.get", side_effect=_stale_settings)
def test_stale_signal_near_entry_is_allowed(mock_get):
    parsed = SimpleNamespace(side="buy", order_type="market", pending_type=None, entry_price=2400.0, stop_loss=2390.0)

    error = CopierService()._validate_stale_signal(
        MagicMock(),
        _message(minutes_old=10),
        parsed,
        {"ask": 2400.25, "bid": 2400.05},
        {"point": 0.01},
    )

    assert error is None


@patch("app.services.copier_service.SettingsService.get", side_effect=_stale_settings)
def test_stale_pending_limit_order_is_allowed_even_far_from_entry(mock_get):
    parsed = SimpleNamespace(
        side="buy",
        order_type="pending",
        pending_type="buy_limit",
        entry_price=2400.0,
        stop_loss=2390.0,
    )

    error = CopierService()._validate_stale_signal(
        MagicMock(),
        _message(minutes_old=60),
        parsed,
        {"ask": 2450.0, "bid": 2449.8},
        {"point": 0.01},
    )

    assert error is None


@patch("app.services.copier_service.SettingsService.get", side_effect=_stale_settings)
def test_stale_validation_force_bypass_allows_old_market_signal(mock_get):
    parsed = SimpleNamespace(side="buy", order_type="market", pending_type=None, entry_price=None, stop_loss=2390.0)

    error = CopierService()._validate_stale_signal(
        MagicMock(),
        _message(minutes_old=60),
        parsed,
        {"ask": 2450.0, "bid": 2449.8},
        {"point": 0.01},
        force_bypass=True,
    )

    assert error is None
