from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from typing import Iterable

import numpy as np


LOW_QUANTILE = 0.25
HIGH_QUANTILE = 0.90
VALIDATION_START = date(2024, 1, 1)
MIN_HISTORY = 10


@dataclass(frozen=True)
class RangeConfig:
    mode: str
    window: int | None
    half_life: float | None
    low_quantile: float = LOW_QUANTILE
    high_quantile: float = HIGH_QUANTILE
    scope: str = "event"


def weighted_quantile(
    values: Iterable[float],
    quantile: float,
    weights: Iterable[float] | None = None,
) -> float:
    data = np.asarray(list(values), dtype=float)
    if len(data) == 0:
        raise ValueError("At least one value is required.")
    if not 0 <= quantile <= 1:
        raise ValueError("Quantile must be between zero and one.")
    if weights is None:
        return float(np.quantile(data, quantile))
    weight_data = np.asarray(list(weights), dtype=float)
    if len(weight_data) != len(data) or np.any(weight_data < 0):
        raise ValueError("Weights must be non-negative and match the values.")
    order = np.argsort(data)
    ordered = data[order]
    ordered_weights = weight_data[order]
    total = float(np.sum(ordered_weights))
    if total <= 0:
        raise ValueError("Weights must have a positive sum.")
    centers = (np.cumsum(ordered_weights) - 0.5 * ordered_weights) / total
    return float(np.interp(quantile, centers, ordered))


def magnitude_rows(samples: list[dict]) -> list[dict]:
    rows = []
    for sample in samples:
        move = abs(float(sample["reaction"]["release_move"]))
        atr = float(sample["context"]["atr_30m"])
        if not np.isfinite(move) or not np.isfinite(atr) or atr <= 0:
            continue
        rows.append(
            {
                "release_utc": sample["release_utc"],
                "event": sample["event"],
                "absolute_move_usd": move,
                "atr_30m": atr,
                "spread_usd": max(0.0, float(sample["context"].get("spread", 0.0))),
            }
        )
    return sorted(rows, key=lambda row: row["release_utc"])


def _weights(length: int, half_life: float | None) -> np.ndarray | None:
    if half_life is None:
        return None
    age = np.arange(length - 1, -1, -1, dtype=float)
    return np.power(0.5, age / half_life)


def _pool(
    history: list[dict],
    event: str,
    window: int | None,
    scope: str = "event",
) -> list[dict]:
    if scope == "event":
        rows = [row for row in history if row["event"] == event]
    elif scope == "global":
        rows = [row for row in history if row["event"] in {"NFP", "CPI", "FOMC"}]
    else:
        raise ValueError(f"Unsupported history scope: {scope}")
    return rows[-window:] if window else rows


def _estimate_component(
    rows: list[dict],
    quantile: float,
    mode: str,
    current_atr: float,
    half_life: float | None,
) -> float:
    weights = _weights(len(rows), half_life)
    dollars = [float(row["absolute_move_usd"]) for row in rows]
    if mode == "usd":
        return weighted_quantile(dollars, quantile, weights)
    ratios = [
        float(row["absolute_move_usd"]) / float(row["atr_30m"])
        for row in rows
    ]
    atr_estimate = weighted_quantile(ratios, quantile, weights) * current_atr
    if mode == "atr":
        return atr_estimate
    if mode == "blend":
        usd_estimate = weighted_quantile(dollars, quantile, weights)
        return 0.5 * usd_estimate + 0.5 * atr_estimate
    raise ValueError(f"Unsupported range mode: {mode}")


def predict_magnitude_range(
    history: list[dict],
    *,
    event: str,
    current_atr: float,
    current_spread: float,
    config: RangeConfig,
) -> dict:
    scopes = (
        ("event", "global")
        if config.scope in {"event_global_max", "event_global_blend"}
        else (config.scope,)
    )
    pools = [_pool(history, event, config.window, scope) for scope in scopes]
    if any(len(rows) < MIN_HISTORY for rows in pools):
        raise ValueError(f"Need at least {MIN_HISTORY} prior {event} events.")
    estimates = [
        (
            _estimate_component(
                rows,
                config.low_quantile,
                config.mode,
                current_atr,
                config.half_life,
            ),
            _estimate_component(
                rows,
                0.5,
                config.mode,
                current_atr,
                config.half_life,
            ),
            _estimate_component(
                rows,
                config.high_quantile,
                config.mode,
                current_atr,
                config.half_life,
            ),
        )
        for rows in pools
    ]
    if config.scope == "event_global_max":
        low, median, high = (max(values) for values in zip(*estimates))
    elif config.scope == "event_global_blend":
        low, median, high = (float(np.mean(values)) for values in zip(*estimates))
    else:
        low, median, high = estimates[0]
    floor = max(0.1, 2 * current_spread)
    low = max(floor, low)
    high = max(low + max(0.1, current_spread), high)
    median = min(high, max(low, median))
    return {
        "minimum_usd": round(low, 2),
        "median_usd": round(median, 2),
        "maximum_usd": round(high, 2),
        "central_coverage_target_pct": round(
            100 * (config.high_quantile - config.low_quantile), 1
        ),
        "history_samples": min(len(rows) for rows in pools),
        "configuration": asdict(config),
    }


def signed_range(direction: str, forecast: dict) -> dict:
    minimum = float(forecast["minimum_usd"])
    median = float(forecast["median_usd"])
    maximum = float(forecast["maximum_usd"])
    normalized = direction.upper()
    if normalized in {"POSITIVE", "BUY"}:
        low, point, high = minimum, median, maximum
    elif normalized in {"NEGATIVE", "SELL"}:
        low, point, high = -maximum, -median, -minimum
    else:
        raise ValueError(f"Unsupported direction: {direction}")
    return {
        **forecast,
        "direction": "POSITIVE" if low >= 0 else "NEGATIVE",
        "range_low_usd": round(low, 2),
        "point_estimate_usd": round(point, 2),
        "range_high_usd": round(high, 2),
        "display": f"{low:+.2f} to {high:+.2f} USD",
    }


def interval_score(actual: float, low: float, high: float, alpha: float = 0.30) -> float:
    width = high - low
    below = (2 / alpha) * (low - actual) if actual < low else 0.0
    above = (2 / alpha) * (actual - high) if actual > high else 0.0
    return width + below + above


def quantile_loss(actual: float, estimate: float, quantile: float) -> float:
    error = actual - estimate
    return max(quantile * error, (quantile - 1) * error)


def select_range_config(
    rows: list[dict],
    *,
    cutoff: date,
    validation_start: date = VALIDATION_START,
) -> tuple[RangeConfig, list[dict]]:
    candidates = [
        RangeConfig(mode, window, half_life, scope=scope)
        for mode in ("usd", "atr", "blend")
        for window in (12, 18, 24, 36, None)
        for half_life in (None, 6.0, 12.0, 18.0, 24.0)
        for scope in ("event", "global", "event_global_blend", "event_global_max")
    ]
    results = []
    for config in candidates:
        history = []
        scores = []
        hits = 0
        widths = []
        for row in rows:
            released = date.fromisoformat(row["release_utc"][:10])
            if released >= cutoff:
                break
            required_scopes = (
                ("event", "global")
                if config.scope in {"event_global_max", "event_global_blend"}
                else (config.scope,)
            )
            enough_history = all(
                len(_pool(history, row["event"], config.window, scope)) >= MIN_HISTORY
                for scope in required_scopes
            )
            if released >= validation_start and enough_history:
                forecast = predict_magnitude_range(
                    history,
                    event=row["event"],
                    current_atr=float(row["atr_30m"]),
                    current_spread=float(row["spread_usd"]),
                    config=config,
                )
                actual = float(row["absolute_move_usd"])
                low = float(forecast["minimum_usd"])
                high = float(forecast["maximum_usd"])
                scores.append(
                    (
                        quantile_loss(actual, low, config.low_quantile)
                        + quantile_loss(actual, high, config.high_quantile)
                    )
                    / max(actual, 1.0)
                )
                hits += int(low <= actual <= high)
                widths.append(high - low)
            history.append(row)
        if scores:
            results.append(
                {
                    "config": config,
                    "events": len(scores),
                    "coverage_pct": 100 * hits / len(scores),
                    "mean_normalized_interval_score": float(np.mean(scores)),
                    "median_width_usd": float(np.median(widths)),
                }
            )
    if not results:
        raise RuntimeError("No magnitude configuration had enough validation history.")

    # Release shocks can change scale much faster than one event's monthly sample.
    # This guard is evaluated strictly before the requested cutoff and switches to
    # the last 12 major releases when their upper tail is materially above history.
    available = [
        row
        for row in rows
        if date.fromisoformat(row["release_utc"][:10]) < cutoff
        and row["event"] in {"NFP", "CPI", "FOMC"}
    ]
    recent = available[-12:]
    earlier = available[:-12]
    regime_ratio = (
        float(np.quantile([row["absolute_move_usd"] for row in recent], 0.90))
        / max(
            0.1,
            float(np.quantile([row["absolute_move_usd"] for row in earlier], 0.90)),
        )
        if len(recent) == 12 and earlier
        else 1.0
    )
    if regime_ratio >= 1.5:
        guarded = next(
            row
            for row in results
            if row["config"]
            == RangeConfig("usd", 12, None, scope="global")
        )
        guarded["regime_guard_active"] = True
        guarded["recent_to_history_p90_ratio"] = regime_ratio
        remaining = [row for row in results if row is not guarded]
        remaining.sort(key=lambda row: row["mean_normalized_interval_score"])
        return guarded["config"], [guarded, *remaining]

    nominal_coverage = 100 * (HIGH_QUANTILE - LOW_QUANTILE)
    coverage_qualified = [
        row for row in results if row["coverage_pct"] >= nominal_coverage - 5
    ]
    ranked = coverage_qualified or results
    ranked.sort(
        key=lambda row: (
            row["mean_normalized_interval_score"],
            abs(
                row["coverage_pct"]
                - 100 * (row["config"].high_quantile - row["config"].low_quantile)
            ),
            row["median_width_usd"],
        )
    )
    remaining = [row for row in results if row not in ranked]
    return ranked[0]["config"], [*ranked, *remaining]


def fit_move_range_artifact(rows: list[dict], config: RangeConfig) -> dict:
    return {
        "artifact_version": 8,
        "purpose": "walk-forward XAUUSD release-minute magnitude interval",
        "configuration": asdict(config),
        "trained_through": rows[-1]["release_utc"],
        "history": rows,
    }


def artifact_move_range(
    artifact: dict,
    *,
    event: str,
    direction: str,
    current_atr: float,
    current_spread: float,
) -> dict:
    config = RangeConfig(**artifact["configuration"])
    forecast = predict_magnitude_range(
        artifact["history"],
        event=event,
        current_atr=current_atr,
        current_spread=current_spread,
        config=config,
    )
    return signed_range(direction, forecast)
