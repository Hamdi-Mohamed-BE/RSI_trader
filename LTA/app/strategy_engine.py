from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
import os
from typing import Any

import numpy as np
import pandas as pd

from .session_time import DEFAULT_DATA_TIMEZONE, DEFAULT_SESSION_TIMEZONE, zone


@dataclass(frozen=True)
class Profile:
    poc: float
    vah: float
    val: float
    hvns: tuple[float, ...] = ()
    lvns: tuple[float, ...] = ()
    row_size: float = 0.0
    total_volume: float = 0.0
    volume_source: str = "unknown"
    range_start: datetime | None = None
    range_end: datetime | None = None


def _to_frame(candles: pd.DataFrame) -> pd.DataFrame:
    df = candles.copy()
    df["time"] = pd.to_datetime(df["time"])
    for col in ("open", "high", "low", "close"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if "volume" not in df.columns:
        df["volume"] = 1.0
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(1.0).clip(lower=1.0)
    if "volume_source" not in df.columns:
        df["volume_source"] = "unknown_proxy"
    return df.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)


def _atr(df: pd.DataFrame, period: int = 14) -> float:
    if len(df) < 2:
        return float((df["high"].iloc[-1] - df["low"].iloc[-1]) or df["close"].iloc[-1] * 0.001)
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)
    tr = pd.concat([(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    value = float(tr.tail(period).mean())
    if not np.isfinite(value) or value <= 0:
        value = float(close.iloc[-1] * 0.001)
    return value


def _volume_profile(
    df: pd.DataFrame,
    bins: int | None = None,
    value_area: float | None = None,
) -> Profile | None:
    if len(df) < 8:
        return None
    low = float(df["low"].min())
    high = float(df["high"].max())
    if high <= low:
        return None
    bins = int(bins if bins is not None else os.getenv("LTA_PROFILE_BINS", "48") or 48)
    value_area = float(
        value_area if value_area is not None else os.getenv("LTA_PROFILE_VALUE_AREA", "0.70") or 0.70
    )
    bins = min(max(16, bins), 96)
    value_area = min(0.90, max(0.50, value_area))
    edges = np.linspace(low, high, bins + 1)
    bar_lows = np.maximum(low, df["low"].to_numpy(dtype=float))[:, None]
    bar_highs = np.minimum(high, df["high"].to_numpy(dtype=float))[:, None]
    bar_volumes = np.maximum(0.0, df["volume"].to_numpy(dtype=float))
    overlap = np.maximum(
        0.0,
        np.minimum(edges[1:][None, :], bar_highs) - np.maximum(edges[:-1][None, :], bar_lows),
    )
    overlap_totals = overlap.sum(axis=1)
    distributable = overlap_totals > 0
    hist = (
        overlap[distributable]
        * (bar_volumes[distributable] / overlap_totals[distributable])[:, None]
    ).sum(axis=0)
    point_rows = np.flatnonzero(~distributable & (bar_volumes > 0))
    if len(point_rows):
        closes = df["close"].to_numpy(dtype=float)
        indices = np.clip(np.searchsorted(edges, closes[point_rows], side="right") - 1, 0, bins - 1)
        np.add.at(hist, indices, bar_volumes[point_rows])
    if hist.sum() <= 0:
        return None
    centers = (edges[:-1] + edges[1:]) / 2
    poc_idx = int(np.argmax(hist))
    left = right = poc_idx
    total = float(hist[poc_idx])
    target = float(hist.sum() * value_area)
    while total < target and (left > 0 or right < bins - 1):
        lower_volume = float(hist[left - 1]) if left > 0 else -1.0
        upper_volume = float(hist[right + 1]) if right < bins - 1 else -1.0
        if upper_volume >= lower_volume and right < bins - 1:
            right += 1
            total += float(hist[right])
        elif left > 0:
            left -= 1
            total += float(hist[left])

    smooth = np.convolve(hist, np.array([0.25, 0.5, 0.25]), mode="same")
    positive = smooth[smooth > 0]
    high_cutoff = float(np.quantile(positive, 0.65)) if len(positive) else 0.0
    low_cutoff = float(np.quantile(positive, 0.25)) if len(positive) else 0.0
    hvn_indices = [
        index
        for index in range(1, bins - 1)
        if smooth[index] >= smooth[index - 1]
        and smooth[index] >= smooth[index + 1]
        and smooth[index] >= high_cutoff
    ]
    lvn_indices = [
        index
        for index in range(1, bins - 1)
        if smooth[index] <= smooth[index - 1]
        and smooth[index] <= smooth[index + 1]
        and 0 < smooth[index] <= low_cutoff
    ]
    hvn_indices.sort(key=lambda index: float(smooth[index]), reverse=True)
    lvn_indices.sort(key=lambda index: float(smooth[index]))
    volume_source = str(df["volume_source"].mode().iloc[0]) if len(df["volume_source"].mode()) else "unknown_proxy"
    return Profile(
        poc=float(centers[poc_idx]),
        vah=float(edges[right + 1]),
        val=float(edges[left]),
        hvns=tuple(float(centers[index]) for index in hvn_indices[:3]),
        lvns=tuple(float(centers[index]) for index in lvn_indices[:3]),
        row_size=float(edges[1] - edges[0]),
        total_volume=float(hist.sum()),
        volume_source=volume_source,
        range_start=pd.Timestamp(df["time"].iloc[0]).to_pydatetime(),
        range_end=pd.Timestamp(df["time"].iloc[-1]).to_pydatetime(),
    )


def _session_name(timestamp: datetime) -> str:
    data_zone = zone(os.getenv("MARKET_DATA_TIMEZONE", DEFAULT_DATA_TIMEZONE), DEFAULT_DATA_TIMEZONE)
    session_zone = zone(os.getenv("LTA_PROFILE_TIMEZONE", DEFAULT_SESSION_TIMEZONE), DEFAULT_SESSION_TIMEZONE)
    aware = timestamp.replace(tzinfo=data_zone) if timestamp.tzinfo is None else timestamp.astimezone(data_zone)
    local = aware.astimezone(session_zone)
    hour = local.hour + local.minute / 60
    if 8 <= hour < 17:
        return "New York"
    if 3 <= hour < 12:
        return "London"
    if hour >= 19 or hour < 2:
        return "Asia"
    return "Off-session"


def _volume_context(df: pd.DataFrame) -> dict[str, Any]:
    if len(df) < 12:
        return {"ratio": 1.0, "regime": "normal", "source": "unknown_proxy"}
    recent = float(df["volume"].tail(3).mean())
    baseline_frame = df["volume"].iloc[:-3].tail(30)
    baseline = float(baseline_frame.median()) if len(baseline_frame) else recent
    ratio = recent / max(baseline, 1.0)
    if ratio >= float(os.getenv("LTA_HIGH_VOLUME_RATIO", "1.35") or 1.35):
        regime = "high"
    elif ratio <= float(os.getenv("LTA_LOW_VOLUME_RATIO", "0.75") or 0.75):
        regime = "low"
    else:
        regime = "normal"
    source = str(df["volume_source"].mode().iloc[0]) if len(df["volume_source"].mode()) else "unknown_proxy"
    return {"ratio": ratio, "regime": regime, "source": source}


def _candle_parts(row: pd.Series) -> dict[str, float]:
    high = float(row["high"])
    low = float(row["low"])
    open_ = float(row["open"])
    close = float(row["close"])
    rng = max(high - low, 1e-9)
    body_high = max(open_, close)
    body_low = min(open_, close)
    return {
        "range": rng,
        "upper_wick": (high - body_high) / rng,
        "lower_wick": (body_low - low) / rng,
        "body": abs(close - open_) / rng,
    }


def detect_bias(candles: pd.DataFrame, timeframe: str = "M15") -> str:
    df = _to_frame(candles)
    if len(df) < 40:
        return "unclear"
    close = df["close"]
    fast = close.rolling(20).mean().iloc[-1]
    slow = close.rolling(50).mean().iloc[-1] if len(df) >= 50 else close.rolling(30).mean().iloc[-1]
    slope = close.iloc[-1] - close.iloc[-20]
    atr = _atr(df)
    if fast > slow and slope > atr:
        return "bullish"
    if fast < slow and slope < -atr:
        return "bearish"
    return "ranging"


def detect_market_structure(candles: pd.DataFrame) -> dict[str, Any]:
    df = _to_frame(candles)
    if len(df) < 30:
        return {"structure": "unclear", "details": "Not enough candles."}
    recent = df.tail(40)
    first = recent.head(20)
    last = recent.tail(20)
    higher_high = float(last["high"].max()) > float(first["high"].max())
    higher_low = float(last["low"].min()) > float(first["low"].min())
    lower_high = float(last["high"].max()) < float(first["high"].max())
    lower_low = float(last["low"].min()) < float(first["low"].min())
    if higher_high and higher_low:
        return {"structure": "bullish", "details": "Recent range is making higher highs and higher lows."}
    if lower_high and lower_low:
        return {"structure": "bearish", "details": "Recent range is making lower highs and lower lows."}
    return {"structure": "ranging", "details": "Recent range is mixed or consolidating."}


def _profile_clock(df: pd.DataFrame) -> pd.DataFrame:
    framed = df.copy()
    data_zone = zone(os.getenv("MARKET_DATA_TIMEZONE", DEFAULT_DATA_TIMEZONE), DEFAULT_DATA_TIMEZONE)
    session_zone = zone(os.getenv("LTA_PROFILE_TIMEZONE", DEFAULT_SESSION_TIMEZONE), DEFAULT_SESSION_TIMEZONE)
    reset_raw = os.getenv("LTA_PROFILE_DAY_START", "18:00") or "18:00"
    try:
        reset_hour, reset_minute = (int(part) for part in reset_raw.split(":", 1))
    except (TypeError, ValueError):
        reset_hour, reset_minute = 18, 0
    reset_minutes = reset_hour * 60 + reset_minute
    rollover_shift = timedelta(minutes=(24 * 60 - reset_minutes) % (24 * 60))
    timestamps = pd.to_datetime(framed["time"])
    if timestamps.dt.tz is None:
        aware = timestamps.dt.tz_localize(data_zone)
    else:
        aware = timestamps.dt.tz_convert(data_zone)
    local = aware.dt.tz_convert(session_zone)
    shifted = local + pd.Timedelta(rollover_shift)
    trading_days = shifted.dt.date
    framed["_local_time"] = local.dt.tz_localize(None)
    framed["_trading_day"] = trading_days
    framed["_week_start"] = [day - timedelta(days=day.weekday()) for day in trading_days]
    framed["_local_minute"] = local.dt.hour * 60 + local.dt.minute
    return framed


def _profile_metadata(profile: Profile) -> dict[str, Any]:
    return {
        "profile_hvns": list(profile.hvns),
        "profile_lvns": list(profile.lvns),
        "profile_row_size": profile.row_size,
        "profile_total_volume": profile.total_volume,
        "volume_source": profile.volume_source,
        "profile_range_start": profile.range_start,
        "profile_range_end": profile.range_end,
    }


def _add_profile_levels(
    levels: list[dict[str, Any]],
    profile: Profile | None,
    profile_type: str,
    prefix: str,
    priority: int,
) -> None:
    if profile is None:
        return
    metadata = _profile_metadata(profile)
    levels.extend(
        [
            {"profile_type": profile_type, "key_level": f"{prefix} PoC", "kind": "PoC", "price": profile.poc, "priority": priority, **metadata},
            {"profile_type": profile_type, "key_level": f"{prefix} VaH", "kind": "VaH", "price": profile.vah, "priority": priority - 1, **metadata},
            {"profile_type": profile_type, "key_level": f"{prefix} VaL", "kind": "VaL", "price": profile.val, "priority": priority - 1, **metadata},
        ]
    )
    for index, price in enumerate(profile.hvns[:2], start=1):
        levels.append(
            {
                "profile_type": profile_type,
                "key_level": f"{prefix} HVN {index}",
                "kind": "HVN",
                "price": price,
                "priority": priority - 2,
                **metadata,
            }
        )


def _add_price_level(
    levels: list[dict[str, Any]],
    profile_type: str,
    key_level: str,
    kind: str,
    price: float,
    priority: int,
    volume_source: str,
) -> None:
    levels.append(
        {
            "profile_type": profile_type,
            "key_level": key_level,
            "kind": kind,
            "price": float(price),
            "priority": priority,
            "volume_source": volume_source,
        }
    )


def _true_range_series(df: pd.DataFrame) -> pd.Series:
    previous_close = df["close"].shift(1)
    return pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - previous_close).abs(),
            (df["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)


def _fixed_range_segment(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]] | None:
    if len(df) < 50:
        return None
    atr_series = _true_range_series(df).rolling(14).mean()
    lengths = (24, 36, 48, 72, 96)
    best: tuple[float, pd.DataFrame, dict[str, Any]] | None = None
    latest_end = len(df) - 5
    earliest_end = max(24, len(df) - 60)
    for end_index in range(latest_end, earliest_end - 1, -1):
        for length in lengths:
            start_index = end_index - length + 1
            if start_index < 0:
                continue
            segment = df.iloc[start_index : end_index + 1]
            after = df.iloc[end_index + 1 :]
            if len(after) < 3:
                continue
            atr_value = float(atr_series.iloc[end_index])
            if not np.isfinite(atr_value) or atr_value <= 0:
                continue
            range_high = float(segment["high"].max())
            range_low = float(segment["low"].min())
            width_atr = (range_high - range_low) / atr_value
            path = float(segment["close"].diff().abs().sum())
            efficiency = abs(float(segment["close"].iloc[-1]) - float(segment["close"].iloc[0])) / max(path, 1e-9)
            midpoint = (range_high + range_low) / 2
            signs = np.sign(segment["close"].to_numpy(dtype=float) - midpoint)
            rotations = int(np.count_nonzero(signs[1:] != signs[:-1]))
            broke_up = bool((after["close"] > range_high + atr_value * 0.10).any())
            broke_down = bool((after["close"] < range_low - atr_value * 0.10).any())
            if not (1.5 <= width_atr <= 8.0 and efficiency <= 0.42 and rotations >= 3 and (broke_up or broke_down)):
                continue
            breakout_direction = "BUY" if broke_up and not broke_down else "SELL" if broke_down and not broke_up else "MIXED"
            recency = end_index / max(len(df), 1)
            score = recency * 10 + rotations - efficiency * 5 + min(length, 72) / 24
            metadata = {
                "anchor_start": pd.Timestamp(segment["time"].iloc[0]).to_pydatetime(),
                "anchor_end": pd.Timestamp(segment["time"].iloc[-1]).to_pydatetime(),
                "breakout_direction": breakout_direction,
                "range_atr": width_atr,
                "rotations": rotations,
            }
            if best is None or score > best[0]:
                best = (score, segment, metadata)
    return (best[1], best[2]) if best else None


def _swing_segment(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]] | None:
    if len(df) < 30:
        return None
    recent = df.tail(min(180, len(df))).copy()
    offset = len(df) - len(recent)
    atr_value = _atr(recent)
    highs = recent["high"].to_numpy(dtype=float)
    lows = recent["low"].to_numpy(dtype=float)
    pivot_highs = [index for index in range(3, len(recent) - 3) if highs[index] >= highs[index - 3 : index + 4].max()]
    pivot_lows = [index for index in range(3, len(recent) - 3) if lows[index] <= lows[index - 3 : index + 4].min()]
    legs: list[tuple[float, int, int, str]] = []
    for high_index in pivot_highs:
        prior_lows = [index for index in pivot_lows if index < high_index and high_index - index <= 100]
        if prior_lows:
            low_index = min(prior_lows, key=lambda index: lows[index])
            move = highs[high_index] - lows[low_index]
            if move >= atr_value * 2.0:
                legs.append((move + high_index * atr_value * 0.01, low_index, high_index, "BUY"))
    for low_index in pivot_lows:
        prior_highs = [index for index in pivot_highs if index < low_index and low_index - index <= 100]
        if prior_highs:
            high_index = max(prior_highs, key=lambda index: highs[index])
            move = highs[high_index] - lows[low_index]
            if move >= atr_value * 2.0:
                legs.append((move + low_index * atr_value * 0.01, high_index, low_index, "SELL"))
    if not legs:
        return None
    _, first, second, direction = max(legs, key=lambda item: item[0])
    start_index, end_index = sorted((first + offset, second + offset))
    segment = df.iloc[start_index : end_index + 1]
    return segment, {
        "anchor_start": pd.Timestamp(segment["time"].iloc[0]).to_pydatetime(),
        "anchor_end": pd.Timestamp(segment["time"].iloc[-1]).to_pydatetime(),
        "swing_direction": direction,
        "swing_high": float(segment["high"].max()),
        "swing_low": float(segment["low"].min()),
    }


def _candidate_levels(df: pd.DataFrame) -> list[dict[str, Any]]:
    levels: list[dict[str, Any]] = []
    if len(df) < 60:
        return levels
    clocked = _profile_clock(df)
    current_day = clocked["_trading_day"].iloc[-1]
    previous_days = sorted(day for day in clocked["_trading_day"].unique() if day < current_day)
    if previous_days:
        previous_day = clocked[clocked["_trading_day"] == previous_days[-1]]
        profile = _volume_profile(previous_day)
        _add_profile_levels(levels, profile, "Previous Daily", "PD", 20)
        source = profile.volume_source if profile else "unknown_proxy"
        _add_price_level(levels, "Previous Daily", "PD High", "High", float(previous_day["high"].max()), 18, source)
        _add_price_level(levels, "Previous Daily", "PD Low", "Low", float(previous_day["low"].min()), 18, source)
        try:
            main_hour, main_minute = (
                int(part) for part in (os.getenv("LTA_PROFILE_MAIN_SESSION_START", "09:30") or "09:30").split(":", 1)
            )
        except (TypeError, ValueError):
            main_hour, main_minute = 9, 30
        main_start_minutes = main_hour * 60 + main_minute
        try:
            reset_hour, reset_minute = (
                int(part) for part in (os.getenv("LTA_PROFILE_DAY_START", "18:00") or "18:00").split(":", 1)
            )
        except (TypeError, ValueError):
            reset_hour, reset_minute = 18, 0
        reset_minutes = reset_hour * 60 + reset_minute
        overnight = previous_day[
            (previous_day["_local_minute"] >= reset_minutes)
            | (previous_day["_local_minute"] < main_start_minutes)
        ]
        _add_profile_levels(levels, _volume_profile(overnight), "Early Previous Daily", "EPD", 17)

    current_week = clocked["_week_start"].iloc[-1]
    previous_weeks = sorted(week for week in clocked["_week_start"].unique() if week < current_week)
    if previous_weeks:
        previous_week = clocked[clocked["_week_start"] == previous_weeks[-1]]
        _add_profile_levels(levels, _volume_profile(previous_week), "Previous Weekly", "PW", 22)
    if len(previous_weeks) >= 2:
        early_previous_week = clocked[clocked["_week_start"] == previous_weeks[-2]]
        _add_profile_levels(levels, _volume_profile(early_previous_week), "Early Previous Weekly", "EPW", 18)

    latest_local = clocked["_local_time"].iloc[-1]
    current_week_reliable = latest_local.weekday() > 2 or (
        latest_local.weekday() == 2 and latest_local.hour >= 17
    )
    if current_week_reliable:
        current_week_frame = clocked[clocked["_week_start"] == current_week]
        _add_profile_levels(levels, _volume_profile(current_week_frame), "Current Weekly", "CW", 19)

    fixed = _fixed_range_segment(df)
    if fixed:
        fixed_frame, fixed_meta = fixed
        before = len(levels)
        _add_profile_levels(levels, _volume_profile(fixed_frame), "Fixed Range", "Fixed", 19)
        for level in levels[before:]:
            level.update(fixed_meta)

    swing = _swing_segment(df)
    if swing:
        swing_frame, swing_meta = swing
        before = len(levels)
        _add_profile_levels(levels, _volume_profile(swing_frame), "Swing", "Swing", 18)
        for level in levels[before:]:
            level.update(swing_meta)
    return levels


def detect_aoi(candles: pd.DataFrame) -> dict[str, Any] | None:
    df = _to_frame(candles)
    if len(df) < 60:
        return None
    current = df.iloc[-1]
    atr = _atr(df)
    tolerance = max(atr * 0.45, abs(float(current["close"])) * 0.00035)
    levels = _candidate_levels(df)
    touched: list[dict[str, Any]] = []
    for level in levels:
        price = float(level["price"])
        in_candle = float(current["low"]) - tolerance <= price <= float(current["high"]) + tolerance
        near_close = abs(float(current["close"]) - price) <= tolerance
        if in_candle or near_close:
            confluence = 1 + sum(
                1
                for other in levels
                if other is not level and abs(float(other["price"]) - price) <= tolerance
            )
            item = dict(level)
            item["confluence"] = confluence
            item["tolerance"] = tolerance
            touched.append(item)
    if not touched:
        return None
    touched.sort(key=lambda x: (x["confluence"], x["priority"]), reverse=True)
    return touched[0]


def _liquidity_context(df: pd.DataFrame, direction: str) -> tuple[bool, str]:
    if len(df) < 25:
        return False, "Not enough candles to confirm liquidity buildup."
    recent = df.tail(16)
    atr = _atr(df)
    if direction == "BUY":
        lows = recent["low"].tail(8)
        equal_lows = lows.max() - lows.min() <= atr * 0.8
        swept = recent["low"].iloc[-2] <= recent["low"].head(12).min()
        if swept:
            return True, "Sell-side liquidity was swept before the bullish reaction."
        if equal_lows:
            return True, "Sell-side liquidity was built through clustered lows."
    else:
        highs = recent["high"].tail(8)
        equal_highs = highs.max() - highs.min() <= atr * 0.8
        swept = recent["high"].iloc[-2] >= recent["high"].head(12).max()
        if swept:
            return True, "Buy-side liquidity was swept before the bearish reaction."
        if equal_highs:
            return True, "Buy-side liquidity was built through clustered highs."
    return False, "Liquidity buildup or sweep is not clear."


def _level_touch_indices(df: pd.DataFrame, price: float, tolerance: float, lookback: int = 80) -> list[int]:
    start = max(0, len(df) - lookback)
    touched = (
        (df["low"].iloc[start:] - tolerance <= price)
        & (df["high"].iloc[start:] + tolerance >= price)
    ).to_numpy(dtype=bool)
    episodes: list[int] = []
    previous = False
    for offset, value in enumerate(touched):
        if value and not previous:
            episodes.append(start + offset)
        previous = bool(value)
    return episodes


def _internal_swing_profile(
    df: pd.DataFrame,
    level_price: float,
    tolerance: float,
    direction: str,
) -> tuple[Profile, dict[str, Any]] | None:
    if len(df) < 20:
        return None
    search_end = len(df) - 3
    if search_end < 8:
        return None
    search = df.iloc[max(0, search_end - 70) : search_end]
    candidates = _level_touch_indices(search, level_price, tolerance, lookback=len(search))
    if not candidates:
        return None
    atr_value = _atr(df)
    for relative_touch in reversed(candidates):
        touch_index = max(0, search_end - len(search)) + relative_touch
        if search_end - touch_index < 5:
            continue
        development = df.iloc[touch_index:search_end]
        if direction == "BUY":
            extreme_label = development["high"].idxmax()
            extreme_index = int(df.index.get_loc(extreme_label))
            move = float(df.iloc[extreme_index]["high"]) - level_price
        else:
            extreme_label = development["low"].idxmin()
            extreme_index = int(df.index.get_loc(extreme_label))
            move = level_price - float(df.iloc[extreme_index]["low"])
        if extreme_index <= touch_index or move < atr_value * 0.55:
            continue
        segment = df.iloc[touch_index : extreme_index + 1]
        profile = _volume_profile(segment)
        if profile:
            return profile, {
                "touch_index": touch_index,
                "swing_index": extreme_index,
                "anchor_start": pd.Timestamp(segment["time"].iloc[0]).to_pydatetime(),
                "anchor_end": pd.Timestamp(segment["time"].iloc[-1]).to_pydatetime(),
            }
    return None


def detect_entry_confirmation(candles: pd.DataFrame, level: dict[str, Any] | None = None, direction: str | None = None) -> dict[str, Any]:
    df = _to_frame(candles)
    if level is None or direction is None or len(df) < 8:
        return {"confirmed": False, "model": None, "reasons": ["Missing level, direction, or candle history."]}

    current = df.iloc[-1]
    prev = df.iloc[-2]
    prev2 = df.iloc[-3]
    level_price = float(level["price"])
    tolerance = float(level.get("tolerance") or _atr(df) * 0.45)
    reasons: list[str] = []
    models: list[str] = []
    volume = _volume_context(df)
    touch_indices = _level_touch_indices(df, level_price, tolerance)
    touch_count = len(touch_indices)

    prev_parts = _candle_parts(prev)
    current_parts = _candle_parts(current)
    prev_touched = float(prev["low"]) - tolerance <= level_price <= float(prev["high"]) + tolerance
    current_touched = float(current["low"]) - tolerance <= level_price <= float(current["high"]) + tolerance

    if direction == "BUY":
        double_wick = (
            prev_touched
            and current_touched
            and (prev_parts["lower_wick"] >= 0.28 or current_parts["lower_wick"] >= 0.28)
            and float(current["close"]) > float(current["open"])
            and float(current["close"]) > max(float(prev["open"]), float(prev["close"]))
        )
        if double_wick and touch_count <= 2:
            models.append("Entry Model 1 - Double Wick Confirmation")
            reasons.append("Bullish double wick and candle flip confirmed at the key level.")

        prior = df.iloc[-14:-3]
        swept_low = float(prev["low"]) <= float(prior["low"].min()) if len(prior) else False
        broke_internal = float(current["close"]) > max(float(prev["high"]), float(prev2["high"]))
        reclaimed = float(current["close"]) > level_price
        base_width = float(prior["high"].max() - prior["low"].min()) if len(prior) else float("inf")
        if swept_low and broke_internal and reclaimed and base_width <= _atr(df) * 5.0:
            models.append("Entry Model 3 - Confirmation of Internal Structure")
            reasons.append("Consolidation, sell-side manipulation, and expansion through internal highs confirmed.")

    else:
        double_wick = (
            prev_touched
            and current_touched
            and (prev_parts["upper_wick"] >= 0.28 or current_parts["upper_wick"] >= 0.28)
            and float(current["close"]) < float(current["open"])
            and float(current["close"]) < min(float(prev["open"]), float(prev["close"]))
        )
        if double_wick and touch_count <= 2:
            models.append("Entry Model 1 - Double Wick Confirmation")
            reasons.append("Bearish double wick and candle flip confirmed at the key level.")

        prior = df.iloc[-14:-3]
        swept_high = float(prev["high"]) >= float(prior["high"].max()) if len(prior) else False
        broke_internal = float(current["close"]) < min(float(prev["low"]), float(prev2["low"]))
        rejected = float(current["close"]) < level_price
        base_width = float(prior["high"].max() - prior["low"].min()) if len(prior) else float("inf")
        if swept_high and broke_internal and rejected and base_width <= _atr(df) * 5.0:
            models.append("Entry Model 3 - Confirmation of Internal Structure")
            reasons.append("Consolidation, buy-side manipulation, and expansion through internal lows confirmed.")

    internal = _internal_swing_profile(df, level_price, tolerance, direction)
    internal_metadata: dict[str, Any] | None = None
    if internal:
        swing_profile, internal_metadata = internal
        profile_tolerance = max(tolerance * 0.75, swing_profile.row_size * 1.5)
        if direction == "BUY":
            retested = float(current["low"]) - profile_tolerance <= swing_profile.poc <= float(current["high"]) + profile_tolerance
            structure_broke = float(current["close"]) > max(float(prev["high"]), float(prev2["high"]))
            confirmed = float(current["close"]) > float(current["open"])
        else:
            retested = float(current["low"]) - profile_tolerance <= swing_profile.poc <= float(current["high"]) + profile_tolerance
            structure_broke = float(current["close"]) < min(float(prev["low"]), float(prev2["low"]))
            confirmed = float(current["close"]) < float(current["open"])
        if retested and structure_broke and confirmed:
            models.append("Entry Model 2 - Internal Swing Confirmation")
            reasons.append("The first key-level touch formed an internal swing; its PoC retest and structure break confirmed.")
            internal_metadata = {**internal_metadata, **_profile_metadata(swing_profile), "internal_swing_poc": swing_profile.poc}

    prev2_touched = float(prev2["low"]) - tolerance <= level_price <= float(prev2["high"]) + tolerance
    if volume["regime"] == "high" and prev2_touched:
        prev_parts2 = _candle_parts(prev)
        if direction == "BUY":
            em4 = (
                prev_parts2["body"] <= 0.55
                and float(current["close"]) > float(current["open"])
                and float(current["close"]) > float(prev["high"])
            )
        else:
            em4 = (
                prev_parts2["body"] <= 0.55
                and float(current["close"]) < float(current["open"])
                and float(current["close"]) < float(prev["low"])
            )
        if em4:
            models.append("Entry Model 4 - High Volume Continuation")
            reasons.append("A three-candle high-volume continuation flip confirmed the established directional bias.")

    if models:
        model = " + ".join(dict.fromkeys(models))
        return {
            "confirmed": True,
            "model": model,
            "reasons": reasons,
            "touch_count": touch_count,
            "volume": volume,
            "internal_swing": internal_metadata,
        }
    return {
        "confirmed": False,
        "model": None,
        "reasons": ["No official LTA entry model confirmed yet."],
        "touch_count": touch_count,
        "volume": volume,
        "internal_swing": internal_metadata,
    }


def _direction_from_reaction(df: pd.DataFrame, level: dict[str, Any]) -> str | None:
    current = df.iloc[-1]
    price = float(level["price"])
    close = float(current["close"])
    open_ = float(current["open"])
    if float(current["low"]) <= price <= close and close > open_:
        return "BUY"
    if close <= price <= float(current["high"]) and close < open_:
        return "SELL"
    if close > price and _candle_parts(current)["lower_wick"] > 0.35:
        return "BUY"
    if close < price and _candle_parts(current)["upper_wick"] > 0.35:
        return "SELL"
    return None


def _build_trade_levels(df: pd.DataFrame, direction: str, min_rr: float) -> tuple[float, float, float, float]:
    current = df.iloc[-1]
    entry = float(current["close"])
    atr = _atr(df)
    recent = df.tail(8)
    if direction == "BUY":
        stop = float(recent["low"].min()) - atr * 0.15
        risk = max(entry - stop, atr * 0.25)
        stop = entry - risk
        target = entry + risk * max(min_rr, 5.0)
    else:
        stop = float(recent["high"].max()) + atr * 0.15
        risk = max(stop - entry, atr * 0.25)
        stop = entry + risk
        target = entry - risk * max(min_rr, 5.0)
    rr = abs(target - entry) / max(abs(entry - stop), 1e-9)
    return entry, stop, target, rr


def _profit_targets(entry: float, stop: float, direction: str, final_rr: float = 5.0) -> dict[str, float]:
    risk = abs(entry - stop)
    stages = range(1, int(max(1, round(final_rr))) + 1)
    if direction == "BUY":
        return {f"tp{stage}": entry + risk * stage for stage in stages}
    return {f"tp{stage}": entry - risk * stage for stage in stages}


def _recent_aoi(candles: pd.DataFrame, lookback: int = 12) -> dict[str, Any] | None:
    df = _to_frame(candles)
    level = detect_aoi(df)
    if level:
        current = df.iloc[-1]
        item = dict(level)
        item["touched_recent"] = True
        item["distance_from_close"] = abs(float(current["close"]) - float(level["price"]))
        return item

    if len(df) < 60:
        return None
    current = df.iloc[-1]
    close = float(current["close"])
    atr = _atr(df)
    tolerance = max(atr * 0.55, abs(close) * 0.00045)
    max_distance = max(atr * 4.0, abs(close) * 0.0025)
    levels = _candidate_levels(df)
    recent = df.tail(lookback)
    touched: list[dict[str, Any]] = []

    for level in levels:
        price = float(level["price"])
        touched_recent = float(recent["low"].min()) - tolerance <= price <= float(recent["high"].max()) + tolerance
        distance = abs(close - price)
        if not touched_recent or distance > max_distance:
            continue
        confluence = 1 + sum(
            1
            for other in levels
            if other is not level and abs(float(other["price"]) - price) <= tolerance
        )
        item = dict(level)
        item["confluence"] = confluence
        item["tolerance"] = tolerance
        item["touched_recent"] = True
        item["distance_from_close"] = distance
        touched.append(item)

    if not touched:
        return None
    touched.sort(key=lambda item: (item["confluence"], item["priority"], -item["distance_from_close"]), reverse=True)
    return touched[0]


def _preentry_direction(df: pd.DataFrame, level: dict[str, Any]) -> str | None:
    direction = _direction_from_reaction(df, level)
    if direction:
        return direction

    current = df.iloc[-1]
    recent = df.tail(12)
    price = float(level["price"])
    tolerance = float(level.get("tolerance") or _atr(df) * 0.45)
    close = float(current["close"])
    bias = detect_bias(df)
    touched_support = float(recent["low"].min()) <= price + tolerance and close >= price
    touched_resistance = float(recent["high"].max()) >= price - tolerance and close <= price

    if touched_support and not touched_resistance:
        return "BUY"
    if touched_resistance and not touched_support:
        return "SELL"
    if close > price and bias in {"bullish", "ranging"}:
        return "BUY"
    if close < price and bias in {"bearish", "ranging"}:
        return "SELL"
    if close > price:
        return "BUY"
    if close < price:
        return "SELL"
    return None


def _score_preentry_candidate(
    df: pd.DataFrame,
    level: dict[str, Any],
    direction: str,
    trigger_price: float,
    stop_loss: float,
    risk_reward: float,
    min_rr: float,
    mode: str,
    timeframe: str,
) -> tuple[int, list[str], dict[str, Any]]:
    current = df.iloc[-1]
    atr = _atr(df)
    close = float(current["close"])
    bias = detect_bias(df, timeframe)
    structure = detect_market_structure(df)
    liquidity_ok, liquidity_reason = _liquidity_context(df, direction)
    session = _session_name(pd.Timestamp(current["time"]).to_pydatetime())
    volume = _volume_context(df)
    tolerance = float(level.get("tolerance") or atr * 0.45)
    touch_count = len(_level_touch_indices(df, float(level["price"]), tolerance))
    trigger_distance = abs(trigger_price - close)
    stop_clear = trigger_price > stop_loss if direction == "BUY" else trigger_price < stop_loss

    score = 0
    reasons: list[str] = []
    score += min(20, int(level.get("priority", 10)))
    reasons.append(f"Price recently reacted around {level['key_level']} ({level['profile_type']}).")
    if int(level.get("confluence") or 1) >= 2:
        score += 5
        reasons.append("The pending level has volume-profile confluence.")

    if (bias == "bullish" and direction == "BUY") or (bias == "bearish" and direction == "SELL"):
        score += 15
        reasons.append("Pending direction aligns with the higher-timeframe bias.")
    elif bias == "ranging":
        score += 8
        reasons.append("Range conditions allow a level-to-level reaction setup.")
    else:
        reasons.append("Higher-timeframe bias is not fully aligned yet.")

    if (structure.get("structure") == "bullish" and direction == "BUY") or (
        structure.get("structure") == "bearish" and direction == "SELL"
    ):
        score += 10
        reasons.append(structure.get("details") or "Market structure supports the pending direction.")
    elif structure.get("structure") == "ranging":
        score += 5
        reasons.append("Structure is ranging, so confirmation trigger is required.")

    if liquidity_ok:
        score += 15
        reasons.append(liquidity_reason)
    else:
        reasons.append(liquidity_reason)

    if mode == "structure_break":
        score += 12
        reasons.append("Pending stop is placed only at the internal break/reclaim trigger.")
    elif mode == "supply_demand_retest":
        score += 12
        reasons.append("Pending limit retests the fresh base that produced a volume-backed structure break.")
    else:
        score += 8
        reasons.append("Pending limit is placed at the LTF swing profile retest area after the first reaction.")

    if stop_clear:
        score += 10
        reasons.append("Stop loss is beyond the reacted structure, not inside the noise.")
    else:
        reasons.append("Stop loss is not structurally clear enough.")

    if risk_reward >= min_rr:
        score += 10
        reasons.append("The pending setup keeps the required reward-to-risk profile.")
    else:
        reasons.append("The pending setup does not keep the minimum reward-to-risk.")

    if trigger_distance <= atr * 1.5:
        score += 10
        reasons.append("Trigger is close enough to current price to remain tied to the active setup.")
    elif trigger_distance <= atr * 3.0:
        score += 5
        reasons.append("Trigger is valid but slightly stretched from the current candle.")
    else:
        reasons.append("Trigger is far from current price and may become stale.")

    if session in {"London", "New York"}:
        score += 8
        reasons.append(f"Pending setup is forming during active {session} conditions.")
    elif session == "Asia":
        score += 4
        reasons.append("Asia session requires stricter trigger confirmation.")
    else:
        reasons.append("Off-session timing lowers the pending setup quality.")

    if volume["regime"] == "high":
        score += 6
        reasons.append(f"High relative volume supports the pending reaction ({volume['ratio']:.2f}x baseline).")
    elif volume["regime"] == "low":
        reasons.append(f"Low relative volume requires a higher-timeframe or internal-swing confirmation ({volume['ratio']:.2f}x).")
    else:
        score += 2
    if 1 <= touch_count <= 2:
        score += 4
    elif touch_count > 2:
        score -= 8
        reasons.append(f"The key level has already been mitigated {touch_count} times.")

    if not liquidity_ok:
        score = min(score, 83)
    if not stop_clear:
        score = min(score, 74)
    if risk_reward < min_rr:
        score = min(score, 79)
    if trigger_distance > atr * 3.0:
        score = min(score, 80)
    if touch_count > 2:
        score = min(score, 79)
    if volume["regime"] == "low" and timeframe.upper() in {"M1", "M5", "M15"} and mode != "profile_retest":
        score = min(score, 82)
    score = min(89, max(0, score))
    metadata = {
        "bias": bias,
        "structure": structure.get("structure"),
        "trigger_distance": trigger_distance,
        "atr": atr,
        "session": session,
        "volume_source": level.get("volume_source") or volume.get("source"),
        "volume_ratio": round(float(volume["ratio"]), 3),
        "volume_regime": volume["regime"],
        "level_touch_count": touch_count,
        "profile_hvns": level.get("profile_hvns") or [],
        "profile_lvns": level.get("profile_lvns") or [],
    }
    return score, list(dict.fromkeys(reasons)), metadata


def _structure_break_preentry(
    df: pd.DataFrame,
    level: dict[str, Any],
    direction: str,
    timeframe: str,
    min_rr: float,
) -> dict[str, Any] | None:
    if len(df) < 24:
        return None
    current = df.iloc[-1]
    prev = df.iloc[-2]
    prev2 = df.iloc[-3]
    close = float(current["close"])
    atr = _atr(df)
    buffer = max(atr * 0.05, abs(close) * 0.00002)
    recent = df.tail(12)
    tolerance = float(level.get("tolerance") or atr * 0.45)
    level_price = float(level["price"])

    if direction == "BUY":
        trigger = max(float(current["high"]), float(prev["high"]), float(prev2["high"])) + buffer
        stop = min(float(recent["low"].min()), level_price - tolerance) - atr * 0.15
        pending_order_type = "BUY_STOP"
        valid_if = "Price trades through the internal highs, confirming the reclaim/structure break after the level reaction."
        invalidation = "Close below the reacted key level or the manipulation swing low."
    else:
        trigger = min(float(current["low"]), float(prev["low"]), float(prev2["low"])) - buffer
        stop = max(float(recent["high"].max()), level_price + tolerance) + atr * 0.15
        pending_order_type = "SELL_STOP"
        valid_if = "Price trades through the internal lows, confirming the rejection/structure break after the level reaction."
        invalidation = "Close above the reacted key level or the manipulation swing high."

    if not np.isfinite(trigger) or not np.isfinite(stop):
        return None
    risk = abs(trigger - stop)
    if risk <= 0:
        return None
    target = trigger + risk * max(min_rr, 5.0) if direction == "BUY" else trigger - risk * max(min_rr, 5.0)
    rr = abs(target - trigger) / max(risk, 1e-9)
    if abs(trigger - close) > atr * 3.5:
        return None

    score, reasons, metadata = _score_preentry_candidate(
        df=df,
        level=level,
        direction=direction,
        trigger_price=trigger,
        stop_loss=stop,
        risk_reward=rr,
        min_rr=min_rr,
        mode="structure_break",
        timeframe=timeframe,
    )
    targets = _profit_targets(trigger, stop, direction, max(min_rr, 5.0))
    return {
        "direction": direction,
        "setup_score": int(score),
        "setup_grade": "PRE-A+" if score >= 85 else "WATCH",
        "profile_type": level["profile_type"],
        "key_level": level["key_level"],
        "entry_model": "Pending Entry Model 3 - Internal Structure Break",
        "execution_type": "PENDING",
        "pending_order_type": pending_order_type,
        "trigger_price": round(trigger, 5),
        "entry": round(trigger, 5),
        "stop_loss": round(stop, 5),
        "take_profit": round(target, 5),
        "tp1": round(targets["tp1"], 5),
        "tp2": round(targets["tp2"], 5),
        "tp3": round(targets["tp3"], 5),
        "tp4": round(targets["tp4"], 5) if "tp4" in targets else None,
        "tp5": round(targets["tp5"], 5) if "tp5" in targets else None,
        "risk_reward": round(rr, 2),
        "invalidation": invalidation,
        "preplace_valid_if": valid_if,
        "reasons": reasons,
        "status": "preplace",
        **metadata,
    }


def _supply_demand_retest_preentry(
    df: pd.DataFrame,
    level: dict[str, Any],
    direction: str,
    timeframe: str,
    min_rr: float,
) -> dict[str, Any] | None:
    if len(df) < 50:
        return None
    current = df.iloc[-1]
    close = float(current["close"])
    atr = _atr(df)
    if atr <= 0:
        return None
    level_price = float(level["price"])
    tolerance = float(level.get("tolerance") or atr * 0.45)
    search_start = max(10, len(df) - 20)

    selected: dict[str, Any] | None = None
    for expansion_index in range(len(df) - 1, search_start - 1, -1):
        base_index = expansion_index - 1
        initial_index = expansion_index - 2
        if initial_index < 1:
            continue
        initial = df.iloc[initial_index]
        base = df.iloc[base_index]
        expansion = df.iloc[expansion_index]
        prior = df.iloc[max(0, initial_index - 8) : initial_index + 1]
        if prior.empty:
            continue

        base_low = float(base["low"])
        base_high = float(base["high"])
        base_range = base_high - base_low
        body = abs(float(expansion["close"]) - float(expansion["open"]))
        body_atr = body / atr
        volume_history = df["volume"].iloc[max(0, expansion_index - 30) : expansion_index]
        volume_baseline = float(volume_history.median()) if len(volume_history) else float(expansion["volume"])
        volume_ratio = float(expansion["volume"]) / max(volume_baseline, 1.0)
        level_was_mitigated = (
            min(float(initial["low"]), base_low) - tolerance
            <= level_price
            <= max(float(initial["high"]), base_high) + tolerance
        )
        if not level_was_mitigated or base_range <= 0 or base_range > atr * 1.35:
            continue

        if direction == "BUY":
            broke_structure = (
                float(expansion["close"]) > float(prior["high"].max())
                and float(expansion["high"]) > float(initial["high"])
                and float(expansion["close"]) > float(expansion["open"])
            )
            trigger = base_high
            stop = base_low - atr * 0.15
            moved_away = close > trigger + atr * 0.12
            retested = bool((df["low"].iloc[expansion_index + 1 :] <= trigger).any())
            pending_order_type = "BUY_LIMIT"
            invalidation = "Close below the fresh demand base that produced the bullish structure break."
        else:
            broke_structure = (
                float(expansion["close"]) < float(prior["low"].min())
                and float(expansion["low"]) < float(initial["low"])
                and float(expansion["close"]) < float(expansion["open"])
            )
            trigger = base_low
            stop = base_high + atr * 0.15
            moved_away = close < trigger - atr * 0.12
            retested = bool((df["high"].iloc[expansion_index + 1 :] >= trigger).any())
            pending_order_type = "SELL_LIMIT"
            invalidation = "Close above the fresh supply base that produced the bearish structure break."

        strong_imbalance = body_atr >= 0.75 and (volume_ratio >= 1.15 or body_atr >= 1.20)
        if not broke_structure or not strong_imbalance or not moved_away or retested:
            continue
        if abs(trigger - close) > atr * 3.5:
            continue
        selected = {
            "expansion_index": expansion_index,
            "base_index": base_index,
            "initial_index": initial_index,
            "trigger": trigger,
            "stop": stop,
            "pending_order_type": pending_order_type,
            "invalidation": invalidation,
            "body_atr": body_atr,
            "volume_ratio": volume_ratio,
            "base_low": base_low,
            "base_high": base_high,
        }
        break

    if selected is None:
        return None
    trigger = float(selected["trigger"])
    stop = float(selected["stop"])
    risk = abs(trigger - stop)
    if risk <= 0:
        return None
    final_rr = max(min_rr, 5.0)
    target = trigger + risk * final_rr if direction == "BUY" else trigger - risk * final_rr
    score, reasons, metadata = _score_preentry_candidate(
        df=df,
        level=level,
        direction=direction,
        trigger_price=trigger,
        stop_loss=stop,
        risk_reward=final_rr,
        min_rr=min_rr,
        mode="supply_demand_retest",
        timeframe=timeframe,
    )
    targets = _profit_targets(trigger, stop, direction, final_rr)
    expansion_index = int(selected["expansion_index"])
    base_index = int(selected["base_index"])
    return {
        "direction": direction,
        "setup_score": int(score),
        "setup_grade": "PRE-A+" if score >= 85 else "WATCH",
        "profile_type": level["profile_type"],
        "key_level": level["key_level"],
        "entry_model": "Pending Supply/Demand Base Retest",
        "execution_type": "PENDING",
        "pending_order_type": selected["pending_order_type"],
        "trigger_price": round(trigger, 5),
        "entry": round(trigger, 5),
        "stop_loss": round(stop, 5),
        "take_profit": round(target, 5),
        "tp1": round(targets["tp1"], 5),
        "tp2": round(targets["tp2"], 5),
        "tp3": round(targets["tp3"], 5),
        "tp4": round(targets["tp4"], 5) if "tp4" in targets else None,
        "tp5": round(targets["tp5"], 5) if "tp5" in targets else None,
        "risk_reward": round(final_rr, 2),
        "invalidation": selected["invalidation"],
        "preplace_valid_if": "Price pulls back into the untested base that launched the structure-breaking expansion.",
        "book_aligned_retest": True,
        "supply_demand_zone": {
            "kind": "demand" if direction == "BUY" else "supply",
            "low": round(float(selected["base_low"]), 5),
            "high": round(float(selected["base_high"]), 5),
            "base_time": pd.Timestamp(df.iloc[base_index]["time"]).to_pydatetime(),
            "expansion_time": pd.Timestamp(df.iloc[expansion_index]["time"]).to_pydatetime(),
            "expansion_body_atr": round(float(selected["body_atr"]), 3),
            "expansion_volume_ratio": round(float(selected["volume_ratio"]), 3),
            "fresh": True,
        },
        "reasons": list(dict.fromkeys([
            *reasons,
            "The base is untested after expansion, matching the book's balance-to-imbalance retest model.",
        ])),
        "status": "preplace",
        **metadata,
    }


def _profile_retest_preentry(
    df: pd.DataFrame,
    level: dict[str, Any],
    direction: str,
    timeframe: str,
    min_rr: float,
) -> dict[str, Any] | None:
    if len(df) < 40:
        return None
    current = df.iloc[-1]
    close = float(current["close"])
    atr = _atr(df)
    level_price = float(level["price"])
    tolerance = float(level.get("tolerance") or atr * 0.45)
    internal = _internal_swing_profile(df, level_price, tolerance, direction)
    if internal is None:
        return None
    profile, internal_meta = internal
    reaction = df.iloc[int(internal_meta["touch_index"]) : int(internal_meta["swing_index"]) + 1]
    moved_from_level = (close - level_price) if direction == "BUY" else (level_price - close)
    if moved_from_level < atr * 0.45 or moved_from_level > atr * 3.5:
        return None

    raw_levels = [profile.poc, profile.vah, profile.val]
    if direction == "BUY":
        possible = [price for price in raw_levels if price < close]
        if not possible:
            return None
        trigger = min(possible, key=lambda price: abs(price - profile.poc))
        stop = min(float(reaction["low"].min()), level_price) - atr * 0.15
        pending_order_type = "BUY_LIMIT"
        valid_if = "Price retraces into the LTF swing profile after the first key-level reaction, giving the planned pullback entry."
        invalidation = "Close below the LTF swing low and reacted key level."
    else:
        possible = [price for price in raw_levels if price > close]
        if not possible:
            return None
        trigger = min(possible, key=lambda price: abs(price - profile.poc))
        stop = max(float(reaction["high"].max()), level_price) + atr * 0.15
        pending_order_type = "SELL_LIMIT"
        valid_if = "Price retraces into the LTF swing profile after the first key-level rejection, giving the planned pullback entry."
        invalidation = "Close above the LTF swing high and reacted key level."

    if abs(trigger - close) < atr * 0.12 or abs(trigger - close) > atr * 3.5:
        return None
    risk = abs(trigger - stop)
    if risk <= 0:
        return None
    target = trigger + risk * max(min_rr, 5.0) if direction == "BUY" else trigger - risk * max(min_rr, 5.0)
    rr = abs(target - trigger) / max(risk, 1e-9)
    score, reasons, metadata = _score_preentry_candidate(
        df=df,
        level=level,
        direction=direction,
        trigger_price=trigger,
        stop_loss=stop,
        risk_reward=rr,
        min_rr=min_rr,
        mode="profile_retest",
        timeframe=timeframe,
    )
    targets = _profit_targets(trigger, stop, direction, max(min_rr, 5.0))
    return {
        "direction": direction,
        "setup_score": int(score),
        "setup_grade": "PRE-A+" if score >= 85 else "WATCH",
        "profile_type": level["profile_type"],
        "key_level": level["key_level"],
        "entry_model": "Pending Entry Model 2 - LTF Swing Retest",
        "execution_type": "PENDING",
        "pending_order_type": pending_order_type,
        "trigger_price": round(trigger, 5),
        "entry": round(trigger, 5),
        "stop_loss": round(stop, 5),
        "take_profit": round(target, 5),
        "tp1": round(targets["tp1"], 5),
        "tp2": round(targets["tp2"], 5),
        "tp3": round(targets["tp3"], 5),
        "tp4": round(targets["tp4"], 5) if "tp4" in targets else None,
        "tp5": round(targets["tp5"], 5) if "tp5" in targets else None,
        "risk_reward": round(rr, 2),
        "invalidation": invalidation,
        "preplace_valid_if": valid_if,
        "book_aligned_retest": True,
        "reasons": reasons,
        "status": "preplace",
        "internal_swing": {**internal_meta, **_profile_metadata(profile), "internal_swing_poc": profile.poc},
        **metadata,
    }


def score_setup(context: dict[str, Any]) -> tuple[int, list[str]]:
    reasons: list[str] = []
    score = 0

    level = context["level"]
    if level:
        score += min(20, int(level.get("priority", 10)))
        if level.get("confluence", 1) >= 2:
            score += 5
            reasons.append("Key level has volume-profile confluence.")
        reasons.append(f"Price is reacting from {level['key_level']} ({level['profile_type']}).")
    else:
        reasons.append("No mapped LTA key level.")

    bias = context["bias"]
    direction = context["direction"]
    confirmation = context["confirmation"]
    if (bias == "bullish" and direction == "BUY") or (bias == "bearish" and direction == "SELL"):
        score += 15
        reasons.append("Direction aligns with higher-timeframe bias.")
    elif bias == "ranging" and confirmation.get("confirmed"):
        score += 9
        reasons.append("Range conditions allow a confirmed reaction trade.")
    elif confirmation.get("model") and "Internal Structure" in confirmation["model"]:
        score += 10
        reasons.append("Counter-bias idea is supported by manipulation and internal structure break.")
    else:
        reasons.append("Higher-timeframe bias is not fully aligned.")

    if context["liquidity_ok"]:
        score += 15
        reasons.append(context["liquidity_reason"])
    else:
        reasons.append(context["liquidity_reason"])

    if confirmation.get("confirmed"):
        score += 20
        reasons.extend(confirmation.get("reasons", []))
    else:
        reasons.extend(confirmation.get("reasons", []))

    if context["stop_clear"]:
        score += 10
        reasons.append("Stop loss and invalidation are structure based.")
    else:
        reasons.append("Stop loss or invalidation is unclear.")

    if context["risk_reward"] >= context["min_rr"]:
        score += 10
        reasons.append("Risk-to-reward meets the minimum.")
    else:
        reasons.append("Risk-to-reward is too low.")

    if context["session"] in {"London", "New York"}:
        score += 10
        reasons.append(f"Setup appears during active {context['session']} session conditions.")
    elif context["session"] == "Asia":
        score += 5
        reasons.append("Asia session is acceptable only with extra confirmation.")
    else:
        reasons.append("Off-session timing lowers quality.")

    volume = context.get("volume") or {}
    volume_regime = str(volume.get("regime") or "normal")
    volume_ratio = float(volume.get("ratio") or 1.0)
    if volume_regime == "high":
        score += 8
        reasons.append(f"High relative volume confirms participation ({volume_ratio:.2f}x baseline).")
    elif volume_regime == "normal":
        score += 3
        reasons.append(f"Relative volume is normal ({volume_ratio:.2f}x baseline).")
    else:
        reasons.append(f"Low relative volume requires slower confirmation ({volume_ratio:.2f}x baseline).")

    touch_count = int(confirmation.get("touch_count") or 0)
    if 1 <= touch_count <= 2:
        score += 5
        reasons.append(f"This is key-level mitigation number {touch_count}; first and second touches receive priority.")
    elif touch_count > 2:
        score -= 8
        reasons.append(f"The level has already been mitigated {touch_count} times and is considered degraded.")

    if not level:
        score = min(score, 60)
    if not confirmation.get("confirmed"):
        score = min(score, 70)
    if not context["stop_clear"]:
        score = min(score, 75)
    if context["risk_reward"] < context["min_rr"]:
        score = min(score, 79)
    model = str(confirmation.get("model") or "")
    if volume_regime == "low" and context.get("timeframe") in {"M1", "M5", "M15"} and not any(
        name in model for name in ("Entry Model 2", "Entry Model 3")
    ):
        score = min(score, 84)
    if touch_count > 2:
        score = min(score, 84)

    grade = min(100, max(0, score))
    return grade, reasons


def generate_signal(
    candles: pd.DataFrame,
    symbol: str,
    timeframe: str,
    min_score: int = 90,
    min_rr: float = 5.0,
) -> dict[str, Any] | None:
    df = _to_frame(candles)
    if len(df) < 80:
        return None
    level = detect_aoi(df)
    if not level:
        return None

    direction = _direction_from_reaction(df, level)
    if direction is None:
        direction = "BUY" if float(df.iloc[-1]["close"]) >= float(level["price"]) else "SELL"

    entry, stop, target, rr = _build_trade_levels(df, direction, min_rr)
    targets = _profit_targets(entry, stop, direction, max(min_rr, 5.0))
    confirmation = detect_entry_confirmation(df, level, direction)
    volume = confirmation.get("volume") or _volume_context(df)
    liquidity_ok, liquidity_reason = _liquidity_context(df, direction)
    bias = detect_bias(df, timeframe)
    structure = detect_market_structure(df)
    session = _session_name(pd.Timestamp(df.iloc[-1]["time"]).to_pydatetime())
    stop_clear = abs(entry - stop) > 0 and np.isfinite(stop) and np.isfinite(target)

    context = {
        "level": level,
        "direction": direction,
        "bias": bias,
        "structure": structure,
        "confirmation": confirmation,
        "liquidity_ok": liquidity_ok,
        "liquidity_reason": liquidity_reason,
        "stop_clear": stop_clear,
        "risk_reward": rr,
        "min_rr": min_rr,
        "session": session,
        "timeframe": timeframe.upper(),
        "volume": volume,
    }
    score, reasons = score_setup(context)
    grade = "A+" if score >= 90 else "A" if score >= 80 else "B" if score >= 70 else "C"
    status = "allowed" if score >= min_score else "rejected"

    invalidation = (
        "Close below the rejection wick/internal swing low."
        if direction == "BUY"
        else "Close above the rejection wick/internal swing high."
    )
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "direction": direction,
        "setup_grade": grade,
        "setup_score": int(score),
        "profile_type": level["profile_type"],
        "profile_kind": level.get("kind"),
        "key_level": level["key_level"],
        "entry_model": confirmation.get("model"),
        "confirmation_price": round(entry, 5),
        "atr": round(float(_atr(df)), 5),
        "entry": round(entry, 5),
        "stop_loss": round(stop, 5),
        "take_profit": round(target, 5),
        "tp1": round(targets["tp1"], 5),
        "tp2": round(targets["tp2"], 5),
        "tp3": round(targets["tp3"], 5),
        "tp4": round(targets["tp4"], 5) if "tp4" in targets else None,
        "tp5": round(targets["tp5"], 5) if "tp5" in targets else None,
        "risk_reward": round(rr, 2),
        "invalidation": invalidation,
        "bias": bias,
        "structure": structure.get("structure"),
        "session": session,
        "volume_source": level.get("volume_source") or volume.get("source"),
        "volume_ratio": round(float(volume.get("ratio") or 1.0), 3),
        "volume_regime": volume.get("regime"),
        "profile_hvns": level.get("profile_hvns") or [],
        "profile_lvns": level.get("profile_lvns") or [],
        "profile_range_start": level.get("profile_range_start"),
        "profile_range_end": level.get("profile_range_end"),
        "level_touch_count": confirmation.get("touch_count"),
        "internal_swing": confirmation.get("internal_swing"),
        "reasons": list(dict.fromkeys(reasons)),
        "status": status,
        "timestamp": pd.Timestamp(df.iloc[-1]["time"]).to_pydatetime(),
    }


def generate_preentry_candidate(
    candles: pd.DataFrame,
    symbol: str,
    timeframe: str,
    min_score: int = 85,
    min_rr: float = 5.0,
    allow_after_confirmation: bool = False,
    limit_only: bool = False,
) -> dict[str, Any] | None:
    df = _to_frame(candles)
    if len(df) < 80:
        return None

    level = _recent_aoi(df)
    if not level:
        return None

    direction = _preentry_direction(df, level)
    if direction is None:
        return None

    confirmation = detect_entry_confirmation(df, level, direction)
    if confirmation.get("confirmed") and not allow_after_confirmation:
        return None

    candidates = [
        _profile_retest_preentry(df, level, direction, timeframe, min_rr),
        _supply_demand_retest_preentry(df, level, direction, timeframe, min_rr),
        _structure_break_preentry(df, level, direction, timeframe, min_rr),
    ]
    valid = [
        candidate
        for candidate in candidates
        if candidate
        and int(candidate.get("setup_score") or 0) >= min_score
        and float(candidate.get("risk_reward") or 0.0) >= min_rr
        and (
            not limit_only
            or str(candidate.get("pending_order_type") or "").upper() in {"BUY_LIMIT", "SELL_LIMIT"}
        )
    ]
    if not valid:
        return None

    valid.sort(
        key=lambda item: (
            3
            if "Entry Model 2" in str(item.get("entry_model") or "")
            else 2
            if bool(item.get("book_aligned_retest"))
            else 1
            if str(item.get("pending_order_type") or "").endswith("_LIMIT")
            else 0,
            int(item.get("setup_score") or 0),
        ),
        reverse=True,
    )
    candidate = dict(valid[0])
    candidate["symbol"] = symbol
    candidate["timeframe"] = timeframe
    candidate["timestamp"] = pd.Timestamp(df.iloc[-1]["time"]).to_pydatetime()
    if confirmation.get("confirmed"):
        candidate["confirmed_market_alternative"] = True
        reasons = list(candidate.get("reasons") or [])
        reasons.append("A market confirmation exists; this pending limit is the non-chasing pullback alternative.")
        candidate["reasons"] = list(dict.fromkeys(reasons))
    return candidate
