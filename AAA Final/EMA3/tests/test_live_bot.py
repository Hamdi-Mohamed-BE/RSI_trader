from types import SimpleNamespace

import MetaTrader5 as mt5
import pandas as pd

from ema3_backtest.live_bot import (
    choose_gold_symbol,
    confirmed_signal,
    risk_sized_volume,
    send_request,
)


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
    assert signal["pivot_price"] == 5.0


def test_risk_size_rounds_down_without_exceeding_budget(monkeypatch) -> None:
    info = SimpleNamespace(volume_min=0.01, volume_max=100.0, volume_step=0.01)
    monkeypatch.setattr(
        "ema3_backtest.live_bot.mt5.symbol_info",
        lambda *_: info,
    )
    monkeypatch.setattr(
        "ema3_backtest.live_bot.mt5.order_calc_profit",
        lambda *_: -1_000.0,
    )
    volume, actual_risk = risk_sized_volume(
        "XAUUSD",
        "buy",
        entry=4_000.0,
        stop=3_990.0,
        risk_budget=117.38,
        maximum_lot=100.0,
    )
    assert volume == 0.11
    assert actual_risk == 110.0


def test_send_request_checks_filling_before_submission(monkeypatch) -> None:
    info = SimpleNamespace(filling_mode=1)
    accepted = SimpleNamespace(retcode=0, comment="Done")
    sent = SimpleNamespace(
        retcode=mt5.TRADE_RETCODE_DONE,
        comment="Done",
    )
    checks: list[int] = []
    sends: list[int] = []
    monkeypatch.setattr(mt5, "symbol_info", lambda _symbol: info)
    monkeypatch.setattr(
        mt5,
        "order_check",
        lambda request: checks.append(request["type_filling"]) or accepted,
    )
    monkeypatch.setattr(
        mt5,
        "order_send",
        lambda request: sends.append(request["type_filling"]) or sent,
    )
    result = send_request({"symbol": "XAUUSD", "action": 1})
    assert result is sent
    assert checks == [mt5.ORDER_FILLING_FOK]
    assert sends == [mt5.ORDER_FILLING_FOK]
