import json
from datetime import datetime
from unittest.mock import MagicMock, patch

from app.db.models import ManagedTrade
from app.trading.trade_manager import TradeManager


def _trade(**overrides):
    defaults = dict(
        order_attempt_id=1,
        mt5_ticket=12345,
        position_identifier=12345,
        symbol_raw="XAUUSD",
        broker_symbol="XAUUSDm",
        side="buy",
        lot=0.10,
        entry_price=2400.0,
        stop_loss_original=2390.0,
        stop_loss_current=2390.0,
        take_profits_json=json.dumps([2410.0, 2420.0, 2430.0]),
        final_take_profit=2430.0,
        break_even_trigger_tp=2410.0,
        break_even_enabled=True,
        break_even_done=False,
        status="active",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    defaults.update(overrides)
    return ManagedTrade(**defaults)


@patch("app.trading.trade_manager.SystemEventRepository")
@patch("app.trading.trade_manager.ManagedTradeRepository")
@patch("app.trading.trade_manager.mt5_client")
def test_trade_manager_moves_be_and_closes_half_at_tp2(mock_mt5, mock_repo, mock_events):
    trade = _trade()
    mock_repo.get_active.return_value = [trade]
    mock_mt5.get_positions.return_value = [{"ticket": 12345, "price_current": 2421.0, "sl": 2390.0, "volume": 0.10}]
    mock_mt5.get_symbol_info.return_value = {"point": 0.01, "digits": 2}
    mock_mt5.modify_position.return_value = (True, None)
    mock_mt5.close_partial_position.return_value = (True, {"retcode": 10009}, None)

    count = TradeManager.process_break_even(MagicMock(), dynamic_offset_points=0)

    assert count == 3
    assert trade.break_even_done is True
    assert trade.stop_loss_current == 2410.0
    assert trade.tp2_partial_done is True
    assert trade.trailing_tp_index == 2
    assert mock_mt5.modify_position.call_count == 2
    mock_mt5.modify_position.assert_any_call(12345, stop_loss=2400.0, take_profit=2430.0)
    mock_mt5.modify_position.assert_any_call(12345, stop_loss=2410.0, take_profit=2430.0)
    mock_mt5.close_partial_position.assert_called_once()
    assert mock_mt5.close_partial_position.call_args.kwargs["volume"] == 0.05


@patch("app.trading.trade_manager.SystemEventRepository")
@patch("app.trading.trade_manager.ManagedTradeRepository")
@patch("app.trading.trade_manager.mt5_client")
def test_trade_manager_does_not_repeat_tp2_partial(mock_mt5, mock_repo, mock_events):
    trade = _trade(break_even_done=True, tp2_partial_done=True)
    mock_repo.get_active.return_value = [trade]
    mock_mt5.get_positions.return_value = [{"ticket": 12345, "price_current": 2425.0, "sl": 2400.0, "volume": 0.05}]
    mock_mt5.get_symbol_info.return_value = {"point": 0.01, "digits": 2}
    mock_mt5.modify_position.return_value = (True, None)

    count = TradeManager.process_break_even(MagicMock(), dynamic_offset_points=0)

    assert count == 1
    assert trade.trailing_tp_index == 2
    mock_mt5.modify_position.assert_called_once_with(12345, stop_loss=2410.0, take_profit=2430.0)
    mock_mt5.close_partial_position.assert_not_called()


@patch("app.trading.trade_manager.SystemEventRepository")
@patch("app.trading.trade_manager.ManagedTradeRepository")
@patch("app.trading.trade_manager.mt5_client")
def test_trade_manager_does_not_repeat_tp_ladder(mock_mt5, mock_repo, mock_events):
    trade = _trade(break_even_done=True, tp2_partial_done=True, trailing_tp_index=2, stop_loss_current=2410.0)
    mock_repo.get_active.return_value = [trade]
    mock_mt5.get_positions.return_value = [{"ticket": 12345, "price_current": 2425.0, "sl": 2410.0, "volume": 0.05}]

    count = TradeManager.process_break_even(MagicMock(), dynamic_offset_points=0)

    assert count == 0
    mock_mt5.modify_position.assert_not_called()
    mock_mt5.close_partial_position.assert_not_called()
