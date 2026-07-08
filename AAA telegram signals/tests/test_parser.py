import pytest
from app.llm.parser import parse_determinist

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
