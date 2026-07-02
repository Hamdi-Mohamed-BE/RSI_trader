from types import SimpleNamespace

from telegram_mt5_copier import mt5_copier
from telegram_mt5_copier.mt5_copier import MT5Copier


def test_broker_minimum_lot_is_forced(monkeypatch):
    monkeypatch.setattr(mt5_copier.mt5, "order_calc_profit", lambda *_args: -1000.0)
    info = SimpleNamespace(volume_min=0.1, volume_max=100.0, volume_step=0.01)
    volume, actual_risk, forced = MT5Copier._risk_volume(
        "XAUUSDm", mt5_copier.mt5.ORDER_TYPE_BUY, 4300.0, 4290.0, 1.0, info
    )
    assert volume == 0.1
    assert actual_risk == 100.0
    assert forced is True
