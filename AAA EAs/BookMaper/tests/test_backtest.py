from __future__ import annotations

import numpy as np
import pandas as pd

from bookmaper.backtest import RegimeEAConfig, simulate_regime_ea


def test_backtest_returns_a_complete_metric_set() -> None:
    index = pd.date_range("2020-01-01", periods=700, freq="D")
    close = pd.Series(100 + np.sin(np.arange(700) / 15) * 8 + np.arange(700) * 0.03, index=index)
    frame = pd.DataFrame(
        {
            "Open": close.shift(1).fillna(close.iloc[0]),
            "High": close + 1.0,
            "Low": close - 1.0,
            "Close": close,
            "Volume": 1_000,
        },
        index=index,
    )
    result = simulate_regime_ea(
        frame,
        RegimeEAConfig(window=10, threshold=0.02),
        start="2021-06-01",
        end="2021-11-30",
        roundtrip_cost_bps=5.0,
    )
    assert result["metrics"]["initial_balance"] == 10_000.0
    assert result["metrics"]["trades"] >= 0
    assert len(result["equity"]) > 0
