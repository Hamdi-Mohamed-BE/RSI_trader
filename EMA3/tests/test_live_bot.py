from types import SimpleNamespace

import pandas as pd

from ema3_backtest.live_bot import choose_gold_symbol, confirmed_signal


def test_gold_discovery_accepts_broker_suffix() -> None:
    symbols = [
        SimpleNamespace(
            name="EURUSD.a",
            description="Euro vs US Dollar",
            path="Forex",
            trade_mode=4,
            visible=True,
        ),
        SimpleNamespace(
            name="XAUUSD..",
            description="Gold Spot",
            path="Metals",
            trade_mode=4,
            visible=False,
        ),
    ]
    assert choose_gold_symbol(symbols) == "XAUUSD.."


def test_explicit_gold_hint_wins() -> None:
    symbols = [
        SimpleNamespace(
            name="XAUUSD",
            description="Gold",
            path="Metals",
            trade_mode=4,
            visible=True,
        ),
        SimpleNamespace(
            name="GOLD.pro",
            description="Gold Spot Pro",
            path="Metals",
            trade_mode=4,
            visible=False,
        ),
    ]
    assert choose_gold_symbol(symbols, "GOLD.pro") == "GOLD.pro"


def test_latest_completed_bar_confirms_pivot() -> None:
    distance = 2
    frame = pd.DataFrame(
        {
            "time": pd.date_range("2026-01-01", periods=7, freq="4h", tz="UTC"),
            "open": [10.0] * 7,
            "high": [12.0, 11.0, 10.0, 11.0, 12.0, 13.0, 14.0],
            "low": [8.0, 7.0, 5.0, 7.0, 8.0, 9.0, 10.0],
            "close": [10.0] * 7,
        }
    )
    signal = confirmed_signal(frame.iloc[:5].copy(), distance)
    assert signal is not None
    assert signal["side"] == "buy"
    assert signal["pivot_time"] == frame.at[2, "time"]
