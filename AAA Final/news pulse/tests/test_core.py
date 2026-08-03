from news_pulse.core import discover_gold_symbol, entry_buffer, risk_sized_volume
from news_pulse.state import signal_hash


class Symbol:
    def __init__(self, name: str, description: str, trade_mode: int = 4) -> None:
        self.name = name
        self.description = description
        self.path = "Forex\\Metals"
        self.trade_mode = trade_mode


def test_discovers_broker_gold_alias() -> None:
    assert discover_gold_symbol([Symbol("EURUSD", "Euro vs US Dollar"), Symbol("XAUUSDm", "Gold vs US Dollar")]).name == "XAUUSDm"


def test_buffer_only_uses_largest_constraint() -> None:
    assert entry_buffer(broker_min=0.3, configured_min=0.2, spread=0.4, spread_multiplier=2, atr=3, atr_multiplier=0.1) == 0.8


def test_minimum_lot_never_exceeds_risk() -> None:
    assert risk_sized_volume(cash_risk=5, loss_per_lot=1000, minimum=0.01, maximum=10, step=0.01) is None
    assert risk_sized_volume(cash_risk=20, loss_per_lot=1000, minimum=0.01, maximum=10, step=0.01) == 0.02


def test_signal_hash_is_stable() -> None:
    assert signal_hash("PPI", 1, 2) == signal_hash("PPI", 1, 2)
