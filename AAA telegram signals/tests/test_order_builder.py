import pytest
from unittest.mock import patch, MagicMock
import MetaTrader5 as mt5
from app.trading.order_builder import OrderBuilder, MAGIC_NUMBER

@patch("app.trading.order_builder.mt5_client")
def test_build_request_market_buy(mock_client):
    # Mock symbol specs
    mock_client.get_symbol_info.return_value = {
        "filling_mode": 1
    }
    # Mock current tick price
    mock_client.get_tick.return_value = {
        "ask": 1.10200,
        "bid": 1.10180
    }
    
    request = OrderBuilder.build_request(
        symbol="EURUSDm",
        side="buy",
        order_type="market",
        lot=0.05,
        stop_loss=1.09500,
        take_profit=1.11000
    )
    
    assert request["symbol"] == "EURUSDm"
    assert request["volume"] == 0.05
    assert request["magic"] == MAGIC_NUMBER
    assert request["action"] == mt5.TRADE_ACTION_DEAL
    assert request["type"] == mt5.ORDER_TYPE_BUY
    assert request["price"] == 1.10200
    assert request["sl"] == 1.09500
    assert request["tp"] == 1.11000
    assert request["type_filling"] == mt5.ORDER_FILLING_FOK

@patch("app.trading.order_builder.mt5_client")
def test_build_request_pending_sell_limit(mock_client):
    mock_client.get_symbol_info.return_value = {
        "filling_mode": 2
    }
    
    request = OrderBuilder.build_request(
        symbol="GBPUSD",
        side="sell",
        order_type="pending",
        pending_type="sell_limit",
        lot=0.10,
        entry_price=1.28500,
        stop_loss=1.29000,
        take_profit=1.27500
    )
    
    assert request["symbol"] == "GBPUSD"
    assert request["volume"] == 0.10
    assert request["action"] == mt5.TRADE_ACTION_PENDING
    assert request["type"] == mt5.ORDER_TYPE_SELL_LIMIT
    assert request["price"] == 1.28500
    assert request["sl"] == 1.29000
    assert request["tp"] == 1.27500
    assert request["type_filling"] == mt5.ORDER_FILLING_RETURN
