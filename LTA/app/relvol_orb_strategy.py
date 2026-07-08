from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, datetime, time
import os
from typing import Any

import numpy as np
import pandas as pd

from .session_time import DEFAULT_DATA_TIMEZONE, DEFAULT_SESSION_TIMEZONE, zone


@dataclass(frozen=True)
class RelVolOrbSettings:
    symbols: tuple[str, ...]
    range_minutes: int = 5
    relative_volume_min: float = 1.0
    relative_volume_lookback: int = 14
    atr_lookback: int = 14
    atr_stop_fraction: float = 0.10
    session_start: str = "09:30"
    session_end: str = "16:00"
    session_timezone: str = DEFAULT_SESSION_TIMEZONE
    data_timezone: str = DEFAULT_DATA_TIMEZONE
    min_price: float = 5.0
    min_daily_atr: float = 0.50
    min_average_daily_volume: float = 0.0
    top_n: int = 20
    commission_per_unit_per_side: float = 0.0035
    spread_multiplier: float = 1.0
    risk_percent: float = 1.0
    max_leverage: float = 4.0
    use_minimum_lot: bool = True
    symbol_profiles: dict[str, dict[str, float]] = field(default_factory=dict)
    lot_sizing_mode: str = "RISK_PERCENT"
    symbol_lots: dict[str, float] = field(default_factory=dict)


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)) or default)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)) or default)
    except ValueError:
        return default


def _env_symbols(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    value = os.getenv(name)
    if not value:
        return default
    return tuple(item.strip().upper() for item in value.split(",") if item.strip())


def _env_symbol_profiles(name: str) -> dict[str, dict[str, float]]:
    profiles: dict[str, dict[str, float]] = {}
    for raw_profile in (os.getenv(name) or "").split(";"):
        parts = [item.strip() for item in raw_profile.split(":")]
        if len(parts) != 4 or not parts[0]:
            continue
        try:
            range_minutes = max(5, int(parts[1]))
            atr_stop_fraction = max(0.001, float(parts[2]))
            relative_volume_min = max(0.0, float(parts[3]))
        except ValueError:
            continue
        profiles[parts[0].upper()] = {
            "range_minutes": float(range_minutes),
            "atr_stop_fraction": atr_stop_fraction,
            "relative_volume_min": relative_volume_min,
        }
    return profiles


def _env_symbol_lots(name: str) -> dict[str, float]:
    lots: dict[str, float] = {}
    for raw_item in (os.getenv(name) or "").replace(",", ";").split(";"):
        parts = [item.strip() for item in raw_item.split(":", 1)]
        if len(parts) != 2 or not parts[0]:
            continue
        try:
            lot = float(parts[1])
        except ValueError:
            continue
        if lot > 0:
            lots[parts[0].upper()] = lot
    return lots


def settings_from_env() -> RelVolOrbSettings:
    defaults = ("NVDA", "AMD", "TSLA", "AAPL", "MSFT", "META", "AMZN")
    lot_mode = (os.getenv("RELVOL_ORB_LOT_SIZING_MODE") or "RISK_PERCENT").strip().upper()
    if lot_mode not in {"RISK_PERCENT", "STATIC_LOT"}:
        lot_mode = "RISK_PERCENT"
    return RelVolOrbSettings(
        symbols=_env_symbols("RELVOL_ORB_SYMBOLS", defaults),
        range_minutes=max(5, _env_int("RELVOL_ORB_RANGE_MINUTES", 5)),
        relative_volume_min=max(0.0, _env_float("RELVOL_ORB_MIN_RELATIVE_VOLUME", 1.0)),
        relative_volume_lookback=max(2, _env_int("RELVOL_ORB_RELATIVE_VOLUME_LOOKBACK", 14)),
        atr_lookback=max(2, _env_int("RELVOL_ORB_ATR_LOOKBACK", 14)),
        atr_stop_fraction=max(0.001, _env_float("RELVOL_ORB_ATR_STOP_FRACTION", 0.10)),
        session_start=os.getenv("RELVOL_ORB_SESSION_START", "09:30"),
        session_end=os.getenv("RELVOL_ORB_SESSION_END", "16:00"),
        session_timezone=os.getenv("RELVOL_ORB_SESSION_TIMEZONE", DEFAULT_SESSION_TIMEZONE),
        data_timezone=os.getenv(
            "RELVOL_ORB_DATA_TIMEZONE",
            os.getenv("MARKET_DATA_TIMEZONE", DEFAULT_DATA_TIMEZONE),
        ),
        min_price=max(0.0, _env_float("RELVOL_ORB_MIN_PRICE", 5.0)),
        min_daily_atr=max(0.0, _env_float("RELVOL_ORB_MIN_DAILY_ATR", 0.50)),
        min_average_daily_volume=max(0.0, _env_float("RELVOL_ORB_MIN_AVG_DAILY_VOLUME", 0.0)),
        top_n=max(1, _env_int("RELVOL_ORB_TOP_N", 20)),
        commission_per_unit_per_side=max(0.0, _env_float("RELVOL_ORB_COMMISSION_PER_UNIT", 0.0035)),
        spread_multiplier=max(0.0, _env_float("RELVOL_ORB_SPREAD_MULTIPLIER", 1.0)),
        risk_percent=max(0.0, _env_float("RELVOL_ORB_RISK_PERCENT", 1.0)),
        max_leverage=max(0.0, _env_float("RELVOL_ORB_MAX_LEVERAGE", 4.0)),
        use_minimum_lot=_env_bool("RELVOL_ORB_USE_MINIMUM_LOT", True),
        symbol_profiles=_env_symbol_profiles("RELVOL_ORB_SYMBOL_PROFILES"),
        lot_sizing_mode=lot_mode,
        symbol_lots=_env_symbol_lots("RELVOL_ORB_SYMBOL_LOTS"),
    )


def settings_for_symbol(settings: RelVolOrbSettings, symbol: str) -> RelVolOrbSettings:
    profile = settings.symbol_profiles.get(symbol.upper())
    if not profile:
        return settings
    return replace(
        settings,
        range_minutes=int(profile["range_minutes"]),
        atr_stop_fraction=float(profile["atr_stop_fraction"]),
        relative_volume_min=float(profile["relative_volume_min"]),
    )


def _clock_minutes(value: str, default: str) -> int:
    raw = value or default
    try:
        hour, minute = (int(part) for part in raw.split(":", 1))
    except (TypeError, ValueError):
        hour, minute = (int(part) for part in default.split(":", 1))
    return hour * 60 + minute


def _localize_candles(candles: pd.DataFrame, settings: RelVolOrbSettings) -> pd.DataFrame:
    if candles is None or candles.empty:
        return pd.DataFrame()
    frame = candles.copy()
    timestamps = pd.to_datetime(frame["time"], errors="coerce")
    if timestamps.dt.tz is None:
        timestamps = timestamps.dt.tz_localize(zone(settings.data_timezone))
    timestamps = timestamps.dt.tz_convert(zone(settings.session_timezone))
    frame["local_time"] = timestamps
    frame["session_date"] = timestamps.dt.date
    frame["local_minute"] = timestamps.dt.hour * 60 + timestamps.dt.minute
    frame["volume"] = pd.to_numeric(frame.get("volume", 0.0), errors="coerce").fillna(0.0)
    frame["spread"] = pd.to_numeric(frame.get("spread", 0.0), errors="coerce").fillna(0.0)
    for column in ("open", "high", "low", "close"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame.dropna(subset=["local_time", "open", "high", "low", "close"])


def build_opening_setups(
    candles: pd.DataFrame,
    symbol: str,
    settings: RelVolOrbSettings,
    require_complete_session: bool = False,
) -> list[dict[str, Any]]:
    frame = _localize_candles(candles, settings)
    if frame.empty:
        return []
    start_minute = _clock_minutes(settings.session_start, "09:30")
    end_minute = _clock_minutes(settings.session_end, "16:00")
    range_end = start_minute + settings.range_minutes
    regular = frame[
        (frame["local_minute"] >= start_minute)
        & (frame["local_minute"] < end_minute)
        & (frame["local_time"].dt.weekday < 5)
    ].copy()
    if regular.empty:
        return []

    expected_range_bars = max(1, settings.range_minutes // 5)
    session_rows: list[dict[str, Any]] = []
    session_frames: dict[date, pd.DataFrame] = {}
    for session_day, day_frame in regular.groupby("session_date", sort=True):
        day_frame = day_frame.sort_values("local_time").drop_duplicates("local_minute", keep="last")
        if require_complete_session and int(day_frame.iloc[-1]["local_minute"]) < end_minute - 5:
            continue
        opening = day_frame[
            (day_frame["local_minute"] >= start_minute)
            & (day_frame["local_minute"] < range_end)
        ]
        if len(opening) < expected_range_bars or int(opening.iloc[0]["local_minute"]) != start_minute:
            continue
        opening = opening.head(expected_range_bars)
        future = day_frame[day_frame["local_minute"] >= range_end]
        if future.empty:
            continue
        session_frames[session_day] = future.reset_index(drop=True)
        session_rows.append(
            {
                "session_date": session_day,
                "session_open": float(day_frame.iloc[0]["open"]),
                "session_high": float(day_frame["high"].max()),
                "session_low": float(day_frame["low"].min()),
                "session_close": float(day_frame.iloc[-1]["close"]),
                "session_volume": float(day_frame["volume"].sum()),
                "opening_open": float(opening.iloc[0]["open"]),
                "opening_high": float(opening["high"].max()),
                "opening_low": float(opening["low"].min()),
                "opening_close": float(opening.iloc[-1]["close"]),
                "opening_volume": float(opening["volume"].sum()),
                "opening_time": opening.iloc[0]["local_time"],
                "volume_source": str(opening.iloc[-1].get("volume_source") or "unknown"),
            }
        )
    if not session_rows:
        return []

    sessions = pd.DataFrame(session_rows).sort_values("session_date").reset_index(drop=True)
    previous_close = sessions["session_close"].shift(1)
    true_range = pd.concat(
        [
            sessions["session_high"] - sessions["session_low"],
            (sessions["session_high"] - previous_close).abs(),
            (sessions["session_low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    sessions["daily_atr"] = true_range.shift(1).rolling(settings.atr_lookback).mean()
    sessions["average_daily_volume"] = (
        sessions["session_volume"].shift(1).rolling(settings.relative_volume_lookback).mean()
    )
    sessions["average_opening_volume"] = (
        sessions["opening_volume"].shift(1).rolling(settings.relative_volume_lookback).mean()
    )

    setups: list[dict[str, Any]] = []
    for row in sessions.to_dict(orient="records"):
        baseline = float(row.get("average_opening_volume") or np.nan)
        atr = float(row.get("daily_atr") or np.nan)
        average_daily_volume = float(row.get("average_daily_volume") or np.nan)
        if not np.isfinite(baseline) or baseline <= 0 or not np.isfinite(atr) or atr <= 0:
            continue
        relative_volume = float(row["opening_volume"]) / baseline
        opening_open = float(row["opening_open"])
        opening_close = float(row["opening_close"])
        if opening_close > opening_open:
            direction = "BUY"
            pending_order_type = "BUY_STOP"
            trigger_price = float(row["opening_high"])
        elif opening_close < opening_open:
            direction = "SELL"
            pending_order_type = "SELL_STOP"
            trigger_price = float(row["opening_low"])
        else:
            continue

        eligible = (
            opening_open >= settings.min_price
            and atr >= settings.min_daily_atr
            and relative_volume >= settings.relative_volume_min
            and (
                settings.min_average_daily_volume <= 0
                or (
                    np.isfinite(average_daily_volume)
                    and average_daily_volume >= settings.min_average_daily_volume
                )
            )
        )
        session_day = row["session_date"]
        setups.append(
            {
                **row,
                "symbol": symbol.upper(),
                "direction": direction,
                "pending_order_type": pending_order_type,
                "trigger_price": trigger_price,
                "relative_volume": relative_volume,
                "eligible": bool(eligible),
                "future_bars": session_frames[session_day],
                "range_minutes": settings.range_minutes,
                "atr_stop_fraction": settings.atr_stop_fraction,
            }
        )
    return setups


def simulate_setup(
    setup: dict[str, Any],
    atr_stop_fraction: float,
    point: float,
    spread_multiplier: float = 1.0,
    commission_per_unit_per_side: float = 0.0035,
) -> dict[str, Any] | None:
    bars = setup.get("future_bars")
    if bars is None or bars.empty:
        return None
    direction = str(setup["direction"])
    trigger = float(setup["trigger_price"])
    stop_distance = float(setup["daily_atr"]) * float(atr_stop_fraction)
    if stop_distance <= 0:
        return None

    entry = None
    entry_time = None
    trigger_index = None
    for index, bar in bars.iterrows():
        spread = max(0.0, float(bar.get("spread") or 0.0)) * point * spread_multiplier
        if direction == "BUY" and float(bar["high"]) + spread >= trigger:
            entry = max(trigger, float(bar["open"]) + spread)
            entry_time = bar["local_time"]
            trigger_index = index
            break
        if direction == "SELL" and float(bar["low"]) <= trigger:
            entry = min(trigger, float(bar["open"]))
            entry_time = bar["local_time"]
            trigger_index = index
            break
    if entry is None or trigger_index is None:
        return None

    stop_loss = entry - stop_distance if direction == "BUY" else entry + stop_distance
    exit_price = None
    exit_time = None
    exit_reason = "EOD"
    for _, bar in bars.loc[trigger_index:].iterrows():
        spread = max(0.0, float(bar.get("spread") or 0.0)) * point * spread_multiplier
        if direction == "BUY" and float(bar["low"]) <= stop_loss:
            exit_price = min(stop_loss, float(bar["open"]))
            exit_time = bar["local_time"]
            exit_reason = "SL"
            break
        if direction == "SELL" and float(bar["high"]) + spread >= stop_loss:
            exit_price = max(stop_loss, float(bar["open"]) + spread)
            exit_time = bar["local_time"]
            exit_reason = "SL"
            break
    if exit_price is None:
        final_bar = bars.iloc[-1]
        final_spread = max(0.0, float(final_bar.get("spread") or 0.0)) * point * spread_multiplier
        exit_price = float(final_bar["close"]) if direction == "BUY" else float(final_bar["close"]) + final_spread
        exit_time = final_bar["local_time"]

    gross_per_unit = exit_price - entry if direction == "BUY" else entry - exit_price
    commission_per_unit = 2.0 * commission_per_unit_per_side
    net_per_unit = gross_per_unit - commission_per_unit
    return {
        "session_date": setup["session_date"],
        "symbol": setup["symbol"],
        "direction": direction,
        "range_minutes": int(setup["range_minutes"]),
        "relative_volume": float(setup["relative_volume"]),
        "volume_source": setup.get("volume_source"),
        "entry_time": entry_time,
        "exit_time": exit_time,
        "entry": float(entry),
        "stop_loss": float(stop_loss),
        "exit_price": float(exit_price),
        "exit_reason": exit_reason,
        "stop_distance": stop_distance,
        "gross_per_unit": gross_per_unit,
        "net_per_unit": net_per_unit,
        "r_multiple": net_per_unit / stop_distance,
        "daily_atr": float(setup["daily_atr"]),
        "opening_open": float(setup["opening_open"]),
        "opening_high": float(setup["opening_high"]),
        "opening_low": float(setup["opening_low"]),
        "opening_close": float(setup["opening_close"]),
        "opening_volume": float(setup["opening_volume"]),
    }


def latest_eligible_setups(
    candles_by_symbol: dict[str, pd.DataFrame],
    settings: RelVolOrbSettings,
    session_day: date | None = None,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for symbol, candles in candles_by_symbol.items():
        symbol_settings = settings_for_symbol(settings, symbol)
        setups = build_opening_setups(candles, symbol, symbol_settings)
        if not setups:
            continue
        selected_day = session_day or max(item["session_date"] for item in setups)
        candidates.extend(
            item for item in setups if item["session_date"] == selected_day and item["eligible"]
        )
    candidates.sort(key=lambda item: float(item["relative_volume"]), reverse=True)
    return candidates[: settings.top_n]
