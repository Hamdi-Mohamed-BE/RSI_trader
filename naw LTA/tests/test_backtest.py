from datetime import datetime, timezone

import pandas as pd

from naw_lta.engine.backtest import calculate_metrics, in_enabled_session
from naw_lta.schemas import RuntimeConfig


def test_weekend_is_never_tradeable_by_default():
    config = RuntimeConfig()
    saturday = pd.Timestamp(datetime(2026, 7, 4, 14, tzinfo=timezone.utc))
    assert not in_enabled_session(saturday, config, "XAUUSD")


def test_metrics_report_growth_and_drawdown():
    trades = [
        {"pnl": 15.0, "r_multiple": 1.0},
        {"pnl": -10.0, "r_multiple": -1.0},
    ]
    metrics = calculate_metrics(trades, 300.0, 305.0, 0.05)
    assert metrics["trades"] == 2
    assert metrics["win_rate"] == 50.0
    assert metrics["ending_balance"] == 305.0
    assert metrics["max_drawdown_percent"] == 5.0

