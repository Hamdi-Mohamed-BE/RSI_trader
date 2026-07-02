from naw_lta.engine.strategy import SignalDecision
from naw_lta.schemas import RuntimeConfig
from types import SimpleNamespace

from naw_lta.services import mt5_execution
from naw_lta.services.mt5_execution import MT5Bridge


def test_mt5_bridge_never_places_a_watch_decision():
    config = RuntimeConfig(mt5_live_orders_enabled=True, execution_mode="mt5")
    decision = SignalDecision(
        symbol="XAUUSD",
        timestamp="2026-07-02T00:00:00+00:00",
        direction="FLAT",
        status="WATCH",
        score=0.0,
        regime="BALANCED",
        order_type=None,
        entry=None,
        stop_loss=None,
        take_profit=None,
        reward_risk=4.0,
        reasons=[],
        profile={},
        order_book={},
        trade_flow={},
        indicators={},
    )
    assert MT5Bridge().place(None, decision, config, config.symbols["XAUUSD"], 0.0) is None


def test_mt5_risk_sizing_forces_broker_minimum(monkeypatch):
    monkeypatch.setattr(mt5_execution.mt5, "order_calc_profit", lambda *_args: -1000.0)
    info = SimpleNamespace(volume_min=0.1, volume_max=100.0, volume_step=0.01)
    volume, actual_risk, minimum_forced = MT5Bridge._risk_volume(
        "XAUUSDm", mt5_execution.mt5.ORDER_TYPE_BUY, 4000.0, 3990.0, 1.0, info
    )
    assert volume == 0.1
    assert actual_risk == 100.0
    assert minimum_forced is True
