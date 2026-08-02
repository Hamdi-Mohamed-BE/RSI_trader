from dataclasses import replace
from datetime import date, datetime, timezone

import pandas as pd
import pytest

from amd_bot.article_v2_engine import (
    V2Candidate,
    V2Params,
    _simulate_v2_trade,
    v2_candidates_for_day,
)
from amd_bot.config import load_config


UTC = timezone.utc


def _day_frame() -> pd.DataFrame:
    times = pd.date_range(
        "2026-07-30T00:00:00Z",
        "2026-07-30T12:00:00Z",
        freq="min",
        inclusive="left",
    )
    frame = pd.DataFrame(
        {
            "time": times,
            "open": 105.0,
            "high": 106.0,
            "low": 104.0,
            "close": 105.0,
            "spread": 1,
            "tick_volume": 10,
        }
    )
    frame.loc[10, "high"] = 110.0
    frame.loc[20, "low"] = 100.0
    return frame


def test_v2_reversal_waits_for_fvg_limit_retest() -> None:
    frame = _day_frame()
    sweep = frame["time"].between(
        "2026-07-30T08:00:00Z",
        "2026-07-30T08:04:00Z",
    )
    frame.loc[sweep, ["open", "high", "low", "close"]] = [
        109.0,
        112.0,
        107.0,
        109.5,
    ]
    displacement = frame["time"].between(
        "2026-07-30T08:05:00Z",
        "2026-07-30T08:09:00Z",
    )
    frame.loc[displacement, ["open", "high", "low", "close"]] = [
        103.7,
        103.8,
        102.0,
        102.2,
    ]
    retest = frame["time"].between(
        "2026-07-30T08:10:00Z",
        "2026-07-30T08:14:00Z",
    )
    frame.loc[retest, ["open", "high", "low", "close"]] = [
        103.0,
        104.0,
        102.8,
        103.2,
    ]
    config = replace(load_config(), regime_filter_enabled=False)
    params = V2Params(
        enable_reversal=True,
        enable_continuation=False,
        use_regime_filter=False,
        displacement_range_factor=0.8,
        max_risk_fraction=1.0,
    )
    candidates, asia_high, asia_low = v2_candidates_for_day(
        frame,
        0.01,
        config,
        params,
        date(2026, 7, 30),
    )
    assert asia_high == 110.0
    assert asia_low == 100.0
    assert len(candidates) == 1
    assert candidates[0].phase == "london_v2_reversal"
    assert candidates[0].side == "sell"
    assert candidates[0].signal_time == datetime(
        2026,
        7,
        30,
        8,
        10,
        tzinfo=UTC,
    )
    assert candidates[0].entry_time == datetime(
        2026,
        7,
        30,
        8,
        10,
        tzinfo=UTC,
    )


def test_v2_continuation_requires_breakout_and_hold() -> None:
    frame = _day_frame()
    breakout = frame["time"].between(
        "2026-07-30T08:00:00Z",
        "2026-07-30T08:04:00Z",
    )
    frame.loc[breakout, ["open", "high", "low", "close"]] = [
        109.5,
        112.0,
        109.8,
        111.5,
    ]
    retest = frame["time"].between(
        "2026-07-30T08:05:00Z",
        "2026-07-30T08:09:00Z",
    )
    frame.loc[retest, ["open", "high", "low", "close"]] = [
        110.1,
        111.0,
        109.9,
        110.7,
    ]
    config = replace(load_config(), regime_filter_enabled=False)
    params = V2Params(
        enable_reversal=False,
        enable_continuation=True,
        use_regime_filter=False,
        displacement_range_factor=0.8,
    )
    candidates, _, _ = v2_candidates_for_day(
        frame,
        0.01,
        config,
        params,
        date(2026, 7, 30),
    )
    assert len(candidates) == 1
    assert candidates[0].phase == "london_v2_continuation"
    assert candidates[0].side == "buy"
    assert candidates[0].entry_time == datetime(
        2026,
        7,
        30,
        8,
        10,
        tzinfo=UTC,
    )


def test_v2_partial_and_confirmed_be_are_weighted() -> None:
    times = pd.date_range(
        "2026-07-30T08:00:00Z",
        periods=7,
        freq="min",
    )
    frame = pd.DataFrame(
        {
            "time": times,
            "open": 100.0,
            "high": [100.2, 100.5, 101.2, 101.2, 101.2, 100.2, 100.1],
            "low": [99.9, 99.9, 99.9, 100.2, 100.2, 99.9, 99.9],
            "close": [100.1, 100.4, 101.1, 101.1, 101.1, 100.0, 100.0],
            "spread": 0,
            "tick_volume": 10,
        }
    )
    candidate = V2Candidate(
        phase="london_v2_reversal",
        side="buy",
        signal_time=times[0].to_pydatetime(),
        entry_time=times[0].to_pydatetime(),
        entry_idx=0,
        entry=100.0,
        stop=99.0,
        target=102.0,
        liquidity_level=99.5,
    )
    params = V2Params(
        management_mode="partial_be",
        protect_trigger_r=1.0,
        protect_profit_r=0.0,
        partial_fraction=0.25,
    )
    trade = _simulate_v2_trade(
        frame,
        "XAUUSD",
        date(2026, 7, 30),
        candidate,
        datetime(2026, 7, 30, 8, 7, tzinfo=UTC),
        0.01,
        params,
        110.0,
        100.0,
    )
    assert trade.exit_reason == "partial_protected_stop"
    assert trade.pnl_r == pytest.approx(0.25)
