from __future__ import annotations

import numpy as np
import pandas as pd

from btc_basis.analysis import monte_carlo
from btc_basis.strategy import StrategyConfig, _trade_path_return, detect_reopen_events, performance_metrics


def _frame(index: pd.DatetimeIndex, prices: np.ndarray) -> pd.DataFrame:
    return pd.DataFrame(
        {"open": prices, "high": prices, "low": prices, "close": prices, "volume": 1_000.0},
        index=index,
    )


def test_trade_path_return_directional_and_hedged() -> None:
    assert np.isclose(_trade_path_return("directional", -1, 99.0, 100.0, 105.0, 100.0), 0.01)
    assert np.isclose(_trade_path_return("hedged", -1, 99.0, 100.0, 105.0, 100.0), 0.06)


def test_event_detection_uses_only_history_and_finds_weekend_gap() -> None:
    first = pd.date_range("2025-01-01", periods=120, freq="h", tz="UTC")
    second = pd.date_range(first[-1] + pd.Timedelta(hours=49), periods=8, freq="h", tz="UTC")
    futures_index = first.append(second)
    spot_index = pd.date_range(first[0], second[-1], freq="h", tz="UTC")
    spot_prices = np.full(len(spot_index), 100.0)
    spot_prices[spot_index > first[-1]] = 103.0
    futures_prices = np.linspace(100.0, 100.5, len(futures_index))
    futures_prices[len(first)] = 106.0
    events = detect_reopen_events(
        _frame(spot_index, spot_prices),
        _frame(futures_index, futures_prices),
        StrategyConfig(
            lookback_hours=96,
            minimum_gap_hours=30,
            minimum_spot_move=0.01,
            entry_z=0.5,
            roll_exclusion_days=0,
        ),
    )
    assert len(events) == 1
    assert events.iloc[0]["direction"] == -1


def test_metrics_and_monte_carlo_are_deterministic() -> None:
    returns = pd.Series([0.01, -0.005, 0.02, -0.002])
    trades = pd.DataFrame({"account_return": returns})
    trades["equity"] = (1.0 + returns).cumprod()
    trades["drawdown"] = trades["equity"].div(trades["equity"].cummax()).sub(1.0)
    metrics = performance_metrics(trades)
    assert metrics["trades"] == 4
    assert metrics["profit_factor"] > 4.0
    assert monte_carlo(trades, simulations=200, seed=7) == monte_carlo(trades, simulations=200, seed=7)
