import asyncio
from app.llm.parser import extract_symbol_raw, merge_deterministic_fields, parse_determinist, parse_signal
from app.llm.schemas import SignalParseSchema

def test_parse_determinist_market_buy():
    msg = """
    USDCAD BUY NOW
    STOPLOSS @ 1.41425
    
    TP @ 1.41750
    TP @ 1.41875
    TP @ 1.42050
    """
    
    result = parse_determinist(msg)
    assert result is not None
    assert result.is_signal is True
    assert result.symbol_raw == "USDCAD"
    assert result.side == "buy"
    assert result.order_type == "market"
    assert result.stop_loss == 1.41425
    assert len(result.take_profits) == 3
    assert result.take_profits == [1.41750, 1.41875, 1.42050]
    assert result.final_take_profit == 1.42050
    assert result.break_even_trigger_tp == 1.41750

def test_parse_determinist_pending_sell():
    msg = """
    SELL LIMIT GOLD @ 2355.50
    SL: 2362.00
    TP1: 2348.00
    TP2: 2340.00
    """
    
    result = parse_determinist(msg)
    assert result is not None
    assert result.symbol_raw == "GOLD"
    assert result.side == "sell"
    assert result.order_type == "pending"
    assert result.pending_type == "sell_limit"
    assert result.entry_price == 2355.50
    assert result.stop_loss == 2362.00
    # Sell TP list should be sorted descending
    assert result.take_profits == [2348.00, 2340.00]
    assert result.final_take_profit == 2340.00
    assert result.break_even_trigger_tp == 2348.00


def test_parse_determinist_xauusd_pending_sell_limit_with_at_entry():
    msg = """
    XAUUSD SELL LIMIT AT 4115
    SL 4140
    TP 4077
    """

    result = parse_determinist(msg)

    assert result is not None
    assert result.symbol_raw == "XAUUSD"
    assert result.side == "sell"
    assert result.order_type == "pending"
    assert result.pending_type == "sell_limit"
    assert result.entry_price == 4115
    assert result.stop_loss == 4140
    assert result.take_profits == [4077]


def test_parse_determinist_split_gold_range_signal_without_symbol():
    msg = """
    BUY LIMIT 4087 - 4085 Sl 4082
    TP 4092 4102 4112 4122 4132 4142
    """

    result = parse_determinist(msg)

    assert result is not None
    assert result.symbol_raw == "XAUUSD"
    assert result.side == "buy"
    assert result.order_type == "pending"
    assert result.pending_type == "buy_limit"
    assert result.entry_price == 4085
    assert result.stop_loss == 4082
    assert result.take_profits == [4092, 4102, 4112, 4122, 4132, 4142]
    assert result.final_take_profit == 4142
    assert result.break_even_trigger_tp == 4092


def test_extract_symbol_raw_is_context_based_not_whitelist():
    examples = {
        "**GBPNZD SELL NOW**\nSTOPLOSS @ 2.35770\nTP @ 2.34100": "GBPNZD",
        "CADJPY SELL NOW STOPOSS @ 114.260 TP @ 113.900": "CADJPY",
        "SELL LIMIT GOLD @ 2355.50\nSL 2362\nTP 2348": "GOLD",
        "BUY NOW XAUUSD\nSL 4043\nTP 4067": "XAUUSD",
        "US500 SELL STOP @ 6500\nSL 6550\nTP 6400": "US500",
        "BTCUSD BUY LIMIT 62000\nSL 61000\nTP 64000": "BTCUSD",
    }

    for message, expected in examples.items():
        assert extract_symbol_raw(message) == expected


def test_parse_determinist_accepts_common_stoploss_typos():
    msg = "CADJPY SELL NOW STOPOSS @ 114.260 TP @ 113.900"

    result = parse_determinist(msg)

    assert result is not None
    assert result.symbol_raw == "CADJPY"
    assert result.side == "sell"
    assert result.stop_loss == 114.260
    assert result.take_profits == [113.900]


def test_parse_signal_repairs_missing_llm_symbol_from_deterministic_parser(monkeypatch):
    msg = """
    XAUUSD SELL LIMIT AT 4115
    SL 4140
    TP 4077
    """

    async def fake_parse_message(*args, **kwargs):
        return SignalParseSchema(
            is_signal=True,
            confidence=1.0,
            ignore_reason=None,
            message_type="signal",
            symbol_raw=None,
            side="sell",
            order_type="pending",
            pending_type="sell_limit",
            entry_price=4115.0,
            stop_loss=4140.0,
            take_profits=[4077.0],
            final_take_profit=4077.0,
            break_even_trigger_tp=4077.0,
            risk_warnings=[],
            parser_notes=[],
        )

    monkeypatch.setattr("app.llm.parser.gemini_client.parse_message", fake_parse_message)

    result = asyncio.run(parse_signal(msg))

    assert result.symbol_raw == "XAUUSD"
    assert "Repaired missing fields from deterministic text parser." in result.parser_notes


def test_merge_repairs_missing_symbol_from_gold_price_context():
    primary = SignalParseSchema(
        is_signal=True,
        confidence=1.0,
        ignore_reason=None,
        message_type="signal",
        symbol_raw=None,
        side="buy",
        order_type="pending",
        pending_type="buy_limit",
        entry_price=4065.0,
        stop_loss=4055.0,
        take_profits=[4150.0],
        final_take_profit=4150.0,
        break_even_trigger_tp=4065.0,
        risk_warnings=[],
        parser_notes=[],
    )

    repaired = merge_deterministic_fields(primary, None, "Buy limit 4065 SL 4055 TP 4150")

    assert repaired.symbol_raw == "XAUUSD"


def test_parse_determinist_missing_elements():
    # Missing SL
    msg_no_sl = "EURUSD BUY NOW TP: 1.0950"
    assert parse_determinist(msg_no_sl) is None

    # Missing TP
    msg_no_tp = "EURUSD BUY NOW SL: 1.0800"
    assert parse_determinist(msg_no_tp) is None
    
    # Non-signal text
    msg_chat = "Good morning traders! Hope you have a great trading day."
    assert parse_determinist(msg_chat) is None
