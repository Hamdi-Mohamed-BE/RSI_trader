from types import SimpleNamespace

import MetaTrader5 as mt5

from asia_breakout.live import _account_board, trailing_stop_candidate


def test_buy_trailing_waits_for_start_and_only_advances() -> None:
    assert trailing_stop_candidate("buy", 100, 90, 90, 119, 2, 1) is None
    assert trailing_stop_candidate("buy", 100, 90, 90, 120, 2, 1) == 110
    assert trailing_stop_candidate("buy", 100, 90, 112, 120, 2, 1) is None


def test_sell_trailing_waits_for_start_and_only_advances() -> None:
    assert trailing_stop_candidate("sell", 100, 110, 110, 81, 2, 1) is None
    assert trailing_stop_candidate("sell", 100, 110, 110, 80, 2, 1) == 90
    assert trailing_stop_candidate("sell", 100, 110, 88, 80, 2, 1) is None


def test_account_board_displays_live_equity_and_margin() -> None:
    account = SimpleNamespace(
        login=12345,
        trade_mode=mt5.ACCOUNT_TRADE_MODE_REAL,
        server="Broker-Live",
        currency="USD",
        leverage=500,
        balance=1_000.0,
        equity=1_025.5,
        margin_free=900.25,
        profit=25.5,
        trade_allowed=True,
    )
    board = _account_board(account)
    assert "LIVE" in board
    assert "1,025.50" in board
    assert "900.25" in board
