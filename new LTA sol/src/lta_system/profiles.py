from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd

from .models import VolumeProfile
from .sessions import with_session_keys


def volume_profile(
    frame: pd.DataFrame,
    name: str,
    rows: int = 128,
    value_area_pct: float = 70.0,
    source: str = "TICK_VOLUME_APPROX",
) -> VolumeProfile:
    if frame.empty:
        raise ValueError("Cannot build a volume profile from an empty frame")
    low = float(frame["low"].min())
    high = float(frame["high"].max())
    if high <= low:
        high = low + max(abs(low) * 1e-6, 1e-6)
    edges = np.linspace(low, high, rows + 1)
    centers = (edges[:-1] + edges[1:]) / 2.0
    histogram = np.zeros(rows, dtype=float)
    volume_col = "real_volume"
    if volume_col not in frame or float(frame[volume_col].sum()) <= 0:
        volume_col = "tick_volume" if "tick_volume" in frame else "volume"
    for row in frame.itertuples(index=False):
        bar_low = float(getattr(row, "low"))
        bar_high = float(getattr(row, "high"))
        volume = max(float(getattr(row, volume_col)), 1.0)
        left = max(0, int(np.searchsorted(edges, bar_low, side="right") - 1))
        right = min(rows - 1, int(np.searchsorted(edges, bar_high, side="left")))
        count = max(right - left + 1, 1)
        histogram[left : right + 1] += volume / count
    poc_index = int(np.argmax(histogram))
    target = histogram.sum() * value_area_pct / 100.0
    selected = {poc_index}
    total = histogram[poc_index]
    lower = poc_index - 1
    upper = poc_index + 1
    while total < target and (lower >= 0 or upper < rows):
        lower_volume = histogram[lower] if lower >= 0 else -1
        upper_volume = histogram[upper] if upper < rows else -1
        if upper_volume >= lower_volume:
            selected.add(upper)
            total += max(upper_volume, 0)
            upper += 1
        else:
            selected.add(lower)
            total += max(lower_volume, 0)
            lower -= 1
    threshold_high = float(np.quantile(histogram, 0.80))
    threshold_low = float(np.quantile(histogram, 0.20))
    hvns = tuple(float(centers[i]) for i in range(rows) if histogram[i] >= threshold_high)
    lvns = tuple(
        float(centers[i])
        for i in range(rows)
        if 0 < histogram[i] <= threshold_low
    )
    return VolumeProfile(
        name=name,
        start=pd.Timestamp(frame["time"].iloc[0]).to_pydatetime(),
        end=pd.Timestamp(frame["time"].iloc[-1]).to_pydatetime(),
        low=low,
        high=high,
        poc=float(centers[poc_index]),
        vah=float(edges[max(selected) + 1]),
        val=float(edges[min(selected)]),
        hvns=hvns,
        lvns=lvns,
        source=source,
    )


def build_completed_profile_maps(
    m1: pd.DataFrame,
    rows: int,
    value_area_pct: float,
) -> tuple[dict[object, VolumeProfile], dict[str, VolumeProfile]]:
    keyed = with_session_keys(m1)
    daily: dict[object, VolumeProfile] = {}
    weekly: dict[str, VolumeProfile] = {}
    for key, group in keyed.groupby("session_day", sort=True):
        daily[key] = volume_profile(
            group,
            f"DAY_{key}",
            rows,
            value_area_pct,
        )
    for key, group in keyed.groupby("session_week", sort=True):
        weekly[str(key)] = volume_profile(
            group,
            f"WEEK_{key}",
            rows,
            value_area_pct,
        )
    return daily, weekly


def previous_key(keys: list[object], current: object) -> object | None:
    prior = [key for key in keys if key < current]
    return prior[-1] if prior else None


def profiles_for_row(
    row: pd.Series,
    daily: dict[object, VolumeProfile],
    weekly: dict[str, VolumeProfile],
) -> tuple[VolumeProfile, ...]:
    day_key = previous_key(sorted(daily), row["session_day"])
    week_key = previous_key(sorted(weekly), str(row["session_week"]))
    profiles: list[VolumeProfile] = []
    if day_key is not None:
        profile = daily[day_key]
        profiles.append(
            VolumeProfile(**{**profile.__dict__, "name": "PD"})
        )
        early_key = previous_key(sorted(daily), day_key)
        if early_key is not None:
            early = daily[early_key]
            profiles.append(
                VolumeProfile(**{**early.__dict__, "name": "EPD"})
            )
    if week_key is not None:
        profile = weekly[str(week_key)]
        profiles.append(
            VolumeProfile(**{**profile.__dict__, "name": "PW"})
        )
        early_key = previous_key(sorted(weekly), str(week_key))
        if early_key is not None:
            early = weekly[str(early_key)]
            profiles.append(
                VolumeProfile(**{**early.__dict__, "name": "EPW"})
            )
    return tuple(profiles)


def profile_levels(profiles: tuple[VolumeProfile, ...]) -> list[tuple[str, float]]:
    levels: list[tuple[str, float]] = []
    for profile in profiles:
        levels.extend(
            [
                (f"{profile.name}_POC", profile.poc),
                (f"{profile.name}_VAH", profile.vah),
                (f"{profile.name}_VAL", profile.val),
                (f"{profile.name}_HIGH", profile.high),
                (f"{profile.name}_LOW", profile.low),
            ]
        )
    return levels

