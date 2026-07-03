from datetime import datetime, timedelta
from types import SimpleNamespace

import pandas as pd

from app import strategy_engine
from app.config import load_config
from app.automation import (
    TradeAutomation,
    _oldest_profitable_position,
    _same_direction_pending_orders,
    _same_direction_positions,
)
from app.scanner import _closed_candles
from app.mt5_client import MT5Client


def _candles(count: int = 80) -> pd.DataFrame:
    start = datetime(2026, 7, 1)
    return pd.DataFrame(
        [
            {
                "time": start + timedelta(minutes=15 * index),
                "open": 100.0,
                "high": 100.4,
                "low": 99.6,
                "close": 100.1,
                "volume": 100.0,
                "volume_source": "tick_volume_proxy",
            }
            for index in range(count)
        ]
    )


def test_closed_candles_excludes_the_unfinished_bar() -> None:
    candles = _candles(4)

    closed = _closed_candles(candles, "M15", datetime(2026, 7, 1, 0, 52))

    assert len(closed) == 3
    assert closed.iloc[-1]["time"] == datetime(2026, 7, 1, 0, 30)


def test_directional_exposure_blocks_only_matching_side() -> None:
    positions = [{"type": 0, "ticket": 1}, {"type": 1, "ticket": 2}]
    pending = [{"type": 2, "ticket": 3}, {"type": 5, "ticket": 4}]

    assert [item["ticket"] for item in _same_direction_positions(positions, "BUY")] == [1]
    assert [item["ticket"] for item in _same_direction_positions(positions, "SELL")] == [2]
    assert [item["ticket"] for item in _same_direction_pending_orders(pending, "BUY")] == [3]
    assert [item["ticket"] for item in _same_direction_pending_orders(pending, "SELL")] == [4]


def test_oldest_profitable_position_excludes_flat_and_losing_trades() -> None:
    positions = [
        {"ticket": 1, "time": 100, "profit": -2.0},
        {"ticket": 2, "time": 300, "profit": 5.0},
        {"ticket": 3, "time": 200, "profit": 1.0},
        {"ticket": 4, "time": 50, "profit": 0.0},
    ]

    selected = _oldest_profitable_position(positions)

    assert selected is not None
    assert selected["ticket"] == 3


def test_profitable_same_direction_signal_updates_only_tp() -> None:
    class FakeClient:
        def __init__(self) -> None:
            self.calls = []

        @staticmethod
        def normalize_price(_symbol: str, price: float) -> float:
            return round(price, 2)

        def modify_position_sl_tp(self, **kwargs):
            self.calls.append(kwargs)
            return {"modified": True, "message": "done"}

    client = FakeClient()
    bot = SimpleNamespace(
        client=client,
        config=SimpleNamespace(live_trading=True),
        auto_place_trades=True,
    )
    signal = {"symbol": "XAUUSD", "direction": "BUY", "take_profit": 3400.0}
    positions = [
        {
            "ticket": 91,
            "symbol": "XAUUSDm",
            "type": 0,
            "time": 100,
            "profit": 12.5,
            "volume": 0.03,
            "sl": 3310.0,
            "tp": 3380.0,
        }
    ]

    action = TradeAutomation._refresh_profitable_position_target(
        bot,
        signal,
        positions,
        {"bid": 3350.0, "ask": 3350.2},
        datetime(2026, 7, 1, 12, 0),
    )

    assert action is not None
    assert action["status"] == "target_refreshed"
    assert client.calls == [
        {
            "ticket": 91,
            "symbol": "XAUUSDm",
            "stop_loss": 3310.0,
            "take_profit": 3400.0,
        }
    ]
    assert action["position_volume"] == 0.03


def test_market_entry_blocks_a_chased_confirmation() -> None:
    bot = SimpleNamespace(market_max_chase_atr=0.35)
    signal = {
        "direction": "BUY",
        "confirmation_price": 3300.0,
        "entry": 3300.0,
        "stop_loss": 3290.0,
        "atr": 10.0,
    }

    accepted = TradeAutomation._market_entry_reasons(bot, signal, {"ask": 3303.0, "bid": 3302.8})
    chased = TradeAutomation._market_entry_reasons(bot, signal, {"ask": 3304.0, "bid": 3303.8})

    assert accepted == []
    assert "wait for the book-aligned pullback" in chased[0]


def test_preentry_prefers_book_retest_over_higher_scored_break_stop(monkeypatch) -> None:
    candles = _candles()
    level = {"price": 100.0, "profile_type": "Previous Daily", "key_level": "PD PoC"}
    limit = {
        "direction": "BUY",
        "setup_score": 85,
        "risk_reward": 5.0,
        "entry_model": "Pending Entry Model 2 - LTF Swing Retest",
        "execution_type": "PENDING",
        "pending_order_type": "BUY_LIMIT",
        "book_aligned_retest": True,
        "reasons": [],
    }
    stop = {
        "direction": "BUY",
        "setup_score": 89,
        "risk_reward": 5.0,
        "entry_model": "Pending Entry Model 3 - Internal Structure Break",
        "execution_type": "PENDING",
        "pending_order_type": "BUY_STOP",
        "reasons": [],
    }
    monkeypatch.setattr(strategy_engine, "_recent_aoi", lambda _df: level)
    monkeypatch.setattr(strategy_engine, "_preentry_direction", lambda _df, _level: "BUY")
    monkeypatch.setattr(
        strategy_engine,
        "detect_entry_confirmation",
        lambda _df, _level, _direction: {"confirmed": False},
    )
    monkeypatch.setattr(strategy_engine, "_profile_retest_preentry", lambda *_args: limit)
    monkeypatch.setattr(strategy_engine, "_supply_demand_retest_preentry", lambda *_args: None)
    monkeypatch.setattr(strategy_engine, "_structure_break_preentry", lambda *_args: stop)

    candidate = strategy_engine.generate_preentry_candidate(candles, "XAUUSD", "M15", min_score=85)

    assert candidate is not None
    assert candidate["pending_order_type"] == "BUY_LIMIT"
    assert candidate["entry_model"].startswith("Pending Entry Model 2")


def test_supply_demand_candidate_uses_fresh_base_before_expansion() -> None:
    candles = _candles(60)
    candles.loc[57, ["open", "high", "low", "close", "volume"]] = [100.1, 100.3, 99.9, 100.0, 100.0]
    candles.loc[58, ["open", "high", "low", "close", "volume"]] = [100.0, 100.2, 99.8, 100.05, 100.0]
    candles.loc[59, ["open", "high", "low", "close", "volume"]] = [100.1, 102.0, 100.0, 101.8, 220.0]
    level = {
        "price": 100.0,
        "tolerance": 0.2,
        "profile_type": "Previous Daily",
        "key_level": "PD PoC",
        "priority": 20,
        "confluence": 2,
    }

    candidate = strategy_engine._supply_demand_retest_preentry(
        strategy_engine._to_frame(candles),
        level,
        "BUY",
        "M15",
        1.0,
    )

    assert candidate is not None
    assert candidate["pending_order_type"] == "BUY_LIMIT"
    assert candidate["trigger_price"] == 100.2
    assert candidate["supply_demand_zone"]["kind"] == "demand"
    assert candidate["supply_demand_zone"]["fresh"] is True


def test_lot_sizing_mode_loads_static_and_risk_percent(monkeypatch) -> None:
    monkeypatch.setenv("LOT_SIZING_MODE", "STATIC_LOT")
    monkeypatch.setenv("STATIC_LOT", "0.08")
    static = load_config()
    assert static.lot_sizing_mode == "STATIC_LOT"
    assert static.static_lot == 0.08

    monkeypatch.setenv("LOT_SIZING_MODE", "RISK_PERCENT")
    risk = load_config()
    assert risk.lot_sizing_mode == "RISK_PERCENT"


def test_static_lot_is_normalized_and_reports_estimated_risk(monkeypatch) -> None:
    client = MT5Client()
    monkeypatch.setattr(client, "resolve_symbol", lambda symbol: f"{symbol}m")
    monkeypatch.setattr(client, "normalize_lot", lambda _symbol, lot: round(lot, 2))
    monkeypatch.setattr(
        client,
        "lot_constraints",
        lambda _symbol: {"min": 0.01, "max": 100.0, "step": 0.01},
    )
    monkeypatch.setattr(client, "account_info", lambda: {"balance": 300.0})
    monkeypatch.setattr(
        client,
        "estimate_trade_risk",
        lambda *_args: {"ok": True, "risk": 15.0, "method": "test"},
    )
    signal = {
        "symbol": "XAUUSD",
        "direction": "BUY",
        "entry": 3300.0,
        "stop_loss": 3290.0,
        "execution_type": "MARKET",
    }

    sizing = client.static_lot_sizing(
        signal,
        configured_lot=0.08,
        quote={"bid": 3300.0, "ask": 3300.2},
    )

    assert sizing["ok"] is True
    assert sizing["mode"] == "static_lot"
    assert sizing["lot"] == 0.08
    assert sizing["broker_symbol"] == "XAUUSDm"
    assert sizing["estimated_risk"] == 15.0
    assert sizing["actual_risk_percent"] == 5.0


def test_automation_selects_the_configured_lot_sizing_path() -> None:
    class FakeClient:
        def __init__(self) -> None:
            self.calls: list[tuple[str, float]] = []

        def static_lot_sizing(self, _signal, lot, quote=None):
            self.calls.append(("static", lot))
            return {"ok": True, "lot": lot, "quote": quote}

        def risk_based_lot(self, _signal, risk_percent, **_kwargs):
            self.calls.append(("risk", risk_percent))
            return {"ok": True, "lot": 0.03}

    client = FakeClient()
    bot = SimpleNamespace(
        client=client,
        lot_sizing_mode="STATIC_LOT",
        static_lot=0.08,
        max_lot_risk_pct=5.0,
        config=SimpleNamespace(starting_balance=300.0),
    )
    signal = {"symbol": "XAUUSD", "direction": "BUY"}

    static = TradeAutomation._size_lot(bot, signal, quote=None, require_account_balance=True)
    bot.lot_sizing_mode = "RISK_PERCENT"
    risk = TradeAutomation._size_lot(bot, signal, quote=None, require_account_balance=True)

    assert static["lot"] == 0.08
    assert risk["lot"] == 0.03
    assert client.calls == [("static", 0.08), ("risk", 5.0)]


def test_pending_orders_require_a_plus_grade_and_score_92() -> None:
    bot = SimpleNamespace(preplace_min_score=92)

    accepted = TradeAutomation._pending_quality_reasons(
        bot,
        {"setup_score": 92, "setup_grade": "PRE-A+"},
    )
    low_score = TradeAutomation._pending_quality_reasons(
        bot,
        {"setup_score": 91, "setup_grade": "PRE-A+"},
    )
    low_grade = TradeAutomation._pending_quality_reasons(
        bot,
        {"setup_score": 95, "setup_grade": "WATCH"},
    )

    assert accepted == []
    assert "score >= 92" in low_score[0]
    assert "A+ or PRE-A+" in low_grade[0]
