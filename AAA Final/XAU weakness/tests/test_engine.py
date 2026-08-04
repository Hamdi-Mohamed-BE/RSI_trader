import pandas as pd

from xau_weakness.config import StrategyConfig
from xau_weakness.engine import prepare, setup_at


def _frame():
    values = []
    price = 100.0
    for index in range(40):
        if 20 <= index < 26:
            opened = price
            price -= 1.0
            values.append((opened, opened + 0.1, price - 0.1, price, 5))
        else:
            values.append((price, price + 0.3, price - 0.3, price, 5))
    values[27] = (94.0, 95.0, 93.5, 94.5, 5)
    values[28] = (94.5, 94.7, 93.8, 94.1, 5)
    values[29] = (94.1, 94.6, 93.7, 94.0, 5)
    values[30] = (94.0, 95.05, 93.6, 94.4, 5)
    return pd.DataFrame(values, columns=["open", "high", "low", "close", "spread"], index=pd.date_range("2026-01-01", periods=40, freq="15min", tz="UTC"))


def test_detects_bearish_impulse_double_high():
    frame = prepare(_frame())
    config = StrategyConfig(
        impulse_bars=6, impulse_atr=0.5, test_tolerance_atr=0.3, min_test_gap=2,
        max_test_gap=5, rejection_atr=0.05, max_range_atr=5,
    )
    setup = setup_at(frame, 31, config)
    assert setup is not None
    assert setup.entry > 95.0
    assert setup.stop < 93.6


def test_rejects_non_bearish_history():
    frame = prepare(_frame())
    config = StrategyConfig(impulse_atr=20, max_range_atr=5)
    assert setup_at(frame, 31, config) is None
