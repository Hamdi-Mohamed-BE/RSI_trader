from datetime import datetime, timezone

import app.telegram_signaler as telegram_signaler
from app.telegram_signaler import (
    TelegramTradeSignaler,
    _classify_stop_update,
    _direction,
    _parse_strategy_magics,
    _setup_timeframe,
)


def test_strategy_magic_parser_keeps_named_mappings() -> None:
    parsed = _parse_strategy_magics("LTA:11,ORB:22,SNIPER:33")

    assert parsed == {11: "LTA", 22: "ORB", 33: "SNIPER"}


def test_pending_direction_and_timeframe_are_detected() -> None:
    assert _direction({"type": 4}, pending=True) == "BUY"
    assert _direction({"type": 5}, pending=True) == "SELL"
    assert _setup_timeframe("LTA A+ S94 H1", "LTA", {"LTA": "M15"}) == "H1"
    assert _setup_timeframe("ORB entry", "ORB", {"ORB": "M5"}) == "M5"


def test_tp1_stop_move_is_classified_as_break_even() -> None:
    old = {"direction": "BUY", "price_open": 3300.0, "sl": 3290.0, "point": 0.01}
    new = {"direction": "BUY", "price_open": 3300.0, "sl": 3300.0, "point": 0.01}

    heading, message = _classify_stop_update(old, new)

    assert heading == "TP1 / BREAK EVEN"
    assert "break even" in message.lower()


def test_pending_fill_matches_strategy_symbol_and_direction() -> None:
    position = {"magic": 100, "symbol": "XAUUSDm", "direction": "BUY"}
    removed = {
        "1": {"magic": 100, "symbol": "XAUUSDm", "direction": "SELL", "time": 20},
        "2": {"magic": 100, "symbol": "XAUUSDm", "direction": "BUY", "time": 10},
        "3": {"magic": 100, "symbol": "XAUUSDm", "direction": "BUY", "time": 30},
    }

    matched = TelegramTradeSignaler._matching_removed_order(position, removed)

    assert matched is not None
    assert matched[0] == "3"


def test_chart_renderer_returns_a_png(monkeypatch) -> None:
    start = int(datetime(2026, 7, 1, tzinfo=timezone.utc).timestamp())
    rates = [
        {
            "time": start + index * 300,
            "open": 3300.0 + index,
            "high": 3301.5 + index,
            "low": 3299.0 + index,
            "close": 3300.8 + index,
        }
        for index in range(20)
    ]

    class FakeMT5:
        @staticmethod
        def copy_rates_from_pos(_symbol, _timeframe, _offset, _bars):
            return rates

    monkeypatch.setattr(telegram_signaler, "mt5", FakeMT5())
    monkeypatch.setattr(telegram_signaler, "_mt5_timeframe", lambda _timeframe: 5)
    signaler = TelegramTradeSignaler.__new__(TelegramTradeSignaler)
    signaler.send_chart = True
    signaler.chart_bars = 20
    trade = {
        "strategy": "LTA",
        "symbol": "XAUUSD",
        "direction": "BUY",
        "timeframe": "M5",
        "price_open": 3310.0,
        "sl": 3295.0,
        "tp": 3340.0,
        "price_current": 3318.0,
        "digits": 2,
    }

    image = TelegramTradeSignaler._chart_png(signaler, trade)

    assert image is not None
    assert image.startswith(b"\x89PNG\r\n\x1a\n")
