from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TimeframeSpec:
    value: str
    label: str
    minutes: int
    mt5_constant: int


TIMEFRAME_SPECS: tuple[TimeframeSpec, ...] = (
    TimeframeSpec("M1", "M1 - 1 minute", 1, 1),
    TimeframeSpec("M2", "M2 - 2 minutes", 2, 2),
    TimeframeSpec("M3", "M3 - 3 minutes", 3, 3),
    TimeframeSpec("M4", "M4 - 4 minutes", 4, 4),
    TimeframeSpec("M5", "M5 - 5 minutes", 5, 5),
    TimeframeSpec("M6", "M6 - 6 minutes", 6, 6),
    TimeframeSpec("M10", "M10 - 10 minutes", 10, 10),
    TimeframeSpec("M12", "M12 - 12 minutes", 12, 12),
    TimeframeSpec("M15", "M15 - 15 minutes", 15, 15),
    TimeframeSpec("M20", "M20 - 20 minutes", 20, 20),
    TimeframeSpec("M30", "M30 - 30 minutes", 30, 30),
    TimeframeSpec("H1", "H1 - 1 hour", 60, 16385),
    TimeframeSpec("H2", "H2 - 2 hours", 120, 16386),
    TimeframeSpec("H3", "H3 - 3 hours", 180, 16387),
    TimeframeSpec("H4", "H4 - 4 hours", 240, 16388),
    TimeframeSpec("H6", "H6 - 6 hours", 360, 16390),
    TimeframeSpec("H8", "H8 - 8 hours", 480, 16392),
    TimeframeSpec("H12", "H12 - 12 hours", 720, 16396),
    TimeframeSpec("D1", "D1 - 1 day", 1440, 16408),
    TimeframeSpec("W1", "W1 - 1 week", 10080, 32769),
    TimeframeSpec("MN1", "MN1 - 1 month", 43200, 49153),
)

SUPPORTED_TIMEFRAMES: tuple[str, ...] = tuple(item.value for item in TIMEFRAME_SPECS)
TIMEFRAME_MINUTES: dict[str, int] = {item.value: item.minutes for item in TIMEFRAME_SPECS}
TIMEFRAME_MT5_FALLBACKS: dict[str, int] = {item.value: item.mt5_constant for item in TIMEFRAME_SPECS}


def validate_timeframe(value: str) -> str:
    timeframe = str(value).upper()
    if timeframe not in TIMEFRAME_MINUTES:
        raise ValueError(f"Unsupported timeframe: {value}")
    return timeframe


def timeframe_seconds(timeframe: str) -> int:
    return TIMEFRAME_MINUTES.get(str(timeframe).upper(), 1) * 60


def timeframe_options_payload() -> list[dict[str, Any]]:
    return [
        {
            "value": item.value,
            "label": item.label,
            "minutes": item.minutes,
        }
        for item in TIMEFRAME_SPECS
    ]


def mt5_timeframe_value(mt5_backend: Any, timeframe: str) -> int:
    normalized = validate_timeframe(timeframe)
    try:
        return int(getattr(mt5_backend, f"TIMEFRAME_{normalized}"))
    except Exception:  # noqa: BLE001
        return TIMEFRAME_MT5_FALLBACKS[normalized]
