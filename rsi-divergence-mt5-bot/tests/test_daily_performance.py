import pandas as pd

from rsi_divergence_bot.backtest import _build_daily_performance


def _ts(iso: str) -> int:
    return int(pd.Timestamp(iso).timestamp())


def test_build_daily_performance_includes_trade_rows_with_running_balance():
    closed_trades = [
        {
            "symbol": "EURUSD",
            "side": "buy",
            "entry_time": "2026-05-13T08:00:00+00:00",
            "exit_time": "2026-05-13T10:00:00+00:00",
            "exit_kind": "tp1",
            "pnl": 100.0,
            "sort_time": _ts("2026-05-13T10:00:00+00:00"),
        },
        {
            "symbol": "GBPUSD",
            "side": "sell",
            "entry_time": "2026-05-13T11:00:00+00:00",
            "exit_time": "2026-05-13T12:00:00+00:00",
            "exit_kind": "sl",
            "pnl": -50.0,
            "sort_time": _ts("2026-05-13T12:00:00+00:00"),
        },
        {
            "symbol": "XAUUSD",
            "side": "buy",
            "entry_time": "2026-05-14T09:00:00+00:00",
            "exit_time": "2026-05-14T11:00:00+00:00",
            "exit_kind": "tp2",
            "pnl": 25.0,
            "sort_time": _ts("2026-05-14T11:00:00+00:00"),
        },
    ]

    rows = _build_daily_performance(closed_trades, starting_balance=1000.0)

    assert len(rows) == 2
    assert rows[0]["date"] == "2026-05-13"
    assert rows[0]["start_balance"] == 1000.0
    assert rows[0]["balance"] == 1050.0
    assert len(rows[0]["trade_rows"]) == 2
    assert rows[0]["trade_rows"][0]["balance_after"] == 1100.0
    assert rows[0]["trade_rows"][1]["balance_after"] == 1050.0

    assert rows[1]["date"] == "2026-05-14"
    assert rows[1]["start_balance"] == 1050.0
    assert rows[1]["trade_rows"][0]["balance_after"] == 1075.0
