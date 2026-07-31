from __future__ import annotations

import pandas as pd

from .models import Zone


def detect_active_zones(
    frame: pd.DataFrame,
    end_index: int,
    lookback: int = 500,
    max_touches: int = 2,
) -> tuple[Zone, ...]:
    if end_index < 25:
        return ()
    start = max(20, end_index - lookback)
    candidates: list[Zone] = []
    for base_start in range(start, end_index - 3):
        base_end = base_start + 2
        impulse_index = base_end + 1
        if impulse_index >= end_index:
            break
        base = frame.iloc[base_start : base_end + 1]
        impulse = frame.iloc[impulse_index]
        atr = float(frame.iloc[base_end].get("atr", 0) or 0)
        if atr <= 0:
            continue
        average_range = float((base["high"] - base["low"]).mean())
        if average_range > 0.85 * atr:
            continue
        base_high = float(base["high"].max())
        base_low = float(base["low"].min())
        impulse_range = float(impulse["high"] - impulse["low"])
        body = abs(float(impulse["close"] - impulse["open"]))
        if impulse_range < 1.20 * atr or body < 0.55 * impulse_range:
            continue
        before = frame.iloc[max(start, base_start - 3) : base_start]
        prior_move = (
            float(before["close"].iloc[-1] - before["open"].iloc[0])
            if not before.empty
            else 0.0
        )
        if float(impulse["close"]) > base_high:
            kind = "demand"
            pattern = "DBR" if prior_move < 0 else "RBR"
            distal = base_low
            proximal = float(base[["open", "close"]].max(axis=1).max())
        elif float(impulse["close"]) < base_low:
            kind = "supply"
            pattern = "RBD" if prior_move > 0 else "DBD"
            distal = base_high
            proximal = float(base[["open", "close"]].min(axis=1).min())
        else:
            continue
        zone_low = min(distal, proximal)
        zone_high = max(distal, proximal)
        later = frame.iloc[impulse_index + 1 : end_index + 1]
        intersections = later[
            (later["low"] <= zone_high) & (later["high"] >= zone_low)
        ]
        touches = 0
        last_touch_position = -2
        for position in intersections.index:
            if position > last_touch_position + 1:
                touches += 1
            last_touch_position = int(position)
        invalidated = False
        if not later.empty:
            if kind == "demand":
                invalidated = bool((later["close"] < distal).any())
            else:
                invalidated = bool((later["close"] > distal).any())
        if invalidated or touches > max_touches:
            continue
        created = pd.Timestamp(frame.iloc[impulse_index]["time"]).to_pydatetime()
        candidates.append(
            Zone(
                zone_id=f"{kind[:1].upper()}{created:%Y%m%d%H}_{base_start}",
                kind=kind,
                pattern=pattern,
                created_at=created,
                proximal=proximal,
                distal=distal,
                impulse_atr=impulse_range / atr,
                touches=touches,
                fresh=touches == 0,
            )
        )
    # Keep the most recent representative from strongly overlapping zones.
    selected: list[Zone] = []
    for zone in reversed(candidates):
        duplicate = any(
            existing.kind == zone.kind
            and min(existing.high, zone.high) >= max(existing.low, zone.low)
            for existing in selected
        )
        if not duplicate:
            selected.append(zone)
        if len(selected) >= 12:
            break
    return tuple(reversed(selected))


def zones_near_price(
    zones: tuple[Zone, ...],
    low: float,
    high: float,
    tolerance: float,
) -> tuple[Zone, ...]:
    return tuple(
        zone
        for zone in zones
        if low - tolerance <= zone.high and high + tolerance >= zone.low
    )


def build_zone_timeline(
    frame: pd.DataFrame,
    lookback: int = 500,
    max_touches: int = 2,
) -> tuple[tuple[Zone, ...], ...]:
    """Build point-in-time active zones once for the full chronological run.

    The slower ``detect_active_zones`` function is useful for isolated chart
    checks. A backtest needs the same information for every candle, so this
    function updates zone state as each candle arrives without reading any
    future candle.
    """
    states: list[dict[str, object]] = []
    timeline: list[tuple[Zone, ...]] = []
    for index in range(len(frame)):
        row = frame.iloc[index]
        updated: list[dict[str, object]] = []
        for state in states:
            if index - int(state["created_index"]) > lookback:
                continue
            kind = str(state["kind"])
            distal = float(state["distal"])
            invalidated = (
                kind == "demand" and float(row["close"]) < distal
            ) or (
                kind == "supply" and float(row["close"]) > distal
            )
            if invalidated:
                continue
            zone_low = min(distal, float(state["proximal"]))
            zone_high = max(distal, float(state["proximal"]))
            intersects = (
                float(row["low"]) <= zone_high
                and float(row["high"]) >= zone_low
            )
            if intersects and index > int(state["created_index"]):
                if index > int(state["last_touch"]) + 1:
                    state["touches"] = int(state["touches"]) + 1
                state["last_touch"] = index
            if int(state["touches"]) <= max_touches:
                updated.append(state)
        states = updated

        # A three-candle base immediately followed by displacement.
        if index >= 23:
            base_start = index - 3
            base = frame.iloc[base_start:index]
            impulse = row
            atr = float(frame.iloc[index - 1].get("atr", 0) or 0)
            if atr > 0:
                average_range = float((base["high"] - base["low"]).mean())
                base_high = float(base["high"].max())
                base_low = float(base["low"].min())
                impulse_range = float(impulse["high"] - impulse["low"])
                body = abs(float(impulse["close"] - impulse["open"]))
                before = frame.iloc[max(0, base_start - 3) : base_start]
                prior_move = (
                    float(before["close"].iloc[-1] - before["open"].iloc[0])
                    if not before.empty
                    else 0.0
                )
                state: dict[str, object] | None = None
                if (
                    average_range <= 0.85 * atr
                    and impulse_range >= 1.20 * atr
                    and body >= 0.55 * impulse_range
                ):
                    if float(impulse["close"]) > base_high:
                        state = {
                            "kind": "demand",
                            "pattern": "DBR" if prior_move < 0 else "RBR",
                            "distal": base_low,
                            "proximal": float(
                                base[["open", "close"]].max(axis=1).max()
                            ),
                        }
                    elif float(impulse["close"]) < base_low:
                        state = {
                            "kind": "supply",
                            "pattern": "RBD" if prior_move > 0 else "DBD",
                            "distal": base_high,
                            "proximal": float(
                                base[["open", "close"]].min(axis=1).min()
                            ),
                        }
                if state is not None:
                    created = pd.Timestamp(row["time"]).to_pydatetime()
                    state.update(
                        {
                            "zone_id": (
                                f"{str(state['kind'])[:1].upper()}"
                                f"{created:%Y%m%d%H}_{base_start}"
                            ),
                            "created_at": created,
                            "created_index": index,
                            "impulse_atr": impulse_range / atr,
                            "touches": 0,
                            "last_touch": -2,
                        }
                    )
                    states.append(state)

        zones = [
            Zone(
                zone_id=str(state["zone_id"]),
                kind=str(state["kind"]),
                pattern=str(state["pattern"]),
                created_at=state["created_at"],  # type: ignore[arg-type]
                proximal=float(state["proximal"]),
                distal=float(state["distal"]),
                impulse_atr=float(state["impulse_atr"]),
                touches=int(state["touches"]),
                fresh=int(state["touches"]) == 0,
            )
            for state in states
        ]
        selected: list[Zone] = []
        for zone in reversed(zones):
            duplicate = any(
                existing.kind == zone.kind
                and min(existing.high, zone.high)
                >= max(existing.low, zone.low)
                for existing in selected
            )
            if not duplicate:
                selected.append(zone)
            if len(selected) >= 12:
                break
        timeline.append(tuple(reversed(selected)))
    return tuple(timeline)
