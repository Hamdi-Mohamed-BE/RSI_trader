from dataclasses import replace

import pandas as pd

from app.relvol_orb_backtest import _normalize_volume
from app.relvol_orb_strategy import (
    RelVolOrbSettings,
    build_opening_setups,
    settings_for_symbol,
    settings_from_env,
    simulate_setup,
)


def _history(days: int = 18) -> pd.DataFrame:
    rows = []
    for index, session_day in enumerate(pd.bdate_range("2026-05-01", periods=days)):
        opening_volume = 200.0 if index == 14 else 100.0
        opening_close = 100.50
        bars = [
            ("09:30", 100.00, 100.60, 99.80, opening_close, opening_volume),
            ("09:35", 100.55, 100.90, 100.50, 100.80, 70.0),
            ("10:00", 100.80, 101.50, 100.70, 101.30, 80.0),
            ("15:55", 101.30, 102.10, 101.20, 102.00, 90.0),
        ]
        for clock, open_, high, low, close, volume in bars:
            timestamp = pd.Timestamp(f"{session_day.date()} {clock}:00")
            rows.append(
                {
                    "time": timestamp,
                    "open": open_,
                    "high": high,
                    "low": low,
                    "close": close,
                    "volume": volume,
                    "tick_volume": volume,
                    "real_volume": 0.0,
                    "volume_source": "tick_volume_proxy",
                    "spread": 2.0,
                }
            )
    return pd.DataFrame(rows)


def _settings() -> RelVolOrbSettings:
    return RelVolOrbSettings(
        symbols=("TEST",),
        range_minutes=5,
        relative_volume_min=1.0,
        session_timezone="UTC",
        data_timezone="UTC",
        min_price=5.0,
        min_daily_atr=0.5,
        min_average_daily_volume=0.0,
    )


def test_relative_volume_uses_only_the_prior_fourteen_sessions() -> None:
    setups = build_opening_setups(_history(), "TEST", _settings(), require_complete_session=True)
    target = next(item for item in setups if str(item["session_date"]) == "2026-05-21")

    assert target["relative_volume"] == 2.0
    assert target["direction"] == "BUY"
    assert target["pending_order_type"] == "BUY_STOP"
    assert target["trigger_price"] == 100.60
    assert target["eligible"] is True


def test_trade_enters_at_range_high_and_exits_at_end_of_day() -> None:
    setups = build_opening_setups(_history(), "TEST", _settings(), require_complete_session=True)
    target = next(item for item in setups if str(item["session_date"]) == "2026-05-21")

    trade = simulate_setup(
        target,
        atr_stop_fraction=0.10,
        point=0.01,
        spread_multiplier=1.0,
        commission_per_unit_per_side=0.0035,
    )

    assert trade is not None
    assert trade["entry"] == 100.60
    assert trade["exit_reason"] == "EOD"
    assert trade["exit_price"] == 102.00
    assert trade["r_multiple"] > 0


def test_relative_volume_and_doji_filters_block_setup() -> None:
    history = _history()
    mask = history["time"] == pd.Timestamp("2026-05-21 09:30:00")
    history.loc[mask, "close"] = history.loc[mask, "open"]

    setups = build_opening_setups(history, "TEST", replace(_settings(), relative_volume_min=2.5))

    assert all(str(item["session_date"]) != "2026-05-21" for item in setups)


def test_volume_normalization_rounds_down_and_respects_minimum() -> None:
    assert _normalize_volume(3.8, minimum=1.0, maximum=100.0, step=1.0) == 3.0
    assert _normalize_volume(0.8, minimum=1.0, maximum=100.0, step=1.0) == 0.0


def test_per_symbol_profiles_override_global_settings(monkeypatch) -> None:
    monkeypatch.setenv(
        "RELVOL_ORB_SYMBOL_PROFILES",
        "US100:60:0.15:0.75;BTCUSD:5:0.15:0.75;ETHUSD:15:0.20:1.0",
    )
    settings = settings_from_env()

    us100 = settings_for_symbol(settings, "US100")
    eth = settings_for_symbol(settings, "ETHUSD")

    assert us100.range_minutes == 60
    assert us100.atr_stop_fraction == 0.15
    assert us100.relative_volume_min == 0.75
    assert eth.range_minutes == 15
    assert eth.atr_stop_fraction == 0.20
    assert eth.relative_volume_min == 1.0


def test_per_symbol_static_lots_are_parsed(monkeypatch) -> None:
    monkeypatch.setenv("RELVOL_ORB_LOT_SIZING_MODE", "STATIC_LOT")
    monkeypatch.setenv("RELVOL_ORB_SYMBOL_LOTS", "US100:0.01;BTCUSD:0.02,ETHUSD:0.10")

    settings = settings_from_env()

    assert settings.lot_sizing_mode == "STATIC_LOT"
    assert settings.symbol_lots == {"US100": 0.01, "BTCUSD": 0.02, "ETHUSD": 0.10}
