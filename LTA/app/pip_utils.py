from __future__ import annotations

from typing import Mapping


DEFAULT_PIP_SIZES: dict[str, float] = {
    "XAUUSD": 0.01,
    "XAGUSD": 0.001,
    "BTCUSD": 0.01,
    "US30": 1.0,
    "US100": 1.0,
    "US300": 1.0,
}


def base_symbol(symbol: str) -> str:
    upper = str(symbol or "").strip().upper()
    known = (*DEFAULT_PIP_SIZES, "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD", "EURGBP", "EURJPY", "GBPJPY")
    for candidate in known:
        if candidate in upper:
            return candidate
    return upper


def parse_pip_size_map(value: str | None) -> dict[str, float]:
    parsed: dict[str, float] = {}
    for item in str(value or "").split(","):
        if ":" not in item:
            continue
        symbol, raw_size = item.split(":", 1)
        try:
            size = float(raw_size.strip())
        except ValueError:
            continue
        if size > 0:
            parsed[base_symbol(symbol)] = size
    return parsed


def pip_size_for(
    symbol: str,
    *,
    point: float | None = None,
    digits: int | None = None,
    overrides: Mapping[str, float] | None = None,
) -> float:
    base = base_symbol(symbol)
    override = float((overrides or {}).get(base, 0.0) or 0.0)
    if override > 0:
        return override
    if len(base) == 6 and base.isalpha():
        return 0.01 if base.endswith("JPY") else 0.0001
    if base in DEFAULT_PIP_SIZES:
        return DEFAULT_PIP_SIZES[base]
    point_value = float(point or 0.0)
    if point_value > 0:
        return point_value * 10 if int(digits or 0) in {3, 5} else point_value
    return 0.0
