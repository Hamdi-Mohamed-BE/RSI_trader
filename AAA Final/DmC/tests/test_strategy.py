from datetime import datetime, time
from pathlib import Path

import pandas as pd

from dmc_bot.config import Config, InstrumentSettings
from dmc_bot.strategy import (
    body_level_gain_failure,
    build_plans,
    hourly_gain_failure,
    idea_comment,
    next_body_target,
)


def _config() -> Config:
    return Config(
        root=Path("."), canonical_symbol="US100", enable_trading=False,
        dry_run=True, live_unlock="", risk_pct=2.0, magic=1,
        ny_timezone="America/New_York", ny_open=time(9, 30),
        pending_expiry=time(16, 0), h4_hours=4,
        d1_min_body_fraction=0.2, h4_min_body_fraction=0.2,
        strong_body_fraction=0.5, pullback_points=25.0,
        stop_points=55.0, trail_start_r=1.0, trail_distance_r=1.0,
        max_hold_hours=72, max_trades_per_week=3, poll_seconds=15,
        deviation_points=30, max_spread_points=12.0,
        comment_reason="D1+H4 aligned",
    )


def test_comment_contract_and_mt5_limit():
    value = idea_comment("A+", "D1+H4 aligned")
    assert value == "DmC A+ D1+H4 aligned"
    assert len(value) <= 31


def test_per_instrument_profile_overrides_execution_distances():
    base = _config()
    gold = InstrumentSettings("XAUUSD", 22.5, 2.0, 1.5, 24, 40.0)
    configured = Config(
        **{
            **{name: getattr(base, name) for name in base.__dataclass_fields__},
            "instruments": (gold,),
        }
    )
    selected = configured.for_instrument("xauusd")
    assert selected.canonical_symbol == "XAUUSD"
    assert selected.stop_points == 22.5
    assert selected.trail_start_r == 2.0
    assert selected.max_spread_points == 40.0


def test_daily_and_market_open_h4_must_align():
    ny = "America/New_York"
    previous = pd.DataFrame(
        {
            "time": pd.to_datetime(["2026-07-30 14:00", "2026-07-30 20:00"], utc=True),
            "open": [100.0, 105.0], "high": [107.0, 112.0],
            "low": [98.0, 104.0], "close": [105.0, 110.0],
            "tick_volume": [1, 1], "spread": [1, 1], "real_volume": [0, 0],
        }
    )
    h4_times = pd.date_range("2026-07-31 09:30", periods=240, freq="min", tz="UTC")
    h4 = pd.DataFrame(
        {
            "time": h4_times,
            "open": [110.0] * 240, "high": [122.0] * 240,
            "low": [109.0] * 240, "close": [120.0] * 240,
            "tick_volume": [1] * 240, "spread": [1] * 240,
            "real_volume": [0] * 240,
        }
    )
    plans = build_plans(pd.concat([previous, h4], ignore_index=True), _config())
    assert len(plans) == 1
    assert plans[0].side == 1
    assert plans[0].rank == "A+"
    assert plans[0].entry == 95.0
    assert plans[0].initial_stop == 40.0


def test_hourly_gain_and_failure_use_previous_candle_body():
    previous = (100.0, 112.0, 95.0, 110.0)
    assert hourly_gain_failure(previous, (108.0, 115.0, 106.0, 113.0)) == (
        1,
        110.0,
        "gain_high",
    )
    assert hourly_gain_failure(previous, (108.0, 114.0, 103.0, 107.0)) == (
        -1,
        110.0,
        "fail_high",
    )
    assert hourly_gain_failure(previous, (102.0, 106.0, 94.0, 101.0)) == (
        1,
        100.0,
        "fail_low",
    )


def test_next_body_target_respects_direction_and_r_limits():
    levels = [80.0, 95.0, 108.0, 120.0, 140.0]
    assert next_body_target(levels, 100.0, 90.0, 1, 0.5, 3.0) == 108.0
    assert next_body_target(levels, 100.0, 110.0, -1, 0.5, 3.0) == 95.0


def test_body_level_gain_failure_uses_nearest_aligned_reaction():
    levels = [90.0, 100.0, 110.0]
    assert body_level_gain_failure(
        levels, (99.0, 102.0, 98.0, 101.0), side_hint=1
    ) == (1, 100.0, "gain_high")
    assert body_level_gain_failure(
        levels, (99.0, 101.0, 96.0, 98.0), side_hint=-1
    ) == (-1, 100.0, "fail_high")
