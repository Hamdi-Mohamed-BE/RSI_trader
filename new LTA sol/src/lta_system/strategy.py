from __future__ import annotations

import pandas as pd

from .config import AppConfig
from .entry_models import EntryCandidate, MODEL_FUNCTIONS
from .grading import grade_at_least, grade_for_score
from .models import Signal, VolumeProfile, Zone
from .profiles import profile_levels


def _structural_target(
    frame: pd.DataFrame,
    index: int,
    candidate: EntryCandidate,
    profiles: tuple[VolumeProfile, ...],
    zones: tuple[Zone, ...],
    min_rr: float,
) -> tuple[float, float] | None:
    entry = candidate.entry
    risk = abs(entry - candidate.stop)
    atr = float(frame.iloc[index]["atr"])
    if risk <= max(0.05 * atr, 1e-9) or risk > 3.0 * atr:
        return None
    levels = [price for _, price in profile_levels(profiles)]
    for zone in zones:
        levels.extend([zone.low, zone.high])
    historical = frame.iloc[max(0, index - 80) : index]
    levels.extend(
        [
            float(historical["high"].max()),
            float(historical["low"].min()),
            float(historical["high"].rolling(12).max().iloc[-1]),
            float(historical["low"].rolling(12).min().iloc[-1]),
        ]
    )
    if candidate.direction == "buy":
        valid = sorted(
            value
            for value in levels
            if value >= entry + min_rr * risk
        )
        if not valid:
            return None
        target = valid[0]
        return target, (target - entry) / risk
    valid = sorted(
        (
            value
            for value in levels
            if value <= entry - min_rr * risk
        ),
        reverse=True,
    )
    if not valid:
        return None
    target = valid[0]
    return target, (entry - target) / risk


def _score_candidate(
    frame: pd.DataFrame,
    index: int,
    candidate: EntryCandidate,
    zones: tuple[Zone, ...],
    rr: float,
) -> tuple[int, str, tuple[str, ...]]:
    row = frame.iloc[index]
    reasons = list(candidate.reasons)
    score = 3  # A fully confirmed, named entry model.
    profile_confluence = (
        "POC" in candidate.level_name
        or "VAH" in candidate.level_name
        or "VAL" in candidate.level_name
    )
    if profile_confluence:
        score += 2
        reasons.append("completed/swing profile confluence")
    zone = next((item for item in zones if item.zone_id == candidate.zone_id), None)
    if zone is not None:
        score += 2
        reasons.append(f"{zone.pattern} {zone.kind} zone")
        if zone.fresh:
            score += 1
            reasons.append("fresh zone")
    aligned = (
        candidate.direction == "buy" and row["trend"] == "bullish"
    ) or (
        candidate.direction == "sell" and row["trend"] == "bearish"
    )
    if aligned:
        score += 2
        reasons.append("intraday trend aligned")
    break_aligned = str(row["structure_break"]) == (
        "bullish" if candidate.direction == "buy" else "bearish"
    )
    if break_aligned or candidate.model == "EM3":
        score += 1
        reasons.append("internal structure confirmed")
    if rr >= 2.0:
        score += 2
        reasons.append(f"structural target offers {rr:.2f}R")
    if 2 <= int(row.get("ny_hour", 0)) <= 16:
        score += 1
        reasons.append("active London/New York liquidity window")
    archetype = (
        "hybrid"
        if zone is not None and profile_confluence
        else "momentum"
        if aligned
        else "contrarian"
    )
    return score, archetype, tuple(reasons)


def evaluate_signals(
    frame: pd.DataFrame,
    index: int,
    symbol: str,
    profiles: tuple[VolumeProfile, ...],
    zones: tuple[Zone, ...],
    config: AppConfig,
    apply_min_grade: bool = True,
) -> tuple[Signal, ...]:
    row = frame.iloc[index]
    if pd.isna(row.get("atr")):
        return ()
    candidates: list[EntryCandidate] = []
    for model in config.entry_models:
        candidates.extend(MODEL_FUNCTIONS[model](frame, index, profiles, zones))
    signals: list[Signal] = []
    for candidate in candidates:
        target_result = _structural_target(
            frame,
            index,
            candidate,
            profiles,
            zones,
            config.min_rr,
        )
        if target_result is None:
            continue
        target, rr = target_result
        score, archetype, reasons = _score_candidate(
            frame, index, candidate, zones, rr
        )
        grade = grade_for_score(score)
        # Macro/COT/seasonality feeds are not yet connected. A+ is reserved
        # until full context can be evaluated point-in-time.
        context_quality = "TECHNICAL_CONTEXT_ONLY"
        if grade == "A+":
            grade = "A"
            reasons = reasons + ("A+ capped: point-in-time macro context unavailable",)
        if apply_min_grade and not grade_at_least(grade, config.min_grade):
            continue
        invalidation = (
            f"H1 close below {candidate.stop:.3f}"
            if candidate.direction == "buy"
            else f"H1 close above {candidate.stop:.3f}"
        )
        signals.append(
            Signal(
                time=pd.Timestamp(row["time"]).to_pydatetime(),
                symbol=symbol,
                direction=candidate.direction,
                model=candidate.model,
                archetype=archetype,
                grade=grade,
                score=score,
                entry=candidate.entry,
                stop=candidate.stop,
                target=target,
                rr=rr,
                level=candidate.level,
                level_name=candidate.level_name,
                zone_id=candidate.zone_id,
                context_quality=context_quality,
                reasons=reasons,
                invalidation=invalidation,
            )
        )
    # Highest-quality signal wins; avoid duplicate orders from one candle.
    signals.sort(key=lambda value: (value.score, value.rr), reverse=True)
    return tuple(signals[:1])


def watch_snapshot(
    frame: pd.DataFrame,
    index: int,
    profiles: tuple[VolumeProfile, ...],
    zones: tuple[Zone, ...],
) -> dict[str, object]:
    row = frame.iloc[index]
    price = float(row["close"])
    levels = profile_levels(profiles)
    nearest_level = min(levels, key=lambda item: abs(item[1] - price)) if levels else None
    nearest_zone = (
        min(zones, key=lambda zone: min(abs(zone.low - price), abs(zone.high - price)))
        if zones
        else None
    )
    return {
        "time": pd.Timestamp(row["time"]).isoformat(),
        "price": price,
        "trend": str(row["trend"]),
        "structure_break": str(row["structure_break"]),
        "nearest_profile_level": nearest_level,
        "nearest_zone": (
            {
                "id": nearest_zone.zone_id,
                "kind": nearest_zone.kind,
                "pattern": nearest_zone.pattern,
                "low": nearest_zone.low,
                "high": nearest_zone.high,
                "touches": nearest_zone.touches,
            }
            if nearest_zone
            else None
        ),
    }

