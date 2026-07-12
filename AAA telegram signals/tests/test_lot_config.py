from app.trading.lot_config import canonical_symbol, fixed_lot_for_signal, parse_symbol_lots


def test_canonical_symbol_handles_aliases_and_broker_suffixes():
    assert canonical_symbol("GOLD") == "XAUUSD"
    assert canonical_symbol("XAAUSD") == "XAUUSD"
    assert canonical_symbol("XAUUSDm") == "XAUUSD"
    assert canonical_symbol("BTCUSD.raw") == "BTCUSD"
    assert canonical_symbol("USTEC") == "US100"
    assert canonical_symbol("USTECm") == "US100"


def test_parse_symbol_lots_accepts_ui_lines_and_json():
    assert parse_symbol_lots("XAUUSD=0.10\nBTCUSD:1") == {"XAUUSD": 0.10, "BTCUSD": 1.0}
    assert parse_symbol_lots('{"GOLD": 0.2, "EURUSD": 0.05}') == {
        "XAUUSD": 0.2,
        "EURUSD": 0.05,
    }


def test_fixed_lot_uses_raw_or_broker_symbol_then_default():
    configured = "XAUUSD=0.10\nBTCUSD=1.00"

    assert fixed_lot_for_signal("GOLD", "XAUUSDm", 0.01, configured) == (
        0.10,
        "symbol override (XAUUSD)",
    )
    assert fixed_lot_for_signal("EURUSD", "EURUSDm", 0.01, configured) == (
        0.01,
        "default fixed lot",
    )
