import numpy as np
import pandas as pd

from naw_lta.engine.strategy import LtaOrderFlowEngine
from naw_lta.schemas import RuntimeConfig


def test_strategy_returns_structured_decision():
    index = pd.date_range("2026-01-01", periods=180, freq="15min", tz="UTC")
    close = np.linspace(100, 120, len(index)) + np.sin(np.arange(len(index)) / 4)
    frame = pd.DataFrame(
        {
            "open": close - 0.2,
            "high": close + 0.6,
            "low": close - 0.7,
            "close": close,
            "volume": 100 + (np.arange(len(index)) % 20) * 5,
        },
        index=index,
    )
    decision = LtaOrderFlowEngine(RuntimeConfig()).evaluate("XAUUSD", frame)
    assert decision.direction in {"BUY", "SELL", "FLAT"}
    assert 0 <= decision.score <= 100
    assert decision.profile["source"] == "ohlcv-1m"
