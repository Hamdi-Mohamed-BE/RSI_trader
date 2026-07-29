from datetime import time
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from orb2.config import RuntimeConfig, StrategyConfig
from orb2.engine import simulate_signal
from orb2.models import Signal


def runtime() -> RuntimeConfig:
    return RuntimeConfig(
        root=Path("."),
        mt5_path="",
        symbols=("XAUUSD",),
        timezone_name="America/New_York",
        range_start=time(9, 30),
        range_minutes=15,
        last_entry=time(12),
        flat_time=time(16),
        backtest_days=60,
        starting_balance=300,
        risk_percent=1,
        max_trades_per_symbol_day=1,
        max_daily_losses=2,
        slippage_points=0,
        cache_data=False,
        live_trading=False,
        place_trades=False,
        poll_seconds=10,
        magic=1,
        comment="TEST",
        fixed_lot=0,
        deviation_points=10,
    )


def signal() -> Signal:
    return Signal(
        symbol="XAUUSD",
        session_date="2026-07-20",
        model="retest",
        direction="buy",
        signal_time="2026-07-20T09:45:00-04:00",
        signal_index=0,
        or_high=100,
        or_low=99,
        stop_reference=99,
        target_reference=None,
        atr=1,
        spread_points=0,
        body_ratio=0.8,
        relative_volume=1.5,
        fvg_confluence=False,
        liquidity_confluence=False,
    )


def bars(low: float) -> pd.DataFrame:
    index = pd.DatetimeIndex(
        ["2026-07-20T09:45:00-04:00", "2026-07-20T09:50:00-04:00"]
    )
    return pd.DataFrame(
        {
            "open": [100, 100],
            "high": [100.5, 103.1],
            "low": [99.5, low],
            "close": [100, 103],
            "spread": [0, 0],
        },
        index=index,
    )


def test_partial_is_applied_before_final_target() -> None:
    config = StrategyConfig(
        target_rr=3,
        partial_at_r=2,
        partial_fraction=0.5,
    )
    trade = simulate_signal(bars(99.5), signal(), runtime(), config, 0.01, 300)
    assert trade is not None
    assert trade.r_multiple == 2.5


def test_stop_first_when_stop_and_target_share_a_bar() -> None:
    config = StrategyConfig(target_rr=3, partial_fraction=0.5)
    trade = simulate_signal(bars(98.5), signal(), runtime(), config, 0.01, 300)
    assert trade is not None
    assert trade.r_multiple == -1
    assert trade.outcome == "stop"
