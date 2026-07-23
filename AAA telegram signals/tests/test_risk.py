import pytest
from unittest.mock import patch, MagicMock
from app.trading.risk import RiskCalculator

@patch("app.trading.risk.mt5_client")
def test_calculate_lot_fixed(mock_client):
    # Mock symbol details
    mock_client.get_symbol_info.return_value = {
        "volume_min": 0.01,
        "volume_max": 100.0,
        "volume_step": 0.01
    }
    mock_client.get_account_info.return_value = {}
    mock_client.calculate_order_profit.return_value = None
    
    lot, warning = RiskCalculator.calculate_lot(
        symbol="EURUSD",
        side="buy",
        entry_price=1.1000,
        stop_loss=1.0900,
        risk_mode="fixed_lot",
        fixed_lot=0.05
    )
    assert lot == 0.05
    assert warning is None

@patch("app.trading.risk.mt5_client")
def test_calculate_lot_usd_cap(mock_client):
    # Mock EURUSD specs where 1 point of EURUSD (0.00001) has tick value of $1.00 for 1 lot.
    # Actually tick size = 0.00001, tick value = 1.0 (for account in USD, 1 pip = 10 points = $10 per lot, meaning tick value = $1.00 for 0.00001 change).
    mock_client.get_symbol_info.return_value = {
        "trade_tick_size": 0.00001,
        "trade_tick_value": 1.0,
        "volume_min": 0.01,
        "volume_max": 100.0,
        "volume_step": 0.01
    }
    mock_client.get_account_info.return_value = {}
    mock_client.calculate_order_profit.return_value = None
    
    # Entry: 1.10000, SL: 1.09500 (distance = 0.00500 or 500 points)
    # Risk Cap: $50
    # Formula: risk_per_lot = (0.00500 / 0.00001) * 1.0 = 500
    # Lot = 50 / 500 = 0.10
    lot, warning = RiskCalculator.calculate_lot(
        symbol="EURUSD",
        side="buy",
        entry_price=1.10000,
        stop_loss=1.09500,
        risk_mode="risk_usd_cap",
        risk_usd_cap=50.0
    )
    assert lot == 0.10
    assert warning is None

@patch("app.trading.risk.mt5_client")
def test_calculate_lot_percentage_risk(mock_client):
    mock_client.get_symbol_info.return_value = {
        "trade_tick_size": 0.00001,
        "trade_tick_value": 1.0,
        "volume_min": 0.01,
        "volume_max": 100.0,
        "volume_step": 0.01
    }
    # Mock account balance
    mock_client.get_account_info.return_value = {
        "equity": 10000.0,
        "balance": 10000.0
    }
    mock_client.calculate_order_profit.return_value = None
    
    # 2% Risk on $10,000 equity = $200 risk amount
    # Entry: 1.10000, SL: 1.09000 (distance = 0.01000 or 1000 points)
    # risk_per_lot = (0.01000 / 0.00001) * 1.0 = 1000
    # Lot = 200 / 1000 = 0.20
    lot, warning = RiskCalculator.calculate_lot(
        symbol="EURUSD",
        side="buy",
        entry_price=1.10000,
        stop_loss=1.09000,
        risk_mode="risk_percent",
        risk_percent=2.0,
        use_equity_instead_of_balance=True
    )
    assert lot == 0.20
    assert warning is None

@patch("app.trading.risk.mt5_client")
def test_calculate_lot_min_volume_warning(mock_client):
    mock_client.get_symbol_info.return_value = {
        "trade_tick_size": 0.00001,
        "trade_tick_value": 1.0,
        "volume_min": 0.01,
        "volume_max": 100.0,
        "volume_step": 0.01
    }
    mock_client.get_account_info.return_value = {}
    mock_client.calculate_order_profit.return_value = None
    
    # Entry: 1.10000, SL: 1.00000 (distance = 0.10000 or 10000 points)
    # Risk Cap: $2.00
    # risk_per_lot = (0.10000 / 0.00001) * 1.0 = 10000
    # Raw Lot = 2 / 10000 = 0.0002 (below 0.01 minimum)
    # Expected: use min lot 0.01 with warning
    lot, warning = RiskCalculator.calculate_lot(
        symbol="EURUSD",
        side="buy",
        entry_price=1.10000,
        stop_loss=1.00000,
        risk_mode="risk_usd_cap",
        risk_usd_cap=2.00,
        allow_min_lot_if_risk_too_small=True
    )
    assert lot == 0.01
    assert warning is not None
    assert "Using broker minimum lot" in warning


@patch("app.trading.risk.mt5_client")
def test_calculate_lot_uses_mt5_profit_engine_before_tick_value(mock_client):
    mock_client.get_symbol_info.return_value = {
        "trade_tick_size": 0.01,
        "trade_tick_value": 1.0,
        "volume_min": 0.01,
        "volume_max": 100.0,
        "volume_step": 0.01
    }
    mock_client.get_account_info.return_value = {"equity": 50000.0, "balance": 50000.0}
    mock_client.calculate_order_profit.side_effect = lambda **kwargs: -1500.0 * kwargs["lot"]

    lot, warning = RiskCalculator.calculate_lot(
        symbol="XAUUSD",
        side="buy",
        entry_price=4100.0,
        stop_loss=4085.0,
        risk_mode="risk_usd_cap",
        risk_usd_cap=100.0,
    )

    assert lot == 0.06
    assert warning is None


@patch("app.trading.risk.mt5_client")
def test_calculate_lot_skips_min_lot_when_it_would_exceed_risk_cap(mock_client):
    mock_client.get_symbol_info.return_value = {
        "trade_tick_size": 0.01,
        "trade_tick_value": 1.0,
        "volume_min": 0.01,
        "volume_max": 100.0,
        "volume_step": 0.01
    }
    mock_client.get_account_info.return_value = {"equity": 50000.0, "balance": 50000.0}
    mock_client.calculate_order_profit.side_effect = lambda **kwargs: -1500.0 * kwargs["lot"]

    lot, warning = RiskCalculator.calculate_lot(
        symbol="XAUUSD",
        side="buy",
        entry_price=4100.0,
        stop_loss=4085.0,
        risk_mode="risk_usd_cap",
        risk_usd_cap=5.0,
        allow_min_lot_if_risk_too_small=True,
    )

    assert lot == 0.0
    assert warning is not None
    assert "above configured cap" in warning
