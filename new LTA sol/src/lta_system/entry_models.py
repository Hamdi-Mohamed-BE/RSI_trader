from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .models import VolumeProfile, Zone
from .profiles import profile_levels, volume_profile
from .structure import candle_parts


@dataclass(frozen=True)
class EntryCandidate:
    direction: str
    model: str
    entry: float
    stop: float
    level: float
    level_name: str
    zone_id: str | None
    reasons: tuple[str, ...]


def _all_levels(
    profiles: tuple[VolumeProfile, ...],
    zones: tuple[Zone, ...],
) -> list[tuple[str, float, str | None, str | None]]:
    levels = [(name, price, None, None) for name, price in profile_levels(profiles)]
    for zone in zones:
        if zone.kind == "demand":
            levels.append((f"{zone.pattern}_DEMAND", zone.high, zone.zone_id, "buy"))
            levels.append((f"{zone.pattern}_DISTAL", zone.low, zone.zone_id, "buy"))
        else:
            levels.append((f"{zone.pattern}_SUPPLY", zone.low, zone.zone_id, "sell"))
            levels.append((f"{zone.pattern}_DISTAL", zone.high, zone.zone_id, "sell"))
    return levels


def _touched(row: pd.Series, level: float, tolerance: float) -> bool:
    return float(row["low"]) - tolerance <= level <= float(row["high"]) + tolerance


def em1(
    frame: pd.DataFrame,
    index: int,
    profiles: tuple[VolumeProfile, ...],
    zones: tuple[Zone, ...],
) -> list[EntryCandidate]:
    if index < 2:
        return []
    first = frame.iloc[index - 1]
    second = frame.iloc[index]
    atr = float(second["atr"])
    tolerance = 0.12 * atr
    body1, upper1, lower1 = candle_parts(first)
    body2, upper2, lower2 = candle_parts(second)
    minimum_body = max(0.05 * atr, 1e-9)
    candidates: list[EntryCandidate] = []
    for name, level, zone_id, forced in _all_levels(profiles, zones):
        if not (_touched(first, level, tolerance) and _touched(second, level, tolerance)):
            continue
        if forced in (None, "buy"):
            buy = (
                float(first["close"]) >= level - tolerance
                and lower1 >= 1.25 * max(body1, minimum_body)
                and float(second["close"]) > float(second["open"])
                and float(second["close"]) > level
                and lower2 >= 0.35 * max(body2, minimum_body)
            )
            if buy:
                candidates.append(
                    EntryCandidate(
                        direction="buy",
                        model="EM1",
                        entry=float(second["close"]),
                        stop=min(float(first["low"]), float(second["low"])) - 0.08 * atr,
                        level=level,
                        level_name=name,
                        zone_id=zone_id,
                        reasons=("double-wick bullish rejection",),
                    )
                )
        if forced in (None, "sell"):
            sell = (
                float(first["close"]) <= level + tolerance
                and upper1 >= 1.25 * max(body1, minimum_body)
                and float(second["close"]) < float(second["open"])
                and float(second["close"]) < level
                and upper2 >= 0.35 * max(body2, minimum_body)
            )
            if sell:
                candidates.append(
                    EntryCandidate(
                        direction="sell",
                        model="EM1",
                        entry=float(second["close"]),
                        stop=max(float(first["high"]), float(second["high"])) + 0.08 * atr,
                        level=level,
                        level_name=name,
                        zone_id=zone_id,
                        reasons=("double-wick bearish rejection",),
                    )
                )
    return candidates


def em2(
    frame: pd.DataFrame,
    index: int,
    profiles: tuple[VolumeProfile, ...],
    zones: tuple[Zone, ...],
) -> list[EntryCandidate]:
    if index < 15:
        return []
    window = frame.iloc[index - 12 : index + 1].copy()
    internal = volume_profile(
        window.rename(columns={"volume": "tick_volume"}),
        "INTERNAL_SWING",
        rows=32,
        value_area_pct=70,
    )
    current = frame.iloc[index]
    previous = frame.iloc[index - 1]
    atr = float(current["atr"])
    main_mitigation = any(
        min(float(row["low"]) for _, row in window.tail(8).iterrows()) <= level <=
        max(float(row["high"]) for _, row in window.tail(8).iterrows())
        for _, level in profile_levels(profiles)
    ) or bool(zones)
    if not main_mitigation:
        return []
    level = internal.poc
    tolerance = 0.10 * atr
    if not (_touched(previous, level, tolerance) or _touched(current, level, tolerance)):
        return []
    candidates: list[EntryCandidate] = []
    if (
        float(current["close"]) > level
        and float(current["close"]) > float(current["open"])
        and float(current["close"]) > float(previous["high"])
    ):
        candidates.append(
            EntryCandidate(
                "buy",
                "EM2",
                float(current["close"]),
                min(float(previous["low"]), float(current["low"])) - 0.08 * atr,
                level,
                "INTERNAL_SWING_POC",
                zones[-1].zone_id if zones else None,
                ("HTF mitigation", "internal swing POC reclaim"),
            )
        )
    if (
        float(current["close"]) < level
        and float(current["close"]) < float(current["open"])
        and float(current["close"]) < float(previous["low"])
    ):
        candidates.append(
            EntryCandidate(
                "sell",
                "EM2",
                float(current["close"]),
                max(float(previous["high"]), float(current["high"])) + 0.08 * atr,
                level,
                "INTERNAL_SWING_POC",
                zones[-1].zone_id if zones else None,
                ("HTF mitigation", "internal swing POC rejection"),
            )
        )
    return candidates


def em3(
    frame: pd.DataFrame,
    index: int,
    profiles: tuple[VolumeProfile, ...],
    zones: tuple[Zone, ...],
) -> list[EntryCandidate]:
    if index < 8:
        return []
    consolidation = frame.iloc[index - 6 : index - 1]
    manipulation = frame.iloc[index - 1]
    displacement = frame.iloc[index]
    atr = float(displacement["atr"])
    if float(consolidation["high"].max() - consolidation["low"].min()) > 1.8 * atr:
        return []
    levels = _all_levels(profiles, zones)
    candidates: list[EntryCandidate] = []
    body = abs(float(displacement["close"] - displacement["open"]))
    if body < 0.75 * atr:
        return []
    for name, level, zone_id, forced in levels:
        bullish_sweep = (
            forced in (None, "buy")
            and float(manipulation["low"]) < level
            and float(manipulation["close"]) > level
            and float(displacement["close"]) > float(consolidation["high"].max())
        )
        bearish_sweep = (
            forced in (None, "sell")
            and float(manipulation["high"]) > level
            and float(manipulation["close"]) < level
            and float(displacement["close"]) < float(consolidation["low"].min())
        )
        if bullish_sweep:
            candidates.append(
                EntryCandidate(
                    "buy",
                    "EM3",
                    float(displacement["close"]),
                    float(manipulation["low"]) - 0.08 * atr,
                    level,
                    name,
                    zone_id,
                    ("liquidity manipulation", "bullish displacement", "structure break"),
                )
            )
        if bearish_sweep:
            candidates.append(
                EntryCandidate(
                    "sell",
                    "EM3",
                    float(displacement["close"]),
                    float(manipulation["high"]) + 0.08 * atr,
                    level,
                    name,
                    zone_id,
                    ("liquidity manipulation", "bearish displacement", "structure break"),
                )
            )
    return candidates


def em4(
    frame: pd.DataFrame,
    index: int,
    profiles: tuple[VolumeProfile, ...],
    zones: tuple[Zone, ...],
) -> list[EntryCandidate]:
    if index < 3:
        return []
    one, two, three = frame.iloc[index - 2], frame.iloc[index - 1], frame.iloc[index]
    atr = float(three["atr"])
    tolerance = 0.10 * atr
    trend = str(three["trend"])
    candidates: list[EntryCandidate] = []
    for name, level, zone_id, forced in _all_levels(profiles, zones):
        if not _touched(one, level, tolerance):
            continue
        if (
            trend == "bullish"
            and forced in (None, "buy")
            and float(two["close"]) > float(two["open"])
            and float(three["close"]) > float(one["high"])
            and float(three["close"]) > float(three["open"])
        ):
            candidates.append(
                EntryCandidate(
                    "buy",
                    "EM4",
                    float(three["close"]),
                    min(float(one["low"]), float(two["low"])) - 0.08 * atr,
                    level,
                    name,
                    zone_id,
                    ("bullish trend", "three-candle continuation flip"),
                )
            )
        if (
            trend == "bearish"
            and forced in (None, "sell")
            and float(two["close"]) < float(two["open"])
            and float(three["close"]) < float(one["low"])
            and float(three["close"]) < float(three["open"])
        ):
            candidates.append(
                EntryCandidate(
                    "sell",
                    "EM4",
                    float(three["close"]),
                    max(float(one["high"]), float(two["high"])) + 0.08 * atr,
                    level,
                    name,
                    zone_id,
                    ("bearish trend", "three-candle continuation flip"),
                )
            )
    return candidates


MODEL_FUNCTIONS = {"EM1": em1, "EM2": em2, "EM3": em3, "EM4": em4}

