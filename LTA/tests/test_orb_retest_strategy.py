from datetime import date, datetime

import pandas as pd
import pytest

from app.orb_strategy import (
    ORBSettings,
    confirmed_orb_signal,
    pending_orb_signals,
    session_bounds,
)


def _retest_settings(**overrides) -> ORBSettings:
    values = {
        "session_start": "08:00",
        "session_end": "16:00",
        "range_minutes": 15,
        "reward_risk": 1.5,
        "max_signal_age_minutes": 30,
        "session_timezone": "America/New_York",
        "data_timezone": "UTC",
        "entry_model": "BREAKOUT_RETEST",
        "range_start_utc_offset_minutes": -300,
        "zone_lookback_bars": 6,
    }
    values.update(overrides)
    return ORBSettings(**values)


def _buy_breakout_candles() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"time": "2026-06-15 12:55:00", "open": 100.0, "high": 100.5, "low": 99.5, "close": 100.2},
            {"time": "2026-06-15 13:00:00", "open": 100.2, "high": 100.8, "low": 99.8, "close": 100.5},
            {"time": "2026-06-15 13:05:00", "open": 100.5, "high": 100.9, "low": 100.1, "close": 100.7},
            {"time": "2026-06-15 13:10:00", "open": 100.7, "high": 101.0, "low": 99.8, "close": 100.3},
            {"time": "2026-06-15 13:15:00", "open": 100.8, "high": 101.8, "low": 100.7, "close": 101.5},
        ]
    )


def test_fixed_est_range_anchor_maps_to_new_york_dst() -> None:
    settings = _retest_settings()

    winter_start, winter_range_end, winter_end = session_bounds(date(2026, 1, 15), settings)
    summer_start, summer_range_end, summer_end = session_bounds(date(2026, 6, 15), settings)

    assert winter_start == datetime(2026, 1, 15, 13, 0)
    assert winter_range_end == datetime(2026, 1, 15, 13, 15)
    assert winter_end == datetime(2026, 1, 15, 21, 0)
    assert summer_start == datetime(2026, 6, 15, 13, 0)
    assert summer_range_end == datetime(2026, 6, 15, 13, 15)
    assert summer_end == datetime(2026, 6, 15, 20, 0)


def test_retest_signal_waits_for_closed_m5_breakout() -> None:
    candles = _buy_breakout_candles()
    settings = _retest_settings()

    incomplete = confirmed_orb_signal(
        candles,
        "XAUUSD",
        "M5",
        settings,
        now=datetime(2026, 6, 15, 13, 19, 59),
    )
    confirmed = confirmed_orb_signal(
        candles,
        "XAUUSD",
        "M5",
        settings,
        now=datetime(2026, 6, 15, 13, 20),
    )

    assert incomplete is None
    assert confirmed is not None
    assert confirmed["direction"] == "BUY"
    assert confirmed["execution_type"] == "PENDING"
    assert confirmed["pending_order_type"] == "BUY_LIMIT"
    assert confirmed["entry"] == 101.0
    assert confirmed["stop_loss"] == 99.8
    assert confirmed["take_profit"] == pytest.approx(102.8)
    assert confirmed["expires_at"] == datetime(2026, 6, 15, 20, 0)
    assert confirmed["orb"]["retest_zone"]["time"] == "2026-06-15 13:10:00"


def test_retest_mode_never_stages_pre_breakout_stop_orders() -> None:
    candles = _buy_breakout_candles().iloc[:-1].copy()
    settings = _retest_settings()

    signals = pending_orb_signals(
        candles,
        "XAUUSD",
        "M5",
        settings,
        now=datetime(2026, 6, 15, 13, 20),
    )

    assert signals == []


def test_classic_orb_entry_remains_available() -> None:
    candles = _buy_breakout_candles()
    settings = _retest_settings(
        entry_model="BREAKOUT",
        range_start_utc_offset_minutes=None,
        session_start="09:00",
    )

    signal = confirmed_orb_signal(
        candles,
        "XAUUSD",
        "M5",
        settings,
        now=datetime(2026, 6, 15, 13, 16),
    )

    assert signal is not None
    assert signal["execution_type"] == "MARKET"
    assert signal["entry_model"] == "Opening Range Breakout"
